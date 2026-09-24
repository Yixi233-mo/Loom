"""结构化 JSON 日志 — 全链路可追溯。

必埋字段（方案 · 可观测性）：
  trace_id / device_id / agent_name / workflow_name / dsl_version
  task_status / tokens_used / latency_ms / degradation_level

用法：
  log = StructuredLogger()
  with log.span("hub.submit", trace_id=tid, workflow_name="daily_report") as s:
      ...
      s.set(agent_name="builtin_rag", task_status="done")
  records = log.records_for(trace_id)
"""

from __future__ import annotations

import json
import sys
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional

# 降级档位：0=全功能, 1=备用Agent, 2=规则
DEG_FULL = 0
DEG_FALLBACK_AGENT = 1
DEG_RULES = 2


def new_trace_id() -> str:
    return f"tr-{uuid.uuid4().hex[:12]}"


@dataclass
class LogRecord:
    ts: float
    event: str
    trace_id: str
    device_id: Optional[str] = None
    agent_name: Optional[str] = None
    workflow_name: Optional[str] = None
    dsl_version: Optional[str] = None
    task_status: Optional[str] = None
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    degradation_level: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "ts": self.ts,
            "event": self.event,
            "trace_id": self.trace_id,
        }
        for k in (
            "device_id",
            "agent_name",
            "workflow_name",
            "dsl_version",
            "task_status",
            "tokens_used",
            "latency_ms",
            "degradation_level",
        ):
            v = getattr(self, k)
            if v is not None:
                d[k] = v
        if self.extra:
            d.update(self.extra)
        return d


class Span:
    """一次可计时的调用片段，结束时落一条日志。"""

    def __init__(self, logger: "StructuredLogger", event: str, trace_id: str, **fields: Any):
        self.logger = logger
        self.event = event
        self.trace_id = trace_id
        self.fields = dict(fields)
        self.started = time.time()
        self._finished = False

    def set(self, **fields: Any) -> "Span":
        self.fields.update(fields)
        return self

    def finish(self, status: Optional[str] = None) -> LogRecord:
        if self._finished:
            return self.logger.records[-1]
        latency_ms = (time.time() - self.started) * 1000.0
        self.fields.setdefault("latency_ms", round(latency_ms, 3))
        if status is not None:
            self.fields.setdefault("task_status", status)
        rec = self.logger.emit(self.event, trace_id=self.trace_id, **self.fields)
        self._finished = True
        return rec


class StructuredLogger:
    """线程安全的 JSON 行日志收集器（stdout + 内存缓冲，便于测试回放）。"""

    def __init__(
        self,
        stream: Optional[Any] = None,
        echo: bool = False,
        max_records: int = 5000,
    ) -> None:
        self.records: List[LogRecord] = []
        self.stream = stream
        self.echo = echo
        self.max_records = max_records
        self._lock = threading.Lock()

    def emit(self, event: str, trace_id: str, **fields: Any) -> LogRecord:
        known = {}
        extra = {}
        for k, v in fields.items():
            if v is None:
                continue
            if k in (
                "device_id",
                "agent_name",
                "workflow_name",
                "dsl_version",
                "task_status",
                "tokens_used",
                "latency_ms",
                "degradation_level",
            ):
                known[k] = v
            else:
                extra[k] = v
        rec = LogRecord(
            ts=time.time(),
            event=event,
            trace_id=trace_id,
            extra=extra,
            **known,
        )
        with self._lock:
            self.records.append(rec)
            if len(self.records) > self.max_records:
                self.records = self.records[-self.max_records :]
            if self.echo:
                line = json.dumps(rec.to_dict(), ensure_ascii=False)
                print(line, file=self.stream or sys.stdout, flush=True)
        return rec

    @contextmanager
    def span(self, event: str, trace_id: Optional[str] = None, **fields: Any) -> Iterator[Span]:
        tid = trace_id or fields.pop("trace_id", None) or new_trace_id()
        s = Span(self, event, tid, **fields)
        try:
            yield s
        finally:
            s.finish()

    def records_for(self, trace_id: str) -> List[LogRecord]:
        with self._lock:
            return [r for r in self.records if r.trace_id == trace_id]

    def chain_for(self, trace_id: str) -> List[str]:
        """返回该 trace 的事件名序列，用于验收「完整追溯」。"""
        return [r.event for r in self.records_for(trace_id)]


# 进程内默认实例（可替换/清空）
_default_logger = StructuredLogger()


def get_logger() -> StructuredLogger:
    return _default_logger


def set_logger(logger: StructuredLogger) -> None:
    global _default_logger
    _default_logger = logger


def log_event(event: str, trace_id: str, **fields: Any) -> LogRecord:
    return _default_logger.emit(event, trace_id, **fields)
