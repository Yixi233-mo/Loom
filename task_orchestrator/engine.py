"""Task Orchestrator — 任务分发与状态跟踪。

状态机：pending → assigned → running → done / failed
       pending → assigned（设备上线后分发）
       assigned/running → failed（超时 5min 或显式失败）

Task Schema：
{
  "task_id": "uuid",
  "workflow": "string",
  "device": "pc | tablet | mobile | any",
  "status": "pending | assigned | running | done | failed",
  "assigned_to": "device_id",
  "created_at": 1234567890,
  "result": {}
}
"""

from __future__ import annotations

import time
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from device_mesh.registry import DeviceMesh

DEFAULT_TIMEOUT_SECONDS = 300.0  # 5min


class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


# 合法状态迁移表
_TRANSITIONS: Dict[TaskStatus, set] = {
    TaskStatus.PENDING: {TaskStatus.ASSIGNED, TaskStatus.FAILED},
    TaskStatus.ASSIGNED: {TaskStatus.RUNNING, TaskStatus.FAILED},
    TaskStatus.RUNNING: {TaskStatus.DONE, TaskStatus.FAILED},
    TaskStatus.DONE: set(),
    TaskStatus.FAILED: set(),
}


class TaskError(Exception):
    """任务不存在或操作非法。"""


class InvalidTransitionError(TaskError):
    """非法状态迁移。"""

    def __init__(self, task_id: str, current: TaskStatus, target: TaskStatus):
        self.task_id = task_id
        self.current = current
        self.target = target
        super().__init__(
            f"非法状态迁移: task={task_id} {current.value} → {target.value}"
        )


class TaskOrchestrator:
    """任务编排：提交、路由、排队、超时。"""

    def __init__(
        self,
        device_mesh: DeviceMesh,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self.mesh = device_mesh
        self.timeout_seconds = timeout_seconds
        self.tasks: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------
    # 查询
    # ------------------------------------------------------------------

    def get(self, task_id: str) -> Dict[str, Any]:
        if task_id not in self.tasks:
            raise TaskError(f"未知任务: {task_id}")
        return self.tasks[task_id]

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Dict[str, Any]]:
        items = list(self.tasks.values())
        if status is not None:
            items = [t for t in items if t["status"] == status]
        return items

    def pending_ids(self) -> List[str]:
        return [tid for tid, t in self.tasks.items() if t["status"] == TaskStatus.PENDING]

    # ------------------------------------------------------------------
    # 提交与分发
    # ------------------------------------------------------------------

    def submit(self, workflow: Dict[str, Any]) -> str:
        """提交任务。

        - 成功路由到设备 → status=assigned, assigned_to=device_id
        - 无可用设备 → status=pending（进队列，等待设备上线后分发）
        """
        task_id = str(uuid.uuid4())
        now = time.time()
        record: Dict[str, Any] = {
            "task_id": task_id,
            "workflow": workflow.get("name", ""),
            "device": workflow.get("device", "any"),
            "status": TaskStatus.PENDING,
            "assigned_to": None,
            "created_at": now,
            "result": {},
            "error": None,
        }
        self.tasks[task_id] = record

        device_id = self._route(record)
        if device_id:
            self._assign(task_id, device_id)
        return task_id

    def dispatch_pending(self) -> List[str]:
        """尝试为所有 pending 任务分发设备（设备上线后调用）。

        返回本次成功分发的 task_id 列表。
        """
        dispatched: List[str] = []
        for task_id in self.pending_ids():
            record = self.tasks[task_id]
            device_id = self._route(record)
            if device_id:
                self._assign(task_id, device_id)
                dispatched.append(task_id)
        return dispatched

    def _route(self, record: Dict[str, Any]) -> Optional[str]:
        return self.mesh.route(required_device=record.get("device", "any"))

    def _assign(self, task_id: str, device_id: str) -> None:
        record = self.tasks[task_id]
        self._transition(task_id, TaskStatus.ASSIGNED)
        record["assigned_to"] = device_id

    # ------------------------------------------------------------------
    # 状态迁移
    # ------------------------------------------------------------------

    def _transition(self, task_id: str, target: TaskStatus) -> None:
        record = self.get(task_id)
        current = record["status"]
        if target not in _TRANSITIONS[current]:
            raise InvalidTransitionError(task_id, current, target)
        record["status"] = target

    def mark_running(self, task_id: str) -> None:
        self._transition(task_id, TaskStatus.RUNNING)

    def mark_done(self, task_id: str, result: Optional[Dict[str, Any]] = None) -> None:
        record = self.get(task_id)
        self._transition(task_id, TaskStatus.DONE)
        if result is not None:
            record["result"] = result

    def mark_failed(self, task_id: str, error: str = "") -> None:
        record = self.get(task_id)
        self._transition(task_id, TaskStatus.FAILED)
        if error:
            record["error"] = error

    # ------------------------------------------------------------------
    # 超时
    # ------------------------------------------------------------------

    def check_timeouts(self, now: Optional[float] = None) -> List[str]:
        """检查超时任务：assigned / running 超过 timeout_seconds → failed。

        返回本次标记为 failed 的 task_id 列表。
        """
        if now is None:
            now = time.time()
        timed_out: List[str] = []
        for task_id, record in self.tasks.items():
            if record["status"] not in (TaskStatus.ASSIGNED, TaskStatus.RUNNING):
                continue
            if now - record["created_at"] >= self.timeout_seconds:
                self._transition(task_id, TaskStatus.FAILED)
                record["error"] = f"超时 {self.timeout_seconds}s"
                timed_out.append(task_id)
        return timed_out
