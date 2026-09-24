"""MCP 面板探测测试 — 前端识别 / 连接 / 工具列表。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent_hub.adapters.mcp_protocol import McpJsonRpcClient  # noqa: E402
from api.mcp_routes import create_mcp_router  # noqa: E402


class TestMcpProbeApi(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(create_mcp_router())
        self.client = TestClient(self.app)

    def test_empty_url_400(self):
        r = self.client.post("/api/mcp/probe", json={"url": ""})
        self.assertEqual(r.status_code, 400)

    def test_probe_success_lists_tools(self):
        from unittest.mock import patch

        async def fake_init(self):
            return {"result": {"serverInfo": {"name": "demo"}}}

        async def fake_list(self):
            return {"result": {"tools": [{"name": "code_task"}, {"name": "echo_tool"}]}}

        with patch.object(McpJsonRpcClient, "initialize", fake_init), patch.object(
            McpJsonRpcClient, "tools_list", fake_list
        ):
            r = self.client.post(
                "/api/mcp/probe", json={"url": "http://127.0.0.1:3900/mcp"}
            )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["tools"], ["code_task", "echo_tool"])
        self.assertIn("连接成功", body["message"])

    def test_probe_failure_message(self):
        from unittest.mock import patch

        async def fake_init(self):
            raise RuntimeError("connection refused")

        with patch.object(McpJsonRpcClient, "initialize", fake_init):
            r = self.client.post(
                "/api/mcp/probe", json={"url": "http://127.0.0.1:1/mcp"}
            )
        body = r.json()
        self.assertFalse(body["ok"])
        self.assertIn("无法连接", body["message"])
        self.assertEqual(body["tools"], [])


class TestMockMcpServer(unittest.TestCase):
    def test_mock_server_handlers(self):
        """演示 MCP Server 可识别 initialize / tools/list。"""
        from scripts.mock_mcp_server import app as mock_app

        client = TestClient(mock_app)
        r = client.post("/mcp", json={"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}})
        self.assertEqual(r.status_code, 200)
        self.assertIn("serverInfo", r.json()["result"])

        r2 = client.post("/mcp", json={"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}})
        names = [t["name"] for t in r2.json()["result"]["tools"]]
        self.assertIn("code_task", names)

        r3 = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": "3",
                "method": "tools/call",
                "params": {"name": "code_task", "arguments": {"prompt": "hi"}},
            },
        )
        self.assertIn("已执行", r3.json()["result"]["content"][0]["text"])

        r4 = client.get("/health")
        self.assertTrue(r4.json()["ok"])


class TestFrontendMcpPanel(unittest.TestCase):
    def test_panel_has_plain_language(self):
        panel = (ROOT / "src" / "views" / "mcp-panel.ts").read_text(encoding="utf-8")
        self.assertIn("MCP 外接服务", panel)
        self.assertIn("检测连接", panel)
        self.assertIn("mcp-probe", panel)
        self.assertIn("连接成功", panel)
        self.assertIn("mock_mcp_server", panel)


if __name__ == "__main__":
    unittest.main()
