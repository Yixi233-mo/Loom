"""Work Buddy MCP 适配器 — 内置外部 AI 助手。

流程位：意图识别 → 选执行端 → **调用工具 / 连接 Claude Code / Work Buddy**
（本模块负责「连接 Work Buddy 并 tools/call」一段）。

# 需确认当前版本API：Work Buddy 官方 MCP endpoint / 下载页若变更，改 catalog 即可。
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from agent_hub.adapters.mcp_protocol import McpJsonRpcClient

DEFAULT_ENDPOINT = os.environ.get(
    "LOOM_WORK_BUDDY_MCP", "http://127.0.0.1:54916/mcp"
)
DEFAULT_TOKEN = os.environ.get(
    "LOOM_WORK_BUDDY_TOKEN", "k46BofoxqxEHe9K1uWpxZfvvVB1LwXdp-IWzi_abM6c"
)
DEFAULT_DOWNLOAD_URL = os.environ.get(
    "LOOM_WORK_BUDDY_DOWNLOAD_URL",
    "https://github.com/Yixi233-mo/WorkBuddy/releases/latest",
)
DEFAULT_TIMEOUT = 120.0

WORK_BUDDY_CAPABILITIES = ["buddy.task", "buddy.chat", "buddy.assist"]
WORK_BUDDY_TOOL = os.environ.get("LOOM_WORK_BUDDY_TOOL", "present_files")


class WorkBuddyAdapter:
    """调用 Work Buddy MCP（JSON-RPC tools/call），失败返回 fallback 结构。"""

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout: float = DEFAULT_TIMEOUT,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        tool_name: str = WORK_BUDDY_TOOL,
        auth_token: Optional[str] = None,
    ) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.tool_name = tool_name
        self.auth_token = auth_token if auth_token is not None else DEFAULT_TOKEN
        self.client = McpJsonRpcClient(endpoint, timeout=timeout, transport=transport, auth_token=self.auth_token)

    async def __call__(self, prompt: str, **kwargs: Any) -> Any:
        try:
            await self.client.initialize()
            tools = await self.client.tools_list()
            names = [
                t.get("name")
                for t in (tools.get("result") or {}).get("tools") or []
                if isinstance(t, dict)
            ]
            tool = self.tool_name if self.tool_name in names else (names[0] if names else self.tool_name)
            result = await self.client.tools_call(tool, {"prompt": prompt, **kwargs})
            if isinstance(result, dict):
                result.setdefault("tool", tool)
                result.setdefault("endpoint", self.endpoint)
                result.setdefault("assistant", "work_buddy")
            return result
        except httpx.TimeoutException:
            return {
                "error": "Work Buddy 超时",
                "fallback": True,
                "download_url": DEFAULT_DOWNLOAD_URL,
            }
        except Exception as e:  # noqa: BLE001 — 降级不抛
            return {
                "error": str(e),
                "fallback": True,
                "download_url": DEFAULT_DOWNLOAD_URL,
                "hint": "未安装或未启动 Work Buddy？点内链下载安装后重试",
            }


def build_adapter(
    endpoint: str = DEFAULT_ENDPOINT,
    timeout: float = DEFAULT_TIMEOUT,
    transport: Optional[httpx.AsyncBaseTransport] = None,
) -> WorkBuddyAdapter:
    return WorkBuddyAdapter(endpoint=endpoint, timeout=timeout, transport=transport)


def work_buddy_catalog_entry() -> Dict[str, Any]:
    """内置推荐卡片：产品说明 + 下载内链 + 默认 MCP 地址。"""
    return {
        "id": "work_buddy",
        "name": "Work Buddy",
        "kind": "builtin-assistant",
        "description": "内置推荐的 AI 助手（Work Buddy）。装好后按 MCP 地址接入 Loom，工具调用可直达。",
        "endpoint": DEFAULT_ENDPOINT,
        "auth_token_env": "LOOM_WORK_BUDDY_TOKEN",
        "connected_hint": "本机 WorkBuddy connector-proxy（.workbuddy/.mcp.json）",
        "default_tool": WORK_BUDDY_TOOL,
        "capabilities": list(WORK_BUDDY_CAPABILITIES),
        "download_url": DEFAULT_DOWNLOAD_URL,
        "download_label": "下载 Work Buddy",
        "install_hint": "下载安装 → 启动 Work Buddy 的 MCP 服务 → 在下方填地址并「检测连接」",
        "docs": "目录/MCP_工具调用说明.md",
    }
