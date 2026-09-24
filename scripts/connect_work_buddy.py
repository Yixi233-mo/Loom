"""连接 WorkBuddy（CodeBuddy）connector-proxy 并验证工具调用。

用法：python scripts/connect_work_buddy.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ENDPOINT = os.environ.get("LOOM_WORK_BUDDY_MCP", "http://127.0.0.1:54916/mcp")
# 启动 WorkBuddy 时会在其日志/CLI 注入 connector token；也可用环境变量覆盖
TOKEN = os.environ.get(
    "LOOM_WORK_BUDDY_TOKEN",
    "k46BofoxqxEHe9K1uWpxZfvvVB1LwXdp-IWzi_abM6c",
)


def headers() -> dict:
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    return h


def parse_sse(text: str) -> dict:
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            return json.loads(line[5:].strip())
    try:
        return json.loads(text)
    except Exception:
        return {"raw": text[:500]}


def main() -> int:
    with httpx.Client(timeout=15.0) as c:
        r = c.post(
            ENDPOINT,
            headers=headers(),
            json={
                "jsonrpc": "2.0",
                "id": "1",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "loom-hub", "version": "0.1.0"},
                },
            },
        )
        print("initialize", r.status_code, parse_sse(r.text))
        sid = r.headers.get("mcp-session-id")
        h = headers()
        if sid:
            h["Mcp-Session-Id"] = sid

        r2 = c.post(
            ENDPOINT,
            headers=h,
            json={"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}},
        )
        listed = parse_sse(r2.text)
        tools = (listed.get("result") or {}).get("tools") or []
        print("tools/list", r2.status_code, "count=", len(tools))
        for t in tools[:15]:
            print(" -", t.get("name"), "::", (t.get("description") or "")[:60])

        # 试调用只读工具
        if tools:
            name = tools[0]["name"]
            args = {}
            r3 = c.post(
                ENDPOINT,
                headers=h,
                json={
                    "jsonrpc": "2.0",
                    "id": "3",
                    "method": "tools/call",
                    "params": {"name": name, "arguments": args},
                },
            )
            print("tools/call", name, r3.status_code, parse_sse(r3.text))

        # 落盘给 Loom Hub / 前端读取
        conf = {
            "endpoint": ENDPOINT,
            "token_env": "LOOM_WORK_BUDDY_TOKEN",
            "session_id": sid,
            "serverInfo": (parse_sse(r.text).get("result") or {}).get("serverInfo"),
            "tools": [t.get("name") for t in tools],
            "connected": r.status_code == 200 and len(tools) > 0,
        }
        out = ROOT / "plugins" / "work_buddy_connection.json"
        out.write_text(json.dumps(conf, ensure_ascii=False, indent=2), encoding="utf-8")
        print("saved", out)
        return 0 if conf["connected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
