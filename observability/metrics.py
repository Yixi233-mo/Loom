"""可观测指标 + Prometheus /metrics（N16 10.1–10.7）。"""

from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List

# 简单直方图桶（延迟 ms）
_LAT_BUCKETS = (50, 100, 250, 500, 1000, 2500, 5000, 10000, 30000)


@dataclass
class Metrics:
    """进程内指标登记表。"""

    started_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    counters: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    gauges: Dict[str, float] = field(default_factory=dict)
    latency_sum_ms: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    latency_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    latency_buckets: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(lambda: [0] * len(_LAT_BUCKETS))
    )

    def inc(self, name: str, value: float = 1.0, **labels: str) -> None:
        key = _key(name, labels)
        with self._lock:
            self.counters[key] += value

    def set_gauge(self, name: str, value: float, **labels: str) -> None:
        key = _key(name, labels)
        with self._lock:
            self.gauges[key] = value

    def observe_ms(self, name: str, ms: float, **labels: str) -> None:
        key = _key(name, labels)
        with self._lock:
            self.latency_sum_ms[key] += ms
            self.latency_count[key] += 1
            buckets = self.latency_buckets[key]
            for i, bound in enumerate(_LAT_BUCKETS):
                if ms <= bound:
                    buckets[i] += 1

    def task_result(self, status: str, latency_ms: float = 0.0, tokens: int = 0) -> None:
        """10.4 任务 / 成功率 / P95(近似) / Token。"""
        self.inc("loom_tasks_total", status=status)
        self.observe_ms("loom_task_latency_ms", latency_ms)
        if tokens:
            self.inc("loom_tokens_total", tokens)

    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            tasks = sum(v for k, v in self.counters.items() if k.startswith("loom_tasks_total"))
            # 成功率
            ok = 0.0
            fail = 0.0
            for k, v in self.counters.items():
                if "loom_tasks_total" in k and "status=done" in k:
                    ok += v
                elif "loom_tasks_total" in k and "status=failed" in k:
                    fail += v
            rate = (ok / (ok + fail) * 100.0) if (ok + fail) else 100.0
            # 近似 P95：桶累计
            p95 = _approx_p95(self.latency_buckets, self.latency_count)
            tokens = sum(v for k, v in self.counters.items() if "loom_tokens_total" in k)
            return {
                "uptime_s": time.time() - self.started_at,
                "tasks_total": tasks,
                "success_rate_pct": round(rate, 2),
                "p95_latency_ms": p95,
                "tokens_total": tokens,
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
            }

    def to_prometheus(self) -> str:
        """10.7 文本格式 /metrics。"""
        lines: List[str] = []
        lines.append("# HELP loom_up Loom process up")
        lines.append("# TYPE loom_up gauge")
        lines.append("loom_up 1")
        snap = self.snapshot()
        lines.append("# HELP loom_tasks_total Task outcomes")
        lines.append("# TYPE loom_tasks_total counter")
        for k, v in snap["counters"].items():
            if k.startswith("loom_tasks_total"):
                lines.append(f"{_prom_name(k)} {v}")
        lines.append("# HELP loom_success_rate_pct Success rate percent")
        lines.append("# TYPE loom_success_rate_pct gauge")
        lines.append(f"loom_success_rate_pct {snap['success_rate_pct']}")
        lines.append("# HELP loom_p95_latency_ms Approximate P95 latency")
        lines.append("# TYPE loom_p95_latency_ms gauge")
        lines.append(f"loom_p95_latency_ms {snap['p95_latency_ms']}")
        lines.append("# HELP loom_tokens_total Tokens used")
        lines.append("# TYPE loom_tokens_total counter")
        lines.append(f"loom_tokens_total {snap['tokens_total']}")
        for k, v in snap["gauges"].items():
            lines.append(f"{_prom_name(k)} {v}")
        return "\n".join(lines) + "\n"


def _key(name: str, labels: Dict[str, str]) -> str:
    if not labels:
        return name
    pairs = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
    return f"{name}{{{pairs}}}"


def _prom_name(key: str) -> str:
    """Prometheus 兼容标签渲染。"""
    if "{" not in key:
        return key
    name, rest = key.split("{", 1)
    inner = rest.rstrip("}")
    return f"{name}{{{inner}}}"


def _approx_p95(buckets: Dict[str, List[int]], counts: Dict[str, int]) -> float:
    total = sum(counts.values())
    if not total:
        return 0.0
    # 合并所有序列的桶
    merged = [0] * len(_LAT_BUCKETS)
    for b in buckets.values():
        for i, v in enumerate(b):
            if i < len(merged):
                merged[i] += v
    # 桶是「≤ bound」累计吗？我们逐档累加，改为累计命中
    cum = 0
    for i, bound in enumerate(_LAT_BUCKETS):
        cum += merged[i]
        if cum >= total * 0.95:
            return float(bound)
    return float(_LAT_BUCKETS[-1])


_metrics = Metrics()


def get_metrics() -> Metrics:
    return _metrics


def reset_metrics() -> None:
    global _metrics
    _metrics = Metrics()
