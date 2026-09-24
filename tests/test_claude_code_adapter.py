"""T4 单元测试：Claude Code Adapter — 成功 / 超时 / 异常 / 降级 / 注册。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent_hub.adapters.claude_code import (  # noqa: E402
    CLAUDE_CODE_CAPABILITIES,
    ClaudeCodeAdapter,
    build_adapter,
)
from agent_hub.registry import AgentNotFoundError, AgentRegistry  # noqa: E402


def ok_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    return httpx.Response(
        200,
        json={"result": "reviewed", "echo_prompt": body["args"]["prompt"]},
    )


def timeout_handler(request: httpx.Request) -> httpx.Response:
    raise httpx.ReadTimeout("simulated timeout")


def http_error_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(500, json={"detail": "internal"})


def crash_handler(request: httpx.Request) -> httpx.Response:
    raise RuntimeError("boom")


class TestSuccessPath(unittest.IsolatedAsyncioTestCase):
    async def test_invoke_ok(self):
        adapter = ClaudeCodeAdapter(
            mcp_endpoint="http://localhost:3001",
            transport=httpx.MockTransport(ok_handler),
        )
        result = await adapter("审查这段代码")
        self.assertEqual(result["result"], "reviewed")
        self.assertEqual(result["echo_prompt"], "审查这段代码")
        self.assertNotIn("fallback", result)

    async def test_invoke_passes_kwargs(self):
        captured: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            captured["url"] = str(request.url)
            return httpx.Response(200, json={"ok": True})

        adapter = ClaudeCodeAdapter(
            mcp_endpoint="http://localhost:3001/",
            transport=httpx.MockTransport(handler),
        )
        await adapter("do it", depth="full")
        self.assertEqual(captured["url"], "http://localhost:3001/mcp/invoke")
        self.assertEqual(captured["body"]["tool"], "code_task")
        self.assertEqual(captured["body"]["args"]["prompt"], "do it")
        self.assertEqual(captured["body"]["args"]["depth"], "full")


class TestFallbackPaths(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_returns_fallback(self):
        adapter = ClaudeCodeAdapter(
            mcp_endpoint="http://localhost:3001",
            timeout=0.05,
            transport=httpx.MockTransport(timeout_handler),
        )
        result = await adapter("slow task")
        self.assertTrue(result["fallback"])
        self.assertIn("超时", result["error"])

    async def test_http_error_returns_fallback(self):
        adapter = ClaudeCodeAdapter(
            mcp_endpoint="http://localhost:3001",
            transport=httpx.MockTransport(http_error_handler),
        )
        result = await adapter("task")
        self.assertTrue(result["fallback"])
        self.assertIn("error", result)

    async def test_unexpected_exception_returns_fallback(self):
        adapter = ClaudeCodeAdapter(
            mcp_endpoint="http://localhost:3001",
            transport=httpx.MockTransport(crash_handler),
        )
        result = await adapter("task")
        self.assertTrue(result["fallback"])
        self.assertIn("boom", result["error"])

    async def test_connection_error_returns_fallback(self):
        def refuse(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        adapter = ClaudeCodeAdapter(
            mcp_endpoint="http://127.0.0.1:1",
            transport=httpx.MockTransport(refuse),
        )
        result = await adapter("task")
        self.assertTrue(result["fallback"])


class TestTimeoutSemantics(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_message_exact(self):
        adapter = ClaudeCodeAdapter(timeout=0.01, transport=httpx.MockTransport(timeout_handler))
        result = await adapter("x")
        self.assertEqual(result, {"error": "Claude Code 超时", "fallback": True})


class TestRegistryIntegration(unittest.IsolatedAsyncioTestCase):
    async def test_register_and_invoke(self):
        reg = AgentRegistry()
        adapter = build_adapter(transport=httpx.MockTransport(ok_handler))
        reg.register("claude_code", adapter, CLAUDE_CODE_CAPABILITIES)

        self.assertIn("claude_code", reg.list_agents())
        self.assertIn("claude_code", reg.match("code.gen"))
        self.assertIn("claude_code", reg.match("shell.exec"))

        result = await reg.invoke("claude_code", "生成代码骨架")
        self.assertEqual(result["result"], "reviewed")

    async def test_fallback_still_invocable(self):
        reg = AgentRegistry()
        adapter = build_adapter(transport=httpx.MockTransport(timeout_handler))
        reg.register("claude_code", adapter, CLAUDE_CODE_CAPABILITIES)
        result = await reg.invoke("claude_code", "x")
        self.assertTrue(result["fallback"])

    async def test_unknown_agent_still_raises(self):
        reg = AgentRegistry()
        with self.assertRaises(AgentNotFoundError):
            await reg.invoke("claude_code", "x")


if __name__ == "__main__":
    unittest.main()
