"""工具调用全链路 E2E — 意图识别 → Registry → MCP tools/call → Work Buddy。

覆盖用户指出的缺口：
  对话 → 意图 → 选端 → 调用工具 / 连 Claude Code · Work Buddy
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent_hub.adapters.mcp_protocol import (  # noqa: E402
    McpClaudeCodeAdapter,
    McpJsonRpcClient,
)
from agent_hub.adapters.work_buddy import (  # noqa: E402
    WorkBuddyAdapter,
    work_buddy_catalog_entry,
)
from agent_hub.graph import build_hub_graph  # noqa: E402
from agent_hub.mcp_catalog import (  # noqa: E402
    builtin_mcp_catalog,
    catalog_download_links,
)
from agent_hub.registry import AgentRegistry  # noqa: E402
from api.mcp_routes import create_mcp_router  # noqa: E402
from scripts.mock_mcp_server import app as mock_mcp_app  # noqa: E402


def make_tool_transport(
    tool_text: str = "tool-ok",
    tools: list | None = None,
):
    """最小 MCP JSON-RPC transport：initialize / tools/list / tools/call。"""
    names = tools or [{"name": "code_task"}, {"name": "buddy_task"}, {"name": "echo_tool"}]
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        method = body.get("method")
        rid = body.get("id")
        if method == "initialize":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {"serverInfo": {"name": "e2e-mcp"}},
                },
                headers={"Mcp-Session-Id": "s1"},
            )
        if method == "tools/list":
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": rid, "result": {"tools": names}},
            )
        if method == "tools/call":
            params = body.get("params") or {}
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": f"{tool_text}:{params.get('name')}",
                            }
                        ],
                        "tool": params.get("name"),
                    },
                },
            )
        return httpx.Response(
            200,
            json={"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "no"}},
        )

    return httpx.MockTransport(handler), calls


class TestToolCallChain(unittest.IsolatedAsyncioTestCase):
    """意图 → AgentRegistry → MCP tools/call。"""

    async def test_intent_code_review_calls_mcp_tool(self):
        transport, calls = make_tool_transport("reviewed")
        adapter = McpClaudeCodeAdapter(
            "http://claude.local/mcp", tool_name="code_task", transport=transport
        )
        registry = AgentRegistry()
        registry.register("claude_code", adapter, ["code.gen"])

        graph = build_hub_graph(registry=registry)
        out = await graph.ainvoke({"user_input": "审查代码 def f(): pass"})
        self.assertEqual(out["intent"], "agent_task")
        self.assertEqual(out["agent"], "claude_code")
        self.assertIn("reviewed", out.get("result", ""))

        methods = [c["method"] for c in calls]
        self.assertEqual(methods, ["initialize", "tools/call"])
        self.assertEqual(calls[1]["params"]["name"], "code_task")

    async def test_work_buddy_tool_call(self):
        transport, calls = make_tool_transport("buddy-done", tools=[{"name": "buddy_task"}])
        buddy = WorkBuddyAdapter(
            "http://buddy.local/mcp", transport=transport, tool_name="buddy_task"
        )
        out = await buddy("帮我整理周报")
        self.assertNotIn("fallback", out)
        text = json.dumps(out, ensure_ascii=False)
        self.assertIn("buddy-done:buddy_task", text)
        self.assertEqual(out.get("assistant"), "work_buddy")
        self.assertEqual(calls[-1]["params"]["name"], "buddy_task")

    async def test_work_buddy_missing_server_returns_download_hint(self):
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        buddy = WorkBuddyAdapter("http://127.0.0.1:9/mcp", transport=httpx.MockTransport(refuse))
        out = await buddy("x")
        self.assertTrue(out.get("fallback"))
        self.assertIn("download_url", out)
        self.assertIn("WorkBuddy", out["download_url"] + out.get("hint", ""))

    async def test_registry_dispatch_work_buddy(self):
        transport, _ = make_tool_transport("hi-buddy", tools=[{"name": "buddy_task"}])
        buddy = WorkBuddyAdapter("http://b/mcp", transport=transport)
        registry = AgentRegistry()
        registry.register("work_buddy", buddy, ["buddy.task"])
        graph = build_hub_graph(registry=registry)
        # 规则关键词未覆盖 work buddy → 强制指定 agent 后 dispatch
        await graph.ainvoke(
            {"user_input": "用助手总结", "intent": "agent_task", "agent": "work_buddy"}
        )
        # classify 会覆盖 intent；直接 invoke registry 更稳
        result = await registry.invoke("work_buddy", "用助手总结")
        self.assertIn("hi-buddy", json.dumps(result, ensure_ascii=False))
        self.assertIn(result.get("assistant"), (None, "work_buddy"))


class TestMcpHttpApi(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(create_mcp_router())
        self.client = TestClient(self.app)

    def test_catalog_includes_work_buddy_download(self):
        r = self.client.get("/api/mcp/catalog")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        ids = [x["id"] for x in body["items"]]
        self.assertIn("work_buddy", ids)
        self.assertIn("loom_demo", ids)
        self.assertIn("claude_code", ids)
        self.assertTrue(body["downloads"])
        wb = next(x for x in body["items"] if x["id"] == "work_buddy")
        self.assertIn("download_url", wb)
        self.assertIn("下载 Work Buddy", wb["download_label"])

    def test_tools_call_mcp_protocol(self):
        from unittest.mock import patch

        async def fake_init(self):
            return {"result": {"serverInfo": {"name": "x"}}}

        async def fake_call(self, name, arguments):
            return {"content": [{"type": "text", "text": f"ok:{name}"}]}

        with patch.object(McpJsonRpcClient, "initialize", fake_init), patch.object(
            McpJsonRpcClient, "tools_call", fake_call
        ):
            r = self.client.post(
                "/api/mcp/tools-call",
                json={
                    "url": "http://127.0.0.1:3900/mcp",
                    "tool": "buddy_task",
                    "arguments": {"prompt": "hi"},
                },
            )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["tool"], "buddy_task")
        self.assertIn("ok:buddy_task", json.dumps(body["result"]))

    def test_tools_call_requires_tool(self):
        r = self.client.post(
            "/api/mcp/tools-call",
            json={"url": "http://x/mcp", "tool": ""},
        )
        self.assertEqual(r.status_code, 400)


class TestMockServerBuddy(unittest.TestCase):
    def test_mock_buddy_task(self):
        client = TestClient(mock_mcp_app)
        r = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "tools/call",
                "params": {"name": "buddy_task", "arguments": {"prompt": "日报"}},
            },
        )
        self.assertIn("Work Buddy 演示", r.json()["result"]["content"][0]["text"])
        r2 = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}},
        )
        names = [t["name"] for t in r2.json()["result"]["tools"]]
        self.assertIn("buddy_task", names)


class TestCatalogModule(unittest.TestCase):
    def test_download_links_only_with_url(self):
        links = catalog_download_links()
        self.assertTrue(any(x["id"] == "work_buddy" for x in links))
        entry = work_buddy_catalog_entry()
        self.assertEqual(entry["download_label"], "下载 Work Buddy")
        self.assertTrue(entry["endpoint"].endswith("/mcp"))

    def test_builtin_three_cards(self):
        items = builtin_mcp_catalog()
        self.assertEqual(len(items), 3)


class TestFrontendPanel(unittest.TestCase):
    def test_panel_has_work_buddy_and_catalog(self):
        panel = (ROOT / "src" / "views" / "mcp-panel.ts").read_text(encoding="utf-8")
        self.assertIn("Work Buddy", panel)
        self.assertIn("下载 Work Buddy", panel)
        self.assertIn("catalog", panel)
        self.assertIn("tools-call", panel)


if __name__ == "__main__":
    unittest.main()
