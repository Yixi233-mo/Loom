"""HubStack — 串联 AgentRegistry / TaskOrchestrator / DeviceMesh / SyncEngine / ConnectionManager。

职责：
- Hub Graph workflow 路径 → TaskOrchestrator
- SyncEngine on_broadcast → ConnectionManager.sync_broadcast
- WS result → 任务状态回写
- 结构化日志埋点 + Agent 降级链
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

from agent_hub.degrade import DegradationChain, default_chain
from agent_hub.registry import AgentRegistry
from device_mesh.connection_manager import ConnectionManager
from device_mesh.heartbeat import HeartbeatMonitor
from device_mesh.protocol import build_message
from device_mesh.registry import DeviceMesh
from observability.logging import StructuredLogger, get_logger, new_trace_id
from sync.sync_engine import SyncEngine
from task_orchestrator.engine import TaskOrchestrator, TaskStatus


def _status_str(status: Any) -> str:
    return status.value if isinstance(status, TaskStatus) else str(status)


class HubStack:
    """进程内全栈运行时（可挂到 FastAPI WebSocket 服务）。"""

    def __init__(
        self,
        tools: Optional[Dict[str, Any]] = None,
        agents: Optional[Dict[str, Any]] = None,
        secret: str = "dev-secret",
        logger: Optional[StructuredLogger] = None,
        degrade_chain: Optional[DegradationChain] = None,
    ) -> None:
        self.mesh = DeviceMesh()
        self.registry = AgentRegistry()
        self.orch = TaskOrchestrator(self.mesh)
        self.cm = ConnectionManager()
        self.monitor = HeartbeatMonitor(self.cm)
        self.sync = SyncEngine(on_broadcast=self._on_sync_event)
        self.tools = tools or {}
        self.agents = agents or {}
        self.secret = secret
        self.trace_log: List[Dict[str, Any]] = []
        self.log = logger or get_logger()
        self.degrade = degrade_chain or default_chain()

        for name, fn in self.agents.items():
            async def _adapter(prompt: str, _fn=fn, _name=name, **kwargs: Any) -> Any:
                return _fn(prompt)

            self.registry.register(name, _adapter, ["*"])

    async def invoke_agent_degraded(
        self,
        agent_name: str,
        prompt: str,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """带降级链的 Agent 调用：失败自动切换并记账。"""
        tid = trace_id or new_trace_id()
        result = await self.degrade.run(prompt, trace_id=tid)
        self.log.emit(
            "agent.degraded",
            trace_id=tid,
            agent_name=result.provider,
            degradation_level=result.degradation_level,
            task_status="done",
        )
        self._trace(
            tid,
            "degrade",
            requested=agent_name,
            provider=result.provider,
            level=result.degradation_level,
        )
        return {
            "provider": result.provider,
            "degradation_level": result.degradation_level,
            "value": result.value,
            "errors": result.errors,
        }

    async def _on_sync_event(self, event: str, data: Dict[str, Any]) -> None:
        payload = build_message("sync_broadcast", event=event, data=data)
        await self.cm.broadcast(payload)

    def _trace(self, trace_id: str, stage: str, **detail: Any) -> None:
        self.trace_log.append({"trace_id": trace_id, "stage": stage, **detail})
        self.log.emit(f"hub.{stage}", trace_id=trace_id, **detail)

    async def submit_workflow_async(
        self,
        workflow: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> str:
        trace_id = trace_id or new_trace_id()
        wf_name = (workflow or {}).get("name") or "adhoc"
        with self.log.span(
            "hub.submit",
            trace_id=trace_id,
            workflow_name=wf_name,
            device_id=(workflow or {}).get("device"),
        ) as span:
            task_id = self.orch.submit(workflow)
            record = self.orch.get(task_id)
            status = _status_str(record["status"])
            span.set(task_id=task_id, task_status=status, assigned_to=record.get("assigned_to"))
            self._trace(
                trace_id,
                "submit",
                task_id=task_id,
                status=status,
                assigned_to=record.get("assigned_to"),
                workflow_name=wf_name,
            )
            if record["status"] == TaskStatus.ASSIGNED:
                await self.dispatch_task_to_device_async(task_id, trace_id=trace_id)
        return task_id

    async def dispatch_task_to_device_async(
        self, task_id: str, trace_id: Optional[str] = None
    ) -> bool:
        trace_id = trace_id or task_id
        record = self.orch.get(task_id)
        device_id = record.get("assigned_to")
        wf_name = record.get("workflow")
        with self.log.span(
            "hub.dispatch",
            trace_id=trace_id,
            device_id=device_id,
            workflow_name=wf_name,
        ) as span:
            if not device_id:
                span.set(task_status="pending")
                return False
            if record["status"] == TaskStatus.ASSIGNED:
                self.orch.mark_running(task_id)
            msg = build_message(
                "task_dispatch",
                task_id=task_id,
                workflow=wf_name,
                trace_id=trace_id,
            )
            ok = await self.cm.send_to_device(device_id, msg)
            span.set(task_id=task_id, task_status=_status_str(self.orch.get(task_id)["status"]), sent=bool(ok))
            self._trace(trace_id, "dispatch", device=device_id, task_id=task_id, sent=bool(ok))
            return bool(ok)

    async def complete_task_async(
        self,
        task_id: str,
        status: str,
        output: Any = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        trace_id = trace_id or task_id
        record = self.orch.get(task_id)
        wf_name = record.get("workflow")
        with self.log.span(
            "hub.complete",
            trace_id=trace_id,
            device_id=record.get("assigned_to"),
            workflow_name=wf_name,
            task_status=status,
        ) as span:
            if status == "done":
                self.orch.mark_done(task_id, {"output": output})
            else:
                self.orch.mark_failed(task_id, str(output or status))
            summary = {
                "task_id": task_id,
                "status": status,
                "output": output,
                "trace_id": trace_id,
                "device": record.get("assigned_to"),
            }
            await self.sync.put(key=f"task:{task_id}:result", value=summary, device_id="hub")
            span.set(task_id=task_id)
            self._trace(trace_id, "complete", task_id=task_id, status=status)
        return summary

    async def dispatch_pending_async(self) -> List[str]:
        ids = self.orch.dispatch_pending()
        for tid in ids:
            await self.dispatch_task_to_device_async(tid)
        return ids

    def submit_workflow(
        self, workflow: Dict[str, Any], trace_id: Optional[str] = None
    ) -> str:
        return asyncio.run(self.submit_workflow_async(workflow, trace_id))

    def complete_task(
        self,
        task_id: str,
        status: str,
        output: Any = None,
        trace_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return asyncio.run(self.complete_task_async(task_id, status, output, trace_id))

    def dispatch_pending(self) -> List[str]:
        return asyncio.run(self.dispatch_pending_async())
