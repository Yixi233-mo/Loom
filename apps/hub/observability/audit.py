"""审计日志 — 谁 / 何时 / 调用什么 / 结果（N16 11.9）。"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class AuditEntry:
    ts: float
    actor: str
    action: str
    resource: str = ""
    result: str = "ok"
    trace_id: str = ""
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ts": self.ts,
            "actor": self.actor,
            "action": self.action,
            "resource": self.resource,
            "result": self.result,
            "trace_id": self.trace_id,
            "detail": self.detail,
        }


class AuditLog:
    """线程安全审计缓冲 + 可选落盘。"""

    def __init__(self, path: Optional[str | Path] = None, max_records: int = 2000) -> None:
        self.entries: List[AuditEntry] = []
        self.path = Path(path) if path else None
        self.max_records = max_records
        self._lock = threading.Lock()

    def record(
        self,
        actor: str,
        action: str,
        resource: str = "",
        result: str = "ok",
        trace_id: str = "",
        **detail: Any,
    ) -> AuditEntry:
        entry = AuditEntry(
            ts=time.time(),
            actor=actor or "unknown",
            action=action,
            resource=resource,
            result=result,
            trace_id=trace_id or f"tr-{uuid.uuid4().hex[:12]}",
            detail=detail,
        )
        with self._lock:
            self.entries.append(entry)
            if len(self.entries) > self.max_records:
                self.entries = self.entries[-self.max_records :]
            if self.path:
                try:
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    with self.path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
                except OSError:
                    pass
        return entry

    def query(
        self,
        actor: Optional[str] = None,
        action: Optional[str] = None,
        result: Optional[str] = None,
    ) -> List[AuditEntry]:
        with self._lock:
            out = self.entries
            if actor is not None:
                out = [e for e in out if e.actor == actor]
            if action is not None:
                out = [e for e in out if e.action == action]
            if result is not None:
                out = [e for e in out if e.result == result]
            return list(out)


_default_audit = AuditLog()


def get_audit() -> AuditLog:
    return _default_audit


def set_audit(log: AuditLog) -> None:
    global _default_audit
    _default_audit = log


def audit(actor: str, action: str, **kw: Any) -> AuditEntry:
    return _default_audit.record(actor, action, **kw)
