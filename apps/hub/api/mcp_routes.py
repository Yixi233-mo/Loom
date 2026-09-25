"""REST /api/mcp/* — 探测连接 · 工具调用 · 内置目录 / 下载推荐。

对齐完整链路：
  用户对话 → 意图识别 → 选端 → **工具调用 / 连 Claude Code · Work Buddy**
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agent_hub.adapters.mcp_protocol import McpJsonRpcClient
from agent_hub.mcp_catalog import builtin_mcp_catalog, catalog_download_links
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field


class McpProbeIn(BaseModel):
    url: str = Field(alias="url")
    timeout: float = 8.0
    token: Optional[str] = None

    model_config = {"populate_by_name": True}


class McpToolsCallIn(BaseModel):
    url: str
    tool: str = "code_task"
    arguments: Dict[str, Any] = Field(default_factory=dict)
    timeout: float = 30.0
    protocol: str = "mcp"  # mcp | rest（rest 走 /mcp/invoke）
    token: Optional[str] = None

    model_config = {"populate_by_name": True}


def create_mcp_router() -> APIRouter:
    router = APIRouter(prefix="/api/mcp")

    @router.get("/catalog")
    def catalog() -> Dict[str, Any]:
        """内置 MCP / 助手目录（含 Work Buddy 下载内链）。"""
        return {
            "items": builtin_mcp_catalog(),
            "downloads": catalog_download_links(),
        }

    @router.post("/probe")
    async def probe(body: McpProbeIn) -> Dict[str, Any]:
        """探测 MCP 地址：initialize + tools/list，返回是否可用与工具列表。"""
        url = (body.url or "").strip()
        if not url:
            raise HTTPException(400, "请填 MCP 地址")
        client = McpJsonRpcClient(url, timeout=body.timeout, auth_token=body.token)
        try:
            init = await client.initialize()
        except Exception as e:  # noqa: BLE001
            return {
                "ok": False,
                "url": url,
                "message": f"无法连接（请确认服务已启动、地址正确）: {e}",
                "tools": [],
                "serverInfo": None,
            }
        try:
            listed = await client.tools_list()
        except Exception as e:  # noqa: BLE001
            listed = {"result": {"tools": []}}
            tools_note = f"已连接，但获取工具列表失败: {e}"
        else:
            tools_note = "连接成功"

        tools: List[str] = []
        raw_tools = (listed.get("result") or {}).get("tools") or []
        for t in raw_tools:
            if isinstance(t, dict) and t.get("name"):
                tools.append(str(t["name"]))

        server_info = (init.get("result") or {}).get("serverInfo") or {}
        return {
            "ok": True,
            "url": url,
            "message": tools_note,
            "tools": tools,
            "serverInfo": server_info,
        }

    @router.post("/tools-call")
    async def tools_call(body: McpToolsCallIn) -> Dict[str, Any]:
        """真实工具调用：MCP tools/call（或 REST /mcp/invoke）。"""
        url = (body.url or "").strip()
        tool = (body.tool or "").strip()
        if not url:
            raise HTTPException(400, "请填 MCP 地址")
        if not tool:
            raise HTTPException(400, "请填工具名")

        if body.protocol == "rest":
            import httpx

            payload = {"tool": tool, "args": body.arguments}
            try:
                async with httpx.AsyncClient(timeout=body.timeout) as client:
                    resp = await client.post(f"{url.rstrip('/')}/mcp/invoke", json=payload)
                    resp.raise_for_status()
                    return {
                        "ok": True,
                        "protocol": "rest",
                        "tool": tool,
                        "url": url,
                        "result": resp.json(),
                    }
            except Exception as e:  # noqa: BLE001
                return {
                    "ok": False,
                    "protocol": "rest",
                    "tool": tool,
                    "url": url,
                    "error": str(e),
                    "fallback": True,
                }

        client = McpJsonRpcClient(url, timeout=body.timeout, auth_token=body.token)
        try:
            await client.initialize()
            result = await client.tools_call(tool, body.arguments)
            return {
                "ok": True,
                "protocol": "mcp",
                "tool": tool,
                "url": url,
                "result": result,
            }
        except Exception as e:  # noqa: BLE001
            return {
                "ok": False,
                "protocol": "mcp",
                "tool": tool,
                "url": url,
                "error": str(e),
                "fallback": True,
            }

    return router


def mount_mcp_api(app: Any) -> None:
    app.include_router(create_mcp_router())
