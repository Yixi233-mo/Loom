"""MCP 演示服务 — 普通人可一键启动，用来验证前端「检测连接」。

启动：python scripts/mock_mcp_server.py
地址：http://127.0.0.1:3900/mcp
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock_mcp")

app = FastAPI(title="Loom Mock MCP Server")


def rpc_result(req_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


@app.post("/mcp")
async def mcp_endpoint(request: Request) -> JSONResponse:
    body = await request.json()
    method = body.get("method")
    req_id = body.get("id")
    logger.info("MCP method=%s", method)

    if method == "initialize":
        return JSONResponse(
            rpc_result(
                req_id,
                {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "loom-demo-mcp", "version": "0.1.0"},
                },
            ),
            headers={"Mcp-Session-Id": "demo-session"},
        )

    if method == "tools/list":
        return JSONResponse(
            rpc_result(
                req_id,
                {
                    "tools": [
                        {
                            "name": "code_task",
                            "description": "执行代码审查/生成任务（演示）",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"prompt": {"type": "string"}},
                            },
                        },
                        {
                            "name": "echo_tool",
                            "description": "回声工具（演示）",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"text": {"type": "string"}},
                            },
                        },
                    ]
                },
            )
        )

    if method == "tools/call":
        params = body.get("params") or {}
        name = params.get("name")
        args = params.get("arguments") or {}
        text = f"[演示 MCP] 工具 {name} 已执行，入参={json.dumps(args, ensure_ascii=False)}"
        return JSONResponse(
            rpc_result(req_id, {"content": [{"type": "text", "text": text}]})
        )

    return JSONResponse(
        {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"未知方法: {method}"},
        }
    )


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "name": "loom-demo-mcp"}


if __name__ == "__main__":
    logger.info("演示 MCP: http://127.0.0.1:3900/mcp")
    uvicorn.run(app, host="127.0.0.1", port=3900)
