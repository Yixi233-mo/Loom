"""WebSocket 服务端 — FastAPI 原生 WebSocket。

网络模式（NETWORK_MODE）：
  local     → 127.0.0.1:8765
  tailscale → 0.0.0.0:8765
  public    → 0.0.0.0:8765（反向代理）
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from device_mesh.connection_manager import ConnectionManager
from device_mesh.heartbeat import HeartbeatMonitor
from device_mesh.protocol import (
    ErrorCode,
    MessageType,
    ProtocolError,
    build_message,
    parse_message,
)
from device_mesh.registry import DeviceMesh

logger = logging.getLogger(__name__)

DEFAULT_SECRET = "dev-secret"
DEFAULT_PORT = 8765
DEFAULT_MAX_CONNECTIONS = 1000


def _verify_signature(
    device_id: str,
    device_type: str,
    ts: int,
    sig: str,
    secret: str,
    max_skew: float = 60.0,
    now: Optional[float] = None,
) -> bool:
    """HMAC-SHA256 签名校验：内容 f\"{device_id}:{device_type}:{ts}\"。"""
    if now is None:
        now = time.time()
    try:
        ts_val = float(ts)
    except (TypeError, ValueError):
        return False
    if abs(now - ts_val) > max_skew:
        return False
    expect = hmac.new(
        secret.encode("utf-8"),
        f"{device_id}:{device_type}:{ts_val}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expect, sig or "")


def make_signature(
    device_id: str,
    device_type: str,
    ts: int | float,
    secret: str,
) -> str:
    """客户端/测试用：生成签名。"""
    return hmac.new(
        secret.encode("utf-8"),
        f"{device_id}:{device_type}:{float(ts)}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class HubRuntime:
    """服务端运行时依赖容器（便于测试注入）。"""

    def __init__(
        self,
        mesh: Optional[DeviceMesh] = None,
        cm: Optional[ConnectionManager] = None,
        monitor: Optional[HeartbeatMonitor] = None,
        secret: Optional[str] = None,
        max_connections: Optional[int] = None,
        on_result=None,
    ) -> None:
        self.mesh = mesh or DeviceMesh()
        self.cm = cm or ConnectionManager()
        self.monitor = monitor or HeartbeatMonitor(self.cm)
        self.secret = secret or os.environ.get("WS_SECRET", DEFAULT_SECRET)
        self.max_connections = max_connections or int(
            os.environ.get("MAX_CONNECTIONS", str(DEFAULT_MAX_CONNECTIONS))
        )
        # T9 接入 TaskOrchestrator 后替换
        self.on_result = on_result


def create_app(runtime: Optional[HubRuntime] = None) -> FastAPI:
    """创建 FastAPI 应用。"""
    rt = runtime or HubRuntime()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        rt.monitor.start()
        logger.info(
            "WS server ready: max_connections=%s", rt.max_connections
        )
        yield
        await rt.monitor.stop()

    app = FastAPI(lifespan=lifespan)
    app.state.runtime = rt

    async def _send(ws: WebSocket, payload: Dict[str, Any]) -> None:
        msg_type = payload.pop("type")
        await ws.send_text(build_message(msg_type, **payload))

    async def _handle_register(ws: WebSocket, msg: Dict[str, Any]) -> bool:
        device_id = msg.get("device_id") or ""
        device_type = msg.get("device_type") or ""
        ts = msg.get("ts", 0)
        sig = msg.get("signature") or ""
        if not _verify_signature(
            device_id, device_type, ts, sig, rt.secret
        ):
            await _send(
                ws,
                {
                    "type": MessageType.ERROR,
                    "code": ErrorCode.INVALID_SIGNATURE.value,
                    "message": "签名失败",
                },
            )
            return False

        await rt.cm.register(device_id, ws)
        rt.monitor.update(device_id)
        rt.mesh.register(device_id, device_type, msg.get("capabilities") or [])
        await _send(
            ws,
            {
                "type": MessageType.REGISTERED,
                "session_id": f"sess_{device_id}",
            },
        )
        return True

    async def _handle_heartbeat(ws: WebSocket, msg: Dict[str, Any]) -> None:
        device_id = msg.get("device_id") or ""
        if not rt.cm.is_connected(device_id):
            await _send(
                ws,
                {
                    "type": MessageType.ERROR,
                    "code": ErrorCode.NOT_REGISTERED.value,
                    "message": "未注册",
                },
            )
            return
        rt.monitor.update(device_id)
        await _send(ws, {"type": MessageType.HEARTBEAT_ACK})

    async def _handle_result(ws: WebSocket, msg: Dict[str, Any]) -> None:
        # T9 接入后改为转发给 TaskOrchestrator
        if rt.on_result is not None:
            rt.on_result(msg)
        await _send(ws, {"type": "ok", "task_id": msg.get("task_id")})

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        if rt.cm.connection_count() >= rt.max_connections:
            await websocket.send_text(
                build_message(
                    MessageType.ERROR,
                    code=ErrorCode.TOO_MANY_CONNECTIONS.value,
                    message="连接数超限",
                )
            )
            await websocket.close()
            return

        current_device: Optional[str] = None
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = parse_message(raw)
                except ProtocolError as e:
                    await websocket.send_text(
                        build_message(
                            MessageType.ERROR,
                            code=ErrorCode.INVALID_MESSAGE.value,
                            message=str(e),
                        )
                    )
                    continue

                mtype = msg.get("type")
                if mtype == MessageType.REGISTER.value or mtype == "register":
                    ok = await _handle_register(websocket, msg)
                    if ok:
                        current_device = msg.get("device_id")
                elif mtype == MessageType.HEARTBEAT.value or mtype == "heartbeat":
                    await _handle_heartbeat(websocket, msg)
                elif mtype == MessageType.RESULT.value or mtype == "result":
                    await _handle_result(websocket, msg)
                else:
                    await websocket.send_text(
                        build_message(
                            MessageType.ERROR,
                            code=ErrorCode.INVALID_MESSAGE.value,
                            message=f"未知 type: {mtype}",
                        )
                    )
        except WebSocketDisconnect:
            logger.info("设备断开: %s", current_device)
        except Exception as e:  # noqa: BLE001 — 连接级异常不崩溃服务
            logger.error("WebSocket 异常 device=%s: %s", current_device, e, exc_info=True)
        finally:
            if current_device:
                await rt.cm.unregister(current_device)
                rt.monitor.remove(current_device)
                # DeviceMesh 中保留注册信息但标记离线
                try:
                    rt.mesh.set_online(current_device, False)
                except Exception:  # noqa: BLE001 — 设备可能已注销
                    pass

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {
            "ok": True,
            "online": rt.cm.get_online_devices(),
            "count": rt.cm.connection_count(),
        }

    return app


def run_server() -> None:
    """按 NETWORK_MODE 启动服务。"""
    import uvicorn

    mode = os.environ.get("NETWORK_MODE", "local")
    host = "127.0.0.1" if mode == "local" else "0.0.0.0"
    port = int(os.environ.get("WS_PORT", str(DEFAULT_PORT)))
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(create_app(), host=host, port=port)


if __name__ == "__main__":
    run_server()
