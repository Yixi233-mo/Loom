"""MCP 演示服务 — 普通人可一键启动，验证「检测连接 / 工具调用」。

启动：python scripts/mock_mcp_server.py
地址：http://127.0.0.1:3900/mcp
说明页：http://127.0.0.1:3900/  （避免浏览器打开根路径 404）
Work Buddy 兼容工具：buddy_task（方便与内置 Work Buddy 联调）
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mock_mcp")

app = FastAPI(title="Loom Mock MCP Server")

INDEX_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Loom 演示 MCP</title>
  <style>
    body { font-family: "Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
           background:#f7f1ea; color:#2a221c; margin:0; padding:28px; line-height:1.6; }
    .card { max-width:720px; margin:0 auto; background:rgba(255,252,248,.85);
            border:1px solid rgba(42,34,28,.1); border-radius:18px; padding:24px;
            box-shadow:0 10px 32px rgba(120,72,40,.1); }
    h1 { margin:0 0 8px; font-size:22px; }
    code { background:#f6e2d4; padding:2px 6px; border-radius:6px; font-size:13px; }
    pre { background:#2a221c; color:#f7ece3; padding:12px 14px; border-radius:12px; overflow:auto; }
    .ok { color:#5f7f6a; font-weight:700; }
    a { color:#c56d42; }
  </style>
</head>
<body>
  <div class="card">
    <h1>Loom 演示 MCP <span class="ok">已启动</span></h1>
    <p>这是 <strong>JSON-RPC 协议端点</strong>，不是网页应用。浏览器直接打开本页仅作说明。</p>
    <ul>
      <li>协议地址（填进 Loom）：<code>http://127.0.0.1:3900/mcp</code></li>
      <li>健康检查：<a href="/health">/health</a></li>
    </ul>
    <h2>下一步</h2>
    <ol>
      <li>回到 Loom Web 前端（默认 <code>http://localhost:5173/</code>）</li>
      <li>打开 <strong>导航「MCP」</strong> 或 设置 → MCP 外接服务</li>
      <li>地址填 <code>http://127.0.0.1:3900/mcp</code> → <strong>检测连接</strong> → <strong>试调用工具</strong></li>
    </ol>
    <h2>可用工具</h2>
    <pre>code_task   代码任务（演示）
echo_tool   回声（演示）
buddy_task  Work Buddy 兼容任务（演示）</pre>
    <h2>curl 自测</h2>
    <pre>curl -X POST http://127.0.0.1:3900/mcp \\
  -H "Content-Type: application/json" \\
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'</pre>
  </div>
</body>
</html>
"""


def rpc_result(req_id: Any, result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "id": req_id, "result": result}


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    """浏览器说明页，避免打开根路径 404。"""
    return INDEX_HTML


@app.get("/favicon.ico")
async def favicon() -> JSONResponse:
    return JSONResponse({}, status_code=204)


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
                        {
                            "name": "buddy_task",
                            "description": "Work Buddy 兼容任务工具（演示内置助手联调）",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"prompt": {"type": "string"}},
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
        if name == "buddy_task":
            text = f"[Work Buddy 演示] 已处理：{args.get('prompt', '')}"
        else:
            text = (
                f"[演示 MCP] 工具 {name} 已执行，入参="
                f"{json.dumps(args, ensure_ascii=False)}"
            )
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
    logger.info("演示 MCP 说明页: http://127.0.0.1:3900/")
    logger.info("协议地址: http://127.0.0.1:3900/mcp")
    uvicorn.run(app, host="127.0.0.1", port=3900)
