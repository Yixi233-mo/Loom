"""Agent 降级链 — Cloud API → Ollama → 规则兜底 + 成本记账。

degradation_level（方案）：
  0 = 全功能（Cloud / 主 Agent）
  1 = 备用 Agent（Ollama / 本地）
  2 = 规则兜底（无 LLM）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, List, Optional, Sequence

from observability.cost import CircuitOpenError, CostMeter
from observability.logging import (
    DEG_FALLBACK_AGENT,
    DEG_FULL,
    DEG_RULES,
    get_logger,
    new_trace_id,
)

ProviderFn = Callable[..., Awaitable[Any]]


@dataclass
class Provider:
    name: str
    level: int
    call: ProviderFn
    # 估算 token：默认按 prompt 长度粗算（后续可换真实计费）
    token_estimator: Optional[Callable[[str, Any], int]] = None


@dataclass
class DegradeResult:
    value: Any
    provider: str
    degradation_level: int
    errors: List[str] = field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0

    @property
    def used_fallback(self) -> bool:
        return self.degradation_level > DEG_FULL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "degradation_level": self.degradation_level,
            "tokens_used": self.tokens_used,
            "latency_ms": round(self.latency_ms, 3),
            "errors": self.errors,
            "value": self.value,
        }


def _estimate_tokens(prompt: str, value: Any) -> int:
    # 粗算：输入+输出字符数 / 2（中文近似）
    out_len = 0
    if isinstance(value, dict):
        out_len = len(str(value))
    elif isinstance(value, str):
        out_len = len(value)
    return max(1, (len(prompt) + out_len) // 2)


class DegradationChain:
    """按序尝试 Provider，失败则降级；支持 CostMeter 熔断。"""

    def __init__(self, providers: Sequence[Provider]) -> None:
        if not providers:
            raise ValueError("至少需要一个 Provider")
        self.providers: List[Provider] = list(providers)

    async def run(
        self,
        prompt: str,
        trace_id: Optional[str] = None,
        meter: Optional[CostMeter] = None,
        **kwargs: Any,
    ) -> DegradeResult:
        tid = trace_id or new_trace_id()
        errors: List[str] = []
        log = get_logger()
        import time

        started = time.time()
        total_tokens = 0

        for idx, p in enumerate(self.providers):
            if meter is not None:
                try:
                    meter.guard()
                except CircuitOpenError:
                    log.emit(
                        "cost.breaker_open",
                        trace_id=tid,
                        agent_name=p.name,
                        tokens_used=meter.tokens_used,
                        task_status="failed",
                    )
                    return DegradeResult(
                        value={
                            "error": "token_limit_exceeded",
                            "tokens_used": meter.tokens_used,
                            "limit": meter.limit,
                            "fallback": True,
                        },
                        provider="circuit_breaker",
                        degradation_level=DEG_RULES,
                        errors=errors + ["CircuitOpenError"],
                        tokens_used=total_tokens,
                        latency_ms=(time.time() - started) * 1000.0,
                    )

            with log.span(
                "degrade.attempt",
                trace_id=tid,
                agent_name=p.name,
                degradation_level=p.level,
            ) as span:
                try:
                    value = await p.call(prompt, **kwargs)
                    used = (
                        p.token_estimator(prompt, value)
                        if p.token_estimator
                        else _estimate_tokens(prompt, value)
                    )
                    total_tokens += used
                    if meter is not None:
                        try:
                            meter.add_tokens(used)
                        except CircuitOpenError:
                            span.set(task_status="failed", tokens_used=meter.tokens_used)
                            raise
                        meter.raise_degradation(p.level)
                    latency_ms = (time.time() - started) * 1000.0
                    span.set(task_status="done", tokens_used=used, latency_ms=round(latency_ms, 3))
                    if idx > 0:
                        log.emit(
                            "degrade.switch",
                            trace_id=tid,
                            agent_name=p.name,
                            degradation_level=p.level,
                            reason="; ".join(errors) if errors else "upstream_failed",
                            latency_ms=round(latency_ms, 3),
                        )
                    return DegradeResult(
                        value=value,
                        provider=p.name,
                        degradation_level=p.level,
                        errors=list(errors),
                        tokens_used=total_tokens,
                        latency_ms=latency_ms,
                    )
                except CircuitOpenError:
                    raise
                except Exception as e:  # noqa: BLE001
                    msg = f"{p.name}: {e}"
                    errors.append(msg)
                    span.set(task_status="failed", error=str(e))

        return DegradeResult(
            value={"error": "all_providers_failed", "details": errors, "fallback": True},
            provider="none",
            degradation_level=DEG_RULES,
            errors=errors,
            tokens_used=total_tokens,
            latency_ms=(time.time() - started) * 1000.0,
        )


async def cloud_api_provider(prompt: str, **kwargs: Any) -> Any:
    endpoint = kwargs.get("endpoint") or ""
    if not endpoint:
        raise RuntimeError("Cloud API 未配置（endpoint 为空）")
    raise RuntimeError("Cloud API 调用未实现")  # 需确认当前版本API


async def ollama_provider(prompt: str, **kwargs: Any) -> Any:
    host = kwargs.get("host") or "http://127.0.0.1:11434"
    raise RuntimeError(f"Ollama 不可用: {host}")


async def rules_provider(prompt: str, **kwargs: Any) -> Any:
    text = (prompt or "").strip()
    summary = text[:80] + ("…" if len(text) > 80 else "")
    return {
        "summary": f"[规则兜底] 已处理：{summary}",
        "citations": [],
        "mode": "rules",
    }


def default_chain() -> DegradationChain:
    return DegradationChain(
        [
            Provider("cloud_api", DEG_FULL, cloud_api_provider),
            Provider("ollama", DEG_FALLBACK_AGENT, ollama_provider),
            Provider("rules", DEG_RULES, rules_provider),
        ]
    )
