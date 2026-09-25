"""WebSocket 连接管理器 — 统一管理设备连接。"""

from __future__ import annotations

import asyncio
import logging
from typing import Dict, List

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """管理所有 WebSocket 连接（asyncio.Lock 保护并发写）。"""

    def __init__(self) -> None:
        self._connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def register(self, device_id: str, ws: WebSocket) -> None:
        """注册连接；同 device_id 旧连接会被踢掉。"""
        async with self._lock:
            old = self._connections.get(device_id)
            if old is not None and old is not ws:
                try:
                    await old.close(code=1000, reason="duplicate register")
                except Exception as e:  # noqa: BLE001 — 关闭失败不影响新注册
                    logger.warning("关闭旧连接失败 device=%s: %s", device_id, e)
            self._connections[device_id] = ws

    async def unregister(self, device_id: str) -> None:
        async with self._lock:
            self._connections.pop(device_id, None)

    async def send_to_device(self, device_id: str, msg: str) -> bool:
        """点对点推送；返回是否成功。"""
        ws = self._connections.get(device_id)
        if ws is None:
            return False
        try:
            await ws.send_text(msg)
            return True
        except Exception as e:  # noqa: BLE001 — 推送失败视为断开
            logger.warning("推送失败 device=%s: %s", device_id, e)
            await self.unregister(device_id)
            return False

    async def broadcast(self, msg: str) -> int:
        """广播给所有在线设备；返回成功推送数。"""
        device_ids = list(self._connections.keys())
        results = await asyncio.gather(
            *(self.send_to_device(did, msg) for did in device_ids),
            return_exceptions=False,
        )
        return sum(1 for ok in results if ok)

    def get_online_devices(self) -> List[str]:
        return list(self._connections.keys())

    def is_connected(self, device_id: str) -> bool:
        return device_id in self._connections

    def connection_count(self) -> int:
        return len(self._connections)
