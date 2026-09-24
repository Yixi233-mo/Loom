"""真实 MCP 协议适配器 — JSON-RPC 2.0（initialize / tools/call）。

与简化 POST /mcp/invoke 兼容双模式：
  protocol="mcp"   → JSON-RPC streamable HTTP / SSE 兼容的 POST
  protocol="rest"  → 方案简化端点 /mcp/invoke（历史）

# 需确认当前版本API：MCP streamable HTTP 细节随 SDK 版本变化，
# 此处实现常用 JSON-RPC 消息形状，传输层可替换。
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

import httpx

DEFAULT_TIMEOUT = 120.0
CLAUDE_CODE_CAPABILITIES = ["code.gen", "file.edit", "shell.exec"]


class McpJsonRpcClient:
    """最小 JSON-RPC over HTTP 客户端。"""

    def __init__(
        self,
        endpoint: str,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout
        self._transport = transport
        self._session_id: Optional[str] = None

    async def request(
        self, method: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": method,
            "params": params or {},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id
        async with httpx.AsyncClient(
            timeout=self.timeout, transport=self._transport
        ) as client:
            resp = await client.post(self.endpoint, json=payload, headers=headers)
            sid = resp.headers.get("Mcp-Session-Id") or resp.headers.get("mcp-session-id")
            if sid:
                self._session_id = sid
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "")
            if "text/event-stream" in ctype:
                return _parse_sse_json(resp.text)
            data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            raise RuntimeError(f"MCP error: {data['error']}")
        return data if isinstance(data, dict) else {"result": data}

    async def initialize(self) -> Dict[str, Any]:
        return await self.request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "loom-hub", "version": "0.1.0"},
            },
        )

    async def tools_list(self) -> Dict[str, Any]:
        return await self.request("tools/list", {})

    async def tools_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return await self.request(
            "tools/call", {"name": name, "arguments": arguments}
        )


def _parse_sse_json(text: str) -> Dict[str, Any]:
    """从 SSE `data:` 行提取 JSON-RPC 响应。"""
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            import json

            try:
                return json.loads(line[5:].strip())
            except Exception:  # noqa: BLE001
                continue
    raise RuntimeError(f"SSE 无 JSON 数据: {text[:200]!r}")


class McpClaudeCodeAdapter:
    """真实 MCP 协议调用 Claude Code；失败返回 fallback 结构。"""

    def __init__(
        self,
        endpoint: str = "http://localhost:3001/mcp",
        timeout: float = DEFAULT_TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        tool_name: str = "code_task",
    ) -> None:
        self.client = McpJsonRpcClient(endpoint, timeout=timeout, transport=transport)
        self.tool_name = tool_name
        self.timeout = timeout

    async def __call__(self, prompt: str, **kwargs: Any) -> Any:
        try:
            await self.client.initialize()
            result = await self.client.tools_call(
                self.tool_name, {"prompt": prompt, **kwargs}
            )
            return result
        except httpx.TimeoutException:
            return {"error": "Claude Code 超时", "fallback": True}
        except Exception as e:  # noqa: BLE001 — 降级不抛
            return {"error": str(e), "fallback": True}


class DualProtocolAdapter:
    """mcp / rest 双模式，按 protocol 切换。"""

    def __init__(
        self,
        endpoint: str,
        protocol: str = "mcp",
        timeout: float = DEFAULT_TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        from agent_hub.adapters.claude_code import ClaudeCodeAdapter

        self.protocol = protocol
        self._mcp = McpClaudeCodeAdapter(
            endpoint=endpoint, timeout=timeout, transport=transport
        )
        self._rest = ClaudeCodeAdapter(
            mcp_endpoint=endpoint, timeout=timeout, transport=transport
        )

    async def __call__(self, prompt: str, **kwargs: Any) -> Any:
        if self.protocol == "rest":
            return await self._rest(prompt, **kwargs)
        return await self._mcp(prompt, **kwargs)
