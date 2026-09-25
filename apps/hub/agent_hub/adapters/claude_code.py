"""Claude Code Adapter — 通过 HTTP/MCP 端点调用 Claude Code。

边界：
- 超时 120s
- 失败返回 {"error": ..., "fallback": True}，不抛异常
- 只做调用，不做路由/编排

# 需确认当前版本API：方案中的简化端点为 POST {endpoint}/mcp/invoke，
# 与完整 MCP (JSON-RPC / stdio) 协议不同。若后续接入真实 MCP Server，
# 需替换传输层实现。
"""

from __future__ import annotations

from typing import Any, Optional

import httpx

DEFAULT_TIMEOUT = 120.0
DEFAULT_ENDPOINT = "http://localhost:3001"
INVOKE_PATH = "/mcp/invoke"

# 与方案一致的注册用能力标签
CLAUDE_CODE_CAPABILITIES = ["code.gen", "file.edit", "shell.exec"]


class ClaudeCodeAdapter:
    """通过 MCP 协议连接 Claude Code 的 Agent adapter。"""

    def __init__(
        self,
        mcp_endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ):
        self.endpoint = mcp_endpoint.rstrip("/")
        self.timeout = timeout
        # transport 注入点：生产用默认网络传输，测试用 httpx.MockTransport
        self._transport = transport

    async def __call__(self, prompt: str, **kwargs: Any) -> Any:
        """发送任务给 Claude Code。

        成功：返回响应 JSON。
        超时 / 网络 / HTTP 错误：返回 {"error": ..., "fallback": True}。
        """
        payload = {"tool": "code_task", "args": {"prompt": prompt, **kwargs}}
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                transport=self._transport,
            ) as client:
                resp = await client.post(f"{self.endpoint}{INVOKE_PATH}", json=payload)
                resp.raise_for_status()
                return resp.json()
        except httpx.TimeoutException:
            return {"error": "Claude Code 超时", "fallback": True}
        except Exception as e:
            return {"error": str(e), "fallback": True}


def build_adapter(
    mcp_endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = DEFAULT_TIMEOUT,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> ClaudeCodeAdapter:
    """构造适配器实例，便于注册到 AgentRegistry。"""
    return ClaudeCodeAdapter(mcp_endpoint=mcp_endpoint, timeout=timeout, transport=transport)
