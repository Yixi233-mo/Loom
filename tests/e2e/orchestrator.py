"""E2E 编排胶水 — 串联 DeviceMesh / TaskOrchestrator / WorkflowRunner / SyncEngine。

场景：手机触发 → Hub 路由到 PC → PC 执行工作流 → 结果广播（平板/手机可见）。
全链路携带 trace_id。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from device_mesh.registry import DeviceMesh
from sync.sync_engine import SyncEngine
from task_orchestrator.engine import TaskOrchestrator, TaskStatus


@dataclass
class TraceEvent:
    trace_id: str
    stage: str  # trigger | route | execute | broadcast | view
    device: str
    detail: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)


class E2EOrchestrator:
    """最小跨端闭环编排器（测试/演示用，纯同步）。"""

    def __init__(
        self,
        workflow_yaml: str,
        tools: dict[str, Any],
        agents: dict[str, Any] | None = None,
    ) -> None:
        self.mesh = DeviceMesh()
        self.orch = TaskOrchestrator(self.mesh)
        self.sync = SyncEngine()
        self.events: list[TraceEvent] = []
        self.workflow_yaml = workflow_yaml
        self.tools = tools
        self.agents = agents or {}
        self.results: dict[str, Any] = {}

    def _put(self, key: str, value: Any, device_id: str) -> None:
        # 同步直写（跳过 async 广播；E2E 断言走 changes/all_keys）
        self.sync._put_sync(key, value, device_id)

    def _emit(self, trace_id: str, stage: str, device: str, **detail: Any) -> None:
        self.events.append(TraceEvent(trace_id, stage, device, detail))
        self._put(
            key=f"trace:{trace_id}:{stage}:{len(self.events)}",
            value={"stage": stage, "device": device, "trace_id": trace_id, **detail},
            device_id=device,
        )

    def register_device(
        self, device_id: str, device_type: str, capabilities: list[str]
    ) -> None:
        self.mesh.register(device_id, device_type, capabilities)

    def trigger_from_mobile(
        self,
        mobile_id: str,
        payload: dict[str, Any],
        trace_id: str | None = None,
    ) -> str:
        """手机触发任务，返回 trace_id。"""
        trace_id = trace_id or str(uuid.uuid4())
        self._emit(trace_id, "trigger", mobile_id, payload=payload)

        workflow = {
            "name": payload.get("workflow", "mobile_to_pc_pdf"),
            "device": "pc",
        }
        task_id = self.orch.submit(workflow)
        record = self.orch.get(task_id)
        status = record["status"]
        status_s = status.value if isinstance(status, TaskStatus) else str(status)
        self._emit(
            trace_id,
            "route",
            record.get("assigned_to") or "queue",
            task_id=task_id,
            status=status_s,
            assigned_to=record.get("assigned_to"),
        )

        if record["status"] == TaskStatus.PENDING:
            self.results[trace_id] = {"task_id": task_id, "status": "pending"}
            return trace_id

        pc_id = record["assigned_to"]
        self.orch.mark_running(task_id)
        self._emit(trace_id, "execute", pc_id, task_id=task_id)

        from plugins.example.workflow_runner import WorkflowRunner

        runner = WorkflowRunner(tools=self.tools, agents=self.agents)
        result = runner.run_yaml(self.workflow_yaml)
        if result.get("status") == "done":
            self.orch.mark_done(task_id, result)
        else:
            self.orch.mark_failed(task_id, result.get("error", "workflow failed"))
        self._emit(
            trace_id,
            "execute",
            pc_id,
            task_id=task_id,
            status=result.get("status"),
            output=result.get("steps"),
        )

        summary = {
            "trace_id": trace_id,
            "task_id": task_id,
            "status": result.get("status"),
            "steps": result.get("steps"),
        }
        self._put(key=f"task:{task_id}:result", value=summary, device_id=pc_id)
        for device_info in self.mesh.list_devices():
            did = device_info["device_id"]
            if did == pc_id:
                continue
            self._emit(trace_id, "broadcast", did, task_id=task_id)
            self._emit(trace_id, "view", did, task_id=task_id, summary=summary)

        self.results[trace_id] = summary
        return trace_id

    def events_for(self, trace_id: str) -> list[TraceEvent]:
        return [e for e in self.events if e.trace_id == trace_id]

    def stages(self, trace_id: str) -> list[str]:
        return [e.stage for e in self.events_for(trace_id)]
