"""WebSocket 消息协议 — JSON-RPC 2.0 风格。"""

from __future__ import annotations

import json
import time
from enum import Enum
from typing import Any, Dict

MAX_MESSAGE_BYTES = 1024 * 1024  # 1MB


class MessageType(str, Enum):
    REGISTER = "register"
    HEARTBEAT = "heartbeat"
    RESULT = "result"
    REGISTERED = "registered"
    HEARTBEAT_ACK = "heartbeat_ack"
    TASK_DISPATCH = "task_dispatch"
    SYNC_BROADCAST = "sync_broadcast"
    ERROR = "error"


class ErrorCode(int, Enum):
    NOT_REGISTERED = 4001
    INVALID_MESSAGE = 4002
    TOO_MANY_CONNECTIONS = 4003
    INVALID_SIGNATURE = 4004


class ProtocolError(Exception):
    """消息协议异常。"""


def parse_message(raw: str) -> Dict[str, Any]:
    """解析客户端消息，非法则抛 ProtocolError。"""
    if raw is None:
        raise ProtocolError("消息为空")
    if len(raw.encode("utf-8")) > MAX_MESSAGE_BYTES:
        raise ProtocolError("消息超过 1MB")
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"非法 JSON: {e}") from e
    if not isinstance(msg, dict):
        raise ProtocolError("消息必须是 JSON 对象")
    if "type" not in msg:
        raise ProtocolError("消息缺少 type 字段")
    return msg


def build_message(msg_type: str | MessageType, **kwargs: Any) -> str:
    """构造服务端消息，自动加 server_ts。"""
    t = msg_type.value if isinstance(msg_type, MessageType) else msg_type
    payload: Dict[str, Any] = {"type": t, "server_ts": int(time.time()), **kwargs}
    return json.dumps(payload, ensure_ascii=False, default=_json_default)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"无法序列化: {type(obj)!r}")
