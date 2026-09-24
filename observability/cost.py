"""成本 / 降级追踪 — Token 熔断 + 成本输出。

单任务 Token 上限 10000（方案 · 成本）：
  tokens_used + latency_ms + degradation_level 必输出
  超限熔断：CircuitOpen，后续调用拒绝
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from observability.logging import (
    DEG_FALLBACK_AGENT,
    DEG_FULL,
    DEG_RULES,
)

TOKEN_LIMIT_PER_TASK = 10000

__all__ = [
    "CostMeter",
    "CostReport",
    "CircuitOpenError",
    "TOKEN_LIMIT_PER_TASK",
    "DEG_FULL",
    "DEG_FALLBACK_AGENT",
    "DEG_RULES",
]


class CircuitOpenError(Exception):
    """Token 超限熔断：本任务不再继续调用。"""

    def __init__(self, tokens_used: int, limit: int, task_id: str = ""):
        self.tokens_used = tokens_used
        self.limit = limit
        self.task_id = task_id
        super().__init__(
            f"Token 熔断 task={task_id} tokens_used={tokens_used} limit={limit}"
        )


@dataclass
class CostReport:
    """一次任务的完整成本快照。"""

    task_id: str
    tokens_used: int
    latency_ms: float
    degradation_level: int
    estimated_cost_cny: float = 0.0
    breaker_open: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "tokens_used": self.tokens_used,
            "latency_ms": round(self.latency_ms, 3),
            "degradation_level": self.degradation_level,
            "estimated_cost_cny": self.estimated_cost_cny,
            "breaker_open": self.breaker_open,
        }


# 粗估：默认 ¥0.001 / 千 token（与方案成本表一致量级）
PRICE_PER_1K_TOKENS = 0.001


@dataclass
class CostMeter:
    """单任务 Token / 降级记账 + 熔断。"""

    task_id: str = ""
    tokens_used: int = 0
    degradation_level: int = DEG_FULL
    limit: int = TOKEN_LIMIT_PER_TASK
    started_at: float = field(default_factory=time.time)
    breaker_open: bool = False

    def add_tokens(self, n: int) -> None:
        """记账；超限则熔断（后续 add/guard 均失败）。"""
        if self.breaker_open:
            raise CircuitOpenError(self.tokens_used, self.limit, self.task_id)
        self.tokens_used += max(0, int(n))
        if self.tokens_used > self.limit:
            self.breaker_open = True
            raise CircuitOpenError(self.tokens_used, self.limit, self.task_id)

    def guard(self) -> None:
        """执行前守卫：已熔断则拒绝。"""
        if self.breaker_open:
            raise CircuitOpenError(self.tokens_used, self.limit, self.task_id)

    def raise_degradation(self, level: int) -> None:
        self.degradation_level = max(self.degradation_level, int(level))

    def exceeded(self) -> bool:
        return self.tokens_used > self.limit or self.breaker_open

    def snapshot(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "tokens_used": self.tokens_used,
            "degradation_level": self.degradation_level,
            "breaker_open": self.breaker_open,
        }

    def report(self) -> CostReport:
        latency_ms = (time.time() - self.started_at) * 1000.0
        cost = (self.tokens_used / 1000.0) * PRICE_PER_1K_TOKENS
        return CostReport(
            task_id=self.task_id,
            tokens_used=self.tokens_used,
            latency_ms=latency_ms,
            degradation_level=self.degradation_level,
            estimated_cost_cny=round(cost, 6),
            breaker_open=self.breaker_open,
        )
