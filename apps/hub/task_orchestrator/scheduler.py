"""cron 触发调度 — 最小 5 段表达式 + 到点触发。

字段：分 时 日 月 周（周 0=周日）
支持：数字 / * / 列表 a,b / 范围 a-b / 步进
"""

from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

_FIELD_RE = re.compile(r"^(?:\d+|\*)(?:-(?:\d+|\*))?(?:/\d+)?(?:,(?:\d+|\*)(?:-(?:\d+|\*))?(?:/\d+)?)*$")


def parse_field(expr: str, lo: int, hi: int) -> Set[int]:
    """解析单个 cron 字段为允许值集合。"""
    expr = expr.strip()
    if not expr or not _FIELD_RE.match(expr):
        raise ValueError(f"非法 cron 字段: {expr!r}")
    values: Set[int] = set()
    for part in expr.split(","):
        part = part.strip()
        step = 1
        if "/" in part:
            base, step_s = part.split("/", 1)
            step = int(step_s)
            if step <= 0:
                raise ValueError(f"步进必须>0: {part}")
            part = base
        if part == "*":
            start, end = lo, hi
        elif "-" in part:
            a, b = part.split("-", 1)
            start = lo if a == "*" else int(a)
            end = hi if b == "*" else int(b)
        else:
            start = end = int(part)
        if start < lo or end > hi or start > end:
            raise ValueError(f"越界 cron 字段: {expr!r}")
        values.update(range(start, end + 1, step))
    return values


@dataclass(frozen=True)
class CronExpr:
    minute: frozenset[int]
    hour: frozenset[int]
    day: frozenset[int]
    month: frozenset[int]
    weekday: frozenset[int]

    def matches(self, dt: datetime) -> bool:
        return (
            dt.minute in self.minute
            and dt.hour in self.hour
            and dt.day in self.day
            and dt.month in self.month
            and dt.weekday() % 7 in self.weekday  # 0=周一→转 0=周日
        )


def parse_cron(expr: str) -> CronExpr:
    """解析 `分 时 日 月 周` 五段表达式。"""
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"cron 需 5 段: {expr!r}")
    # 周：python weekday 0=周一；cron 0=周日
    wd = parse_field(parts[4], 0, 7)
    wd = {((d - 1) % 7) for d in wd}  # 0/7→6(周日)... 换算见 matches
    # 统一存 cron 原义：0=周日
    wd_raw = parse_field(parts[4], 0, 7)
    wd_norm = {(d % 7) for d in wd_raw}

    return CronExpr(
        minute=frozenset(parse_field(parts[0], 0, 59)),
        hour=frozenset(parse_field(parts[1], 0, 23)),
        day=frozenset(parse_field(parts[2], 1, 31)),
        month=frozenset(parse_field(parts[3], 1, 12)),
        weekday=frozenset(wd_norm),
    )


# 修正 weekday 匹配：datetime.weekday(): Mon=0..Sun=6
# cron: Sun=0..Sat=6 → map cron_d -> py_d = (cron_d + 6) % 7


def _cron_weekday_match(self: CronExpr, dt: datetime) -> bool:
    # CronExpr.matches 里 weekday 为 cron 语义（0=周日）
    py = dt.weekday()  # Mon=0 .. Sun=6
    cron_d = (py + 1) % 7  # Sun=0 .. Sat=6
    return (
        dt.minute in self.minute
        and dt.hour in self.hour
        and dt.day in self.day
        and dt.month in self.month
        and cron_d in self.weekday
    )


# 覆盖 matches 的 weekday 语义
def _matches(self: CronExpr, dt: datetime) -> bool:
    return _cron_weekday_match(self, dt)


CronExpr.matches = _matches  # type: ignore[method-assign]


@dataclass
class CronJob:
    name: str
    cron_expr: str
    payload: Dict[str, Any] = field(default_factory=dict)
    _parsed: Optional[CronExpr] = field(default=None, repr=False)

    def parsed(self) -> CronExpr:
        if self._parsed is None:
            self._parsed = parse_cron(self.cron_expr)
        return self._parsed

    def set_expr(self, expr: str) -> None:
        """热更新表达式。"""
        self.cron_expr = expr
        self._parsed = None

    def due(self, dt: datetime) -> bool:
        return self.parsed().matches(dt)


class TriggerScheduler:
    """扫描 CronJob，到点调用 fire(name, payload)。"""

    def __init__(self, fire: Callable[[str, Dict[str, Any]], Any], tick_seconds: float = 1.0):
        self.jobs: Dict[str, CronJob] = {}
        self.fire = fire
        self.tick_seconds = tick_seconds
        self._task: Optional[asyncio.Task] = None
        self._stopped = False
        self.fired_log: List[str] = []

    def add_or_update(self, name: str, cron_expr: str, payload: Optional[Dict[str, Any]] = None) -> CronJob:
        """新增或热更新 cron 任务。"""
        job = self.jobs.get(name)
        if job is None:
            job = CronJob(name=name, cron_expr=cron_expr, payload=payload or {})
            self.jobs[name] = job
        else:
            job.set_expr(cron_expr)
            if payload is not None:
                job.payload = payload
        logger.info("cron 任务登记/更新: %s -> %s", name, cron_expr)
        return job

    def remove(self, name: str) -> None:
        self.jobs.pop(name, None)

    def tick(self, now: Optional[datetime] = None) -> List[str]:
        """推进一次调度；返回本次触发的任务名。"""
        dt = now or datetime.now()
        fired: List[str] = []
        for job in list(self.jobs.values()):
            if job.due(dt):
                self.fired_log.append(job.name)
                self.fire(job.name, job.payload)
                fired.append(job.name)
        return fired

    async def _loop(self) -> None:
        while not self._stopped:
            self.tick()
            await asyncio.sleep(self.tick_seconds)

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._stopped = False
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            self._task = loop.create_task(self._loop(), name="trigger-scheduler")

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


def load_workflows_cron(dir_path: str) -> List[CronJob]:
    """从 workflow 目录提取 cron 型 trigger 的任务定义。"""
    from pathlib import Path

    import yaml

    jobs: List[CronJob] = []
    root = Path(dir_path)
    if not root.exists():
        return jobs
    for p in sorted(root.glob("*.yaml")):
        try:
            spec = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        except Exception:  # noqa: BLE001
            continue
        trig = spec.get("trigger") or {}
        if trig.get("type") != "cron" or not trig.get("cron"):
            continue
        jobs.append(
            CronJob(
                name=spec.get("name") or p.stem,
                cron_expr=str(trig["cron"]),
                payload={"workflow": spec.get("name") or p.stem, "device": spec.get("device", "any")},
            )
        )
    return jobs
