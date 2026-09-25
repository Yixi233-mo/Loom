"""FastAPI WebSocket 应用工厂 — 挂接 HubStack。

扩展 T8 协议：客户端可发 `trigger` 触发工作流（集成用）。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from device_mesh.protocol import (
    ErrorCode,
    MessageType,
    ProtocolError,
    build_message,
    parse_message,
)
from device_mesh.ws_server import HubRuntime, _verify_signature
from integration.stack import HubStack, _status_str
from observability.audit import get_audit
from observability.resilience import check_dependencies
from observability.security import redact_obj

logger = logging.getLogger(__name__)


def create_integrated_app(stack: HubStack) -> FastAPI:
    """创建挂接 HubStack 的 WS 应用。"""
    rt = HubRuntime(
        mesh=stack.mesh,
        cm=stack.cm,
        monitor=stack.monitor,
        secret=stack.secret,
    )

    async def on_result(msg: Dict[str, Any]) -> None:
        await stack.complete_task_async(
            task_id=str(msg.get("task_id")),
            status=str(msg.get("status", "done")),
            output=msg.get("output"),
            trace_id=msg.get("trace_id"),
        )

    rt.on_result = on_result

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        stack.monitor.start()
        yield
        await stack.monitor.stop()

    app = FastAPI(lifespan=lifespan)
    # 开发前端 (Vite :5173) 跨源访问 Hub（浏览器 Failed to fetch 根因）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.runtime = rt
    app.state.stack = stack

    @app.exception_handler(Exception)
    async def _unhandled_exception(request, exc):  # noqa: ANN001
        # 4.6 未捕获异常不崩进程；错误体脱敏
        logger.error("未捕获异常 %s: %s", request.url.path, exc, exc_info=True)
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=500, content=redact_obj({
            "code": "INTERNAL",
            "message": "内部错误，已记录日志",
            "trace_id": getattr(request.state, "trace_id", ""),
        }))

    async def _send(ws: WebSocket, payload: Dict[str, Any]) -> None:
        msg_type = payload.pop("type")
        await ws.send_text(build_message(msg_type, **payload))

    async def _handle_register(ws: WebSocket, msg: Dict[str, Any]) -> bool:
        device_id = msg.get("device_id") or ""
        device_type = msg.get("device_type") or ""
        ts = msg.get("ts", 0)
        sig = msg.get("signature") or ""
        if not _verify_signature(device_id, device_type, ts, sig, stack.secret):
            get_audit().record(
                actor=device_id or "unknown",
                action="device.register",
                resource=device_id,
                result="denied",
                reason="invalid_signature",
            )
            await _send(
                ws,
                {
                    "type": MessageType.ERROR,
                    "code": ErrorCode.INVALID_SIGNATURE.value,
                    "message": "签名失败",
                },
            )
            return False
        await stack.cm.register(device_id, ws)
        stack.monitor.update(device_id)
        stack.mesh.register(device_id, device_type, msg.get("capabilities") or [])
        get_audit().record(
            actor=device_id,
            action="device.register",
            resource=device_id,
            result="ok",
            device_type=device_type,
        )
        await _send(
            ws,
            {"type": MessageType.REGISTERED, "session_id": f"sess_{device_id}"},
        )
        return True

    async def _handle_heartbeat(ws: WebSocket, msg: Dict[str, Any]) -> None:
        device_id = msg.get("device_id") or ""
        if not stack.cm.is_connected(device_id):
            await _send(
                ws,
                {
                    "type": MessageType.ERROR,
                    "code": ErrorCode.NOT_REGISTERED.value,
                    "message": "未注册",
                },
            )
            return
        stack.monitor.update(device_id)
        await _send(ws, {"type": MessageType.HEARTBEAT_ACK})

    async def _handle_trigger(ws: WebSocket, msg: Dict[str, Any]) -> None:
        """集成扩展：trigger → HubStack.submit_workflow。"""
        workflow = msg.get("workflow") or {"name": "adhoc", "device": "any"}
        if isinstance(workflow, str):
            workflow = {"name": workflow, "device": msg.get("device", "any")}
        else:
            workflow.setdefault("device", msg.get("device", "any"))
        task_id = await stack.submit_workflow_async(
            workflow, trace_id=msg.get("trace_id")
        )
        record = stack.orch.get(task_id)
        await _send(
            ws,
            {
                "type": "trigger_ack",
                "task_id": task_id,
                "status": _status_str(record.get("status", "")),
                "assigned_to": record.get("assigned_to"),
                "trace_id": msg.get("trace_id"),
            },
        )

    async def _handle_result(ws: WebSocket, msg: Dict[str, Any]) -> None:
        await on_result(msg)
        await _send(ws, {"type": "ok", "task_id": msg.get("task_id")})

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket) -> None:
        await websocket.accept()
        if stack.cm.connection_count() >= 1000:
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
                if mtype == "register":
                    ok = await _handle_register(websocket, msg)
                    if ok:
                        current_device = msg.get("device_id")
                elif mtype == "heartbeat":
                    await _handle_heartbeat(websocket, msg)
                elif mtype == "trigger":
                    await _handle_trigger(websocket, msg)
                elif mtype == "result":
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
        except Exception as e:  # noqa: BLE001
            logger.error("WS 异常 device=%s: %s", current_device, e, exc_info=True)
        finally:
            if current_device:
                await stack.cm.unregister(current_device)
                stack.monitor.remove(current_device)
                try:
                    stack.mesh.set_online(current_device, False)
                except Exception:  # noqa: BLE001
                    pass

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {
            "ok": True,
            "status": "up",
            "online": stack.cm.get_online_devices(),
            "count": stack.cm.connection_count(),
            "tasks": [t["task_id"] for t in stack.orch.list_tasks()],
        }

    @app.get("/ready")
    async def ready() -> Dict[str, Any]:
        """4.2 就绪：检查存储 / 任务引擎 / 密钥配置。"""
        from auth.secrets import audit_secrets

        secrets = audit_secrets()
        db_ok = True
        try:
            _ = stack.orch.list_tasks()
            if getattr(stack, "kb", None) is not None:
                stack.kb.list_kbs()
        except Exception as e:  # noqa: BLE001
            db_ok = False
            logger.warning("ready 检查数据层失败: %s", e)
        status = check_dependencies(
            db_ok=db_ok,
            model_ok=bool(stack.agents),
            secrets_ok=secrets.ok,
            extra={"mesh": {"ok": True, "devices": len(stack.mesh.list_devices()) if hasattr(stack.mesh, "list_devices") else 0}},
        )
        from fastapi.responses import JSONResponse

        body = status.to_dict()
        return JSONResponse(status_code=200 if status.ok else 503, content=body)

    return app
