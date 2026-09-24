"""REST /api/mcp/* — 前端 MCP 识别 / 探测连接。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agent_hub.adapters.mcp_protocol import McpJsonRpcClient


class McpProbeIn(BaseModel):
    url: str = Field(alias="url")
    timeout: float = 8.0

    model_config = {"populate_by_name": True}


def create_mcp_router() -> APIRouter:
    router = APIRouter(prefix="/api/mcp")

    @router.post("/probe")
    async def probe(body: McpProbeIn) -> Dict[str, Any]:
        """探测 MCP 地址：initialize + tools/list，返回是否可用与工具列表。"""
        url = (body.url or "").strip()
        if not url:
            raise HTTPException(400, "请填写 MCP 地址")
        client = McpJsonRpcClient(url, timeout=body.timeout)
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

    return router


def mount_mcp_api(app: Any) -> None:
    app.include_router(create_mcp_router())
