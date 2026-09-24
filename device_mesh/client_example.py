"""客户端重连样例（仅示例）。

演示：注册 → 心跳 → 断线指数退避重连（1→2→4→8s，上限 30s）→ 重新 register。

说明：服务端只用 FastAPI；本样例使用标准库 asyncio + `websockets` 作为
**客户端**依赖（不参与服务端实现）。
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

WS_URL = os.environ.get("WS_URL", "ws://127.0.0.1:8765/ws")
WS_SECRET = os.environ.get("WS_SECRET", "dev-secret")
DEVICE_ID = os.environ.get("DEVICE_ID", "demo-pc-1")
DEVICE_TYPE = os.environ.get("DEVICE_TYPE", "pc")
HEARTBEAT_INTERVAL = 15.0
MAX_BACKOFF = 30.0


def _sign(device_id: str, device_type: str, ts: float, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        f"{device_id}:{device_type}:{float(ts)}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def build_register(device_id: str, device_type: str, secret: str) -> str:
    ts = time.time()
    return json.dumps(
        {
            "type": "register",
            "device_id": device_id,
            "device_type": device_type,
            "capabilities": ["file.read", "shell.exec"],
            "ts": ts,
            "signature": _sign(device_id, device_type, ts, secret),
        }
    )


async def session_loop(ws) -> None:
    """单次连接会话：注册 + 心跳，直到断开。"""
    await ws.send(build_register(DEVICE_ID, DEVICE_TYPE, WS_SECRET))
    raw = await ws.recv()
    msg = json.loads(raw)
    if msg.get("type") != "registered":
        logger.warning("注册失败: %s", msg)
        return
    logger.info("已注册 session_id=%s", msg.get("session_id"))

    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        await ws.send(json.dumps({"type": "heartbeat", "device_id": DEVICE_ID, "ts": time.time()}))
        ack = json.loads(await ws.recv())
        logger.info("心跳: %s", ack.get("type"))


async def run_client(url: str = WS_URL) -> None:
    """带指数退避重连的客户端。"""
    import websockets  # 客户端专用

    backoff = 1.0
    while True:
        try:
            async with websockets.connect(url) as ws:
                logger.info("已连接 %s", url)
                backoff = 1.0
                await session_loop(ws)
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — 断线统一走重连
            logger.warning("连接断开: %s，%.0fs 后重连", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, MAX_BACKOFF)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_client())
