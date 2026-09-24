"""Device Mesh — 设备注册与路由。

设备注册 Schema：
{
  "device_id": "string",
  "device_type": "pc | tablet | mobile",
  "capabilities": ["file.read", "shell.exec", "camera", "notifications"],
  "online": true,
  "last_seen": 1234567890
}
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

DEVICE_TYPES = {"pc", "tablet", "mobile"}


class DeviceMeshError(Exception):
    """设备注册信息非法。"""


class DeviceMesh:
    """设备网格：注册、在线状态、按类型 + 能力路由。"""

    def __init__(self) -> None:
        self.devices: Dict[str, Dict[str, Any]] = {}

    def register(
        self,
        device_id: str,
        device_type: str,
        capabilities: List[str],
    ) -> Dict[str, Any]:
        """注册设备（同 id 覆盖并刷新 online/last_seen）。"""
        if not device_id:
            raise DeviceMeshError("device_id 不能为空")
        if device_type not in DEVICE_TYPES:
            raise DeviceMeshError(f"非法 device_type: {device_type!r}，应为 {sorted(DEVICE_TYPES)}")
        self.devices[device_id] = {
            "device_id": device_id,
            "device_type": device_type,
            "capabilities": list(capabilities or []),
            "online": True,
            "last_seen": time.time(),
        }
        return self.devices[device_id]

    def unregister(self, device_id: str) -> None:
        self.devices.pop(device_id, None)

    def get(self, device_id: str) -> Optional[Dict[str, Any]]:
        return self.devices.get(device_id)

    def list_devices(self) -> List[Dict[str, Any]]:
        return list(self.devices.values())

    def set_online(self, device_id: str, online: bool) -> None:
        """标记设备上下线；更新 last_seen。"""
        if device_id not in self.devices:
            raise DeviceMeshError(f"未注册设备: {device_id}")
        self.devices[device_id]["online"] = online
        self.devices[device_id]["last_seen"] = time.time()

    def heartbeat(self, device_id: str) -> None:
        """刷新 last_seen，确保在线。"""
        if device_id not in self.devices:
            raise DeviceMeshError(f"未注册设备: {device_id}")
        self.devices[device_id]["online"] = True
        self.devices[device_id]["last_seen"] = time.time()

    def route(
        self,
        required_device: str = "any",
        required_cap: Optional[str] = None,
    ) -> Optional[str]:
        """按设备类型 + 能力路由，返回 device_id；无可用设备返回 None。

        - required_device: pc | tablet | mobile | any
        - required_cap: 可选能力标签，如 shell.exec
        - 仅考虑 online 设备，选 last_seen 最新的
        """
        if required_device != "any" and required_device not in DEVICE_TYPES:
            return None

        candidates: List[Dict[str, Any]] = []
        for d in self.devices.values():
            if not d["online"]:
                continue
            if required_device != "any" and d["device_type"] != required_device:
                continue
            if required_cap and required_cap not in d["capabilities"]:
                continue
            candidates.append(d)

        if not candidates:
            return None
        return max(candidates, key=lambda x: x["last_seen"])["device_id"]
