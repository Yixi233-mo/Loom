"""REST /api/* — 对齐前端 src/contracts/index.ts 的 API 路径。"""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from integration.stack import HubStack
from observability.audit import get_audit
from observability.security import MAX_INPUT_CHARS


class SessionMessageIn(BaseModel):
    role: str = "user"
    content: str = ""

    @field_validator("content")
    @classmethod
    def _limit_content(cls, v: str) -> str:
        # 11.1 输入长度 ≤2000
        if len(v) > MAX_INPUT_CHARS:
            raise ValueError(f"消息超过长度上限 {MAX_INPUT_CHARS}")
        return v


class TriggerIn(BaseModel):
    workflowName: str = Field(alias="workflowName")
    device: str = "pc"
    traceId: Optional[str] = Field(default=None, alias="traceId")

    model_config = {"populate_by_name": True}


class UploadIn(BaseModel):
    name: str
    mime: str = "application/octet-stream"
    size: int = 0
    sourceDeviceId: Optional[str] = None
    content: Optional[str] = None


def _now() -> float:
    return time.time()


class ApiStore:
    """内存态：会话 / 文件（任务走 HubStack）。"""

    def __init__(self) -> None:
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.files: Dict[str, Dict[str, Any]] = {}

    def ensure_session(self, session_id: str, title: str = "新会话") -> Dict[str, Any]:
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "sessionId": session_id,
                "title": title,
                "status": "idle",
                "messages": [],
                "updatedAt": _now(),
                "draft": "",
            }
        return self.sessions[session_id]


def create_api_router(stack: HubStack, store: Optional[ApiStore] = None) -> APIRouter:
    st = store or ApiStore()
    st.ensure_session("sess-demo-1")
    router = APIRouter()

    # ---- 会话 ----
    @router.get("/api/sessions")
    def list_sessions() -> List[Dict[str, Any]]:
        return list(st.sessions.values())

    @router.post("/api/sessions")
    def create_session(payload: Dict[str, Any]) -> Dict[str, Any]:
        sid = payload.get("sessionId") or f"sess-{uuid.uuid4().hex[:8]}"
        s = st.ensure_session(sid, payload.get("title") or "新会话")
        return s

    @router.get("/api/sessions/{session_id}")
    def get_session(session_id: str) -> Dict[str, Any]:
        s = st.sessions.get(session_id)
        if not s:
            raise HTTPException(404, "session not found")
        return s

    @router.post("/api/sessions/{session_id}/messages")
    def append_message(session_id: str, body: SessionMessageIn) -> Dict[str, Any]:
        s = st.ensure_session(session_id)
        msg = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "role": body.role,
            "content": body.content,
            "createdAt": _now(),
        }
        s["messages"].append(msg)
        s["updatedAt"] = _now()
        get_audit().record(
            actor="api",
            action="session.message",
            resource=session_id,
            result="ok",
            role=body.role,
            size=len(body.content),
        )
        return msg

    # ---- 任务 ----
    @router.get("/api/tasks")
    def list_tasks(limit: int = 100) -> List[Dict[str, Any]]:
        out = []
        for t in stack.orch.list_tasks():
            out.append(
                {
                    "taskId": t["task_id"],
                    "workflowName": t.get("workflow"),
                    "device": t.get("device"),
                    "status": t["status"].value
                    if hasattr(t["status"], "value")
                    else str(t["status"]),
                    "assignedTo": t.get("assigned_to"),
                    "traceId": t.get("task_id"),
                    "createdAt": t.get("created_at"),
                    "updatedAt": t.get("created_at"),
                    "result": t.get("result"),
                    "error": t.get("error"),
                }
            )
        return out[-limit:] if limit and limit > 0 else out

    @router.get("/api/tasks/{task_id}")
    def get_task(task_id: str) -> Dict[str, Any]:
        try:
            t = stack.orch.get(task_id)
        except Exception as e:  # noqa: BLE001
            raise HTTPException(404, str(e)) from e
        return {
            "taskId": t["task_id"],
            "workflowName": t.get("workflow"),
            "status": t["status"].value
            if hasattr(t["status"], "value")
            else str(t["status"]),
            "assignedTo": t.get("assigned_to"),
            "result": t.get("result"),
            "error": t.get("error"),
        }

    @router.post("/api/tasks/trigger")
    async def trigger_task(body: TriggerIn) -> Dict[str, Any]:
        trace_id = body.traceId or f"api-{uuid.uuid4().hex[:8]}"
        task_id = await stack.submit_workflow_async(
            {"name": body.workflowName, "device": body.device},
            trace_id=trace_id,
        )
        rec = stack.orch.get(task_id)
        return {
            "taskId": task_id,
            "status": rec["status"].value
            if hasattr(rec["status"], "value")
            else str(rec["status"]),
            "traceId": trace_id,
        }

    # ---- Agent ----
    @router.get("/api/agents")
    def list_agents() -> List[Dict[str, Any]]:
        return [
            {
                "agentName": n,
                "status": "online",
                "capabilities": meta.get("capabilities", []),
                "degradationLevel": 0,
                "updatedAt": _now(),
            }
            for n, meta in stack.registry.agents.items()
        ]

    @router.get("/api/agents/{name}")
    def get_agent(name: str) -> Dict[str, Any]:
        if name not in stack.registry.agents:
            raise HTTPException(404, f"unknown agent {name}")
        return {
            "agentName": name,
            "status": "online",
            "capabilities": stack.registry.agents[name].get("capabilities", []),
            "degradationLevel": 0,
            "updatedAt": _now(),
        }

    # ---- 文件 ----
    @router.get("/api/files")
    def list_files() -> List[Dict[str, Any]]:
        return list(st.files.values())

    @router.post("/api/files/upload")
    def upload_file(body: UploadIn) -> Dict[str, Any]:
        fid = f"f-{uuid.uuid4().hex[:8]}"
        ref = {
            "fileId": fid,
            "name": body.name,
            "size": body.size,
            "mime": body.mime,
            "uri": f"hub://files/{fid}",
            "uploadedAt": _now(),
            "sourceDeviceId": body.sourceDeviceId,
        }
        st.files[fid] = ref
        return ref

    @router.delete("/api/files/{file_id}")
    def delete_file(file_id: str) -> Dict[str, Any]:
        if file_id not in st.files:
            raise HTTPException(404, "file not found")
        del st.files[file_id]
        return {"ok": True}

    @router.get("/api/stream")
    def stream_info() -> Dict[str, Any]:
        return {"ok": True, "hint": "实时事件走 WebSocket /ws；SSE 可接此通道"}

    return router


def mount_api(app: FastAPI, stack: HubStack) -> None:
    from api.errors import install_error_contract

    install_error_contract(app)
    from api.llm_routes import create_llm_router
    from llm.config import LLMConfigStore

    app.include_router(create_api_router(stack))
    llm_store = LLMConfigStore(Path(__file__).resolve().parent.parent / "plugins" / "llm_providers.json")
    app.include_router(create_llm_router(llm_store))
    from api.mcp_routes import mount_mcp_api
    mount_mcp_api(app)
    import os
    from pathlib import Path as _P

    from api.knowledge_routes import mount_knowledge_api
    from knowledge.store import KnowledgeStore
    kb_path = _P(os.environ.get("LOOM_KB_PATH", "plugins/knowledge.json"))
    mount_knowledge_api(app, KnowledgeStore(kb_path))
