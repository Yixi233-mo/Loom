"""N10 真实 MCP + REST 联调测试。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from agent_hub.adapters.mcp_protocol import (  # noqa: E402
    DualProtocolAdapter,
    McpClaudeCodeAdapter,
    McpJsonRpcClient,
)


def make_mcp_transport():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        calls.append(body)
        method = body.get("method")
        if method == "initialize":
            return httpx.Response(
                200,
                json={"jsonrpc": "2.0", "id": body["id"], "result": {"ok": True}},
                headers={"Mcp-Session-Id": "sess-1"},
            )
        if method == "tools/call":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"content": [{"type": "text", "text": "reviewed"}]},
                },
            )
        if method == "tools/list":
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "result": {"tools": [{"name": "code_task"}]},
                },
            )
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": body["id"],
                "error": {"code": -32601, "message": "method not found"},
            },
        )

    return httpx.MockTransport(handler), calls


class TestMcpJsonRpc(unittest.IsolatedAsyncioTestCase):
    async def test_initialize_and_tools_call(self):
        transport, calls = make_mcp_transport()
        c = McpJsonRpcClient("http://localhost:3001/mcp", transport=transport)
        init = await c.initialize()
        self.assertTrue(init["result"]["ok"])
        result = await c.tools_call("code_task", {"prompt": "审查代码"})
        self.assertIn("reviewed", json.dumps(result))
        methods = [x["method"] for x in calls]
        self.assertEqual(methods, ["initialize", "tools/call"])
        self.assertEqual(calls[1]["params"]["name"], "code_task")

    async def test_error_response_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "jsonrpc": "2.0",
                    "id": body["id"],
                    "error": {"code": -1, "message": "boom"},
                },
            )

        c = McpJsonRpcClient("http://x/mcp", transport=httpx.MockTransport(handler))
        with self.assertRaises(RuntimeError):
            await c.initialize()


class TestMcpAdapterFallback(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_success(self):
        transport, _ = make_mcp_transport()
        ad = McpClaudeCodeAdapter("http://localhost:3001/mcp", transport=transport)
        out = await ad("审查代码")
        self.assertNotIn("fallback", out)
        self.assertIn("reviewed", json.dumps(out))

    async def test_mcp_down_fallback(self):
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("down")

        ad = McpClaudeCodeAdapter("http://localhost:3001/mcp", transport=httpx.MockTransport(refuse))
        out = await ad("x")
        self.assertTrue(out["fallback"])
        self.assertIn("error", out)

    async def test_dual_protocol_rest_mode(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"tool": "code_task", "ok": True})

        ad = DualProtocolAdapter(
            "http://localhost:3001", protocol="rest", transport=httpx.MockTransport(handler)
        )
        out = await ad("hi")
        self.assertTrue(out.get("ok"))

    async def test_dual_protocol_mcp_mode(self):
        transport, _ = make_mcp_transport()
        ad = DualProtocolAdapter(
            "http://localhost:3001/mcp", protocol="mcp", transport=transport
        )
        out = await ad("hi")
        self.assertIn("reviewed", json.dumps(out))


class TestFrontendRestWiring(unittest.TestCase):
    def test_llm_panel_uses_rest_api_paths(self):
        panel = (ROOT / "apps" / "web" / "src" / "views" / "llm-settings-panel.ts").read_text(encoding="utf-8")
        self.assertIn("save-llm", panel)
        self.assertIn("fetch-models", panel)
        self.assertIn("model-select", panel)

    def test_api_module_exports(self):
        idx = (ROOT / "apps" / "web" / "src" / "services" / "index.ts").read_text(encoding="utf-8")
        self.assertIn("FileService", idx)
        self.assertIn("createServiceLayer", idx)


if __name__ == "__main__":
    unittest.main()
