"""心跳检测 — 后台扫描，超时踢出。"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class HeartbeatMonitor:
    """后台心跳检测：超过 timeout 未心跳 → unregister。"""

    def __init__(
        self,
        connection_manager,
        interval: float = 15.0,
        timeout: float = 60.0,
        time_fn: Optional[Callable[[], float]] = None,
    ) -> None:
        self.cm = connection_manager
        self.interval = interval
        self.timeout = timeout
        self._time_fn = time_fn or time.time
        self._last_seen: Dict[str, float] = {}
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

    def update(self, device_id: str) -> None:
        self._last_seen[device_id] = self._time_fn()

    def remove(self, device_id: str) -> None:
        self._last_seen.pop(device_id, None)

    def last_seen(self, device_id: str) -> Optional[float]:
        return self._last_seen.get(device_id)

    async def scan_once(self) -> list[str]:
        now = self._time_fn()
        expired = [
            did for did, ts in self._last_seen.items() if now - ts > self.timeout
        ]
        for did in expired:
            logger.info("心跳超时，踢出设备: %s", did)
            self._last_seen.pop(did, None)
            await self.cm.unregister(did)
        return expired

    async def _scan_loop(self) -> None:
        while not self._stopped:
            try:
                await asyncio.sleep(self.interval)
                if self._stopped:
                    break
                await self.scan_once()
            except asyncio.CancelledError:
                raise
            except Exception as e:  # noqa: BLE001
                logger.error("心跳扫描异常: %s", e, exc_info=True)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopped = False
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                # 无运行中事件循环时不启动后台任务（单测/同步上下文）
                return
            self._task = loop.create_task(self._scan_loop(), name="heartbeat-monitor")

    async def stop(self) -> None:
        self._stopped = True
        task = self._task
        self._task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001
                pass

    def stop_sync(self) -> None:
        """同步上下文清理：仅标记停止并尝试取消。"""
        self._stopped = True
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
