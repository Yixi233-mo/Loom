"""Agent 降级链 — Cloud API → Ollama → 规则兜底 + 成本记账。

degradation_level（方案）：
  0 = 全功能（Cloud / 主 Agent）
  1 = 备用 Agent（Ollama / 本地）
  2 = 规则兜底（无 LLM）

N16 第 7 章：
  7.2 DeepSeek → Ollama → 规则
  7.3 触发条件：单次 30s 超时 或 连续 3 败
  7.4 降级日志 WARNING + degradation_level
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from observability.cost import CircuitOpenError, CostMeter
from observability.logging import (
    DEG_FALLBACK_AGENT,
    DEG_FULL,
    DEG_RULES,
    get_logger,
    new_trace_id,
)

logger = logging.getLogger(__name__)

ProviderFn = Callable[..., Awaitable[Any]]

# 7.3 触发条件
PROVIDER_TIMEOUT_S = float(os.environ.get("LOOM_PROVIDER_TIMEOUT", "30"))
CONSECUTIVE_FAIL_LIMIT = int(os.environ.get("LOOM_PROVIDER_FAIL_LIMIT", "3"))


@dataclass
class ProviderHealth:
    """单 Provider 健康度：连续失败计数（7.3）。"""

    name: str
    consecutive_fails: int = 0
    last_error: str = ""
    last_latency_ms: float = 0.0

    def mark_fail(self, err: str) -> None:
        self.consecutive_fails += 1
        self.last_error = err

    def mark_ok(self, latency_ms: float) -> None:
        self.consecutive_fails = 0
        self.last_error = ""
        self.last_latency_ms = latency_ms

    def should_skip(self) -> bool:
        """连续 3 败 → 本链跳过该 Provider（触发降级）。"""
        return self.consecutive_fails >= CONSECUTIVE_FAIL_LIMIT


@dataclass
class Provider:
    name: str
    level: int
    call: ProviderFn
    # 估算 token：默认按 prompt 长度粗算（后续可换真实计费）
    token_estimator: Optional[Callable[[str, Any], int]] = None
    timeout_s: float = PROVIDER_TIMEOUT_S


@dataclass
class DegradeResult:
    value: Any
    provider: str
    degradation_level: int
    errors: List[str] = field(default_factory=list)
    tokens_used: int = 0
    latency_ms: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def used_fallback(self) -> bool:
        return self.degradation_level > DEG_FULL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "degradation_level": self.degradation_level,
            "tokens_used": self.tokens_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
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


def _split_tokens(prompt: str, value: Any) -> tuple[int, int]:
    """7.7 prompt / completion 分项。"""
    p = max(1, len(prompt) // 2)
    out = _estimate_tokens(prompt, value)
    return p, max(1, out - p)


class DegradationChain:
    """按序尝试 Provider，失败则降级；支持 CostMeter 熔断。"""

    def __init__(self, providers: Sequence[Provider]) -> None:
        if not providers:
            raise ValueError("至少需要一个 Provider")
        self.providers: List[Provider] = list(providers)
        self.health: Dict[str, ProviderHealth] = {
            p.name: ProviderHealth(name=p.name) for p in self.providers
        }

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

        started = time.time()
        total_tokens = 0
        prompt_tokens = 0
        completion_tokens = 0

        for idx, p in enumerate(self.providers):
            health = self.health.setdefault(p.name, ProviderHealth(name=p.name))
            if health.should_skip():
                # 7.3 连续 3 败：跳过并记 WARNING 降级
                reason = f"consecutive_fails={health.consecutive_fails}"
                errors.append(f"{p.name}: skipped ({reason})")
                logger.warning(
                    "[degrade] skip provider=%s reason=%s degradation_level=%s",
                    p.name,
                    reason,
                    p.level,
                )
                log.emit(
                    "degrade.skip",
                    trace_id=tid,
                    agent_name=p.name,
                    degradation_level=p.level,
                    reason=reason,
                    task_status="skipped",
                )
                continue

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
                    # 7.3 单次 30s 超时
                    value = await asyncio.wait_for(
                        p.call(prompt, **kwargs), timeout=p.timeout_s
                    )
                    used = (
                        p.token_estimator(prompt, value)
                        if p.token_estimator
                        else _estimate_tokens(prompt, value)
                    )
                    pt, ct = _split_tokens(prompt, value)
                    total_tokens += used
                    prompt_tokens += pt
                    completion_tokens += ct
                    if meter is not None:
                        try:
                            meter.add_tokens(used, prompt=pt, completion=ct)
                        except CircuitOpenError:
                            span.set(task_status="failed", tokens_used=meter.tokens_used)
                            raise
                        meter.raise_degradation(p.level)
                    latency_ms = (time.time() - started) * 1000.0
                    health.mark_ok(latency_ms)
                    span.set(task_status="done", tokens_used=used, latency_ms=round(latency_ms, 3))
                    if idx > 0:
                        # 7.4 降级 WARNING + degradation_level
                        logger.warning(
                            "[degrade] switch provider=%s level=%s reason=%s",
                            p.name,
                            p.level,
                            "; ".join(errors) if errors else "upstream_failed",
                        )
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
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                    )
                except CircuitOpenError:
                    raise
                except asyncio.TimeoutError:
                    msg = f"{p.name}: timeout {p.timeout_s}s"
                    errors.append(msg)
                    health.mark_fail(msg)
                    logger.warning("[degrade] timeout provider=%s (%.0fs)", p.name, p.timeout_s)
                    span.set(task_status="failed", error=msg)
                except Exception as e:  # noqa: BLE001
                    msg = f"{p.name}: {e}"
                    errors.append(msg)
                    health.mark_fail(str(e))
                    logger.warning(
                        "[degrade] fail provider=%s consecutive=%s err=%s",
                        p.name,
                        health.consecutive_fails,
                        e,
                    )
                    span.set(task_status="failed", error=str(e))

        return DegradeResult(
            value={"error": "all_providers_failed", "details": errors, "fallback": True},
            provider="none",
            degradation_level=DEG_RULES,
            errors=errors,
            tokens_used=total_tokens,
            latency_ms=(time.time() - started) * 1000.0,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )


async def cloud_api_provider(prompt: str, **kwargs: Any) -> Any:
    """7.1 DeepSeek / OpenAI 兼容 Cloud API。"""
    import httpx

    base_url = (
        kwargs.get("base_url")
        or os.environ.get("DEEPSEEK_BASE_URL")
        or "https://api.deepseek.com/v1"
    )
    api_key = kwargs.get("api_key") or os.environ.get("DEEPSEEK_API_KEY", "")
    model = kwargs.get("model") or os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    if not api_key:
        raise RuntimeError("Cloud API 未配置（缺少 DEEPSEEK_API_KEY）")
    from observability.security import split_prompt_messages

    messages = split_prompt_messages(prompt, system=str(kwargs.get("system") or "你是 Loom 助手"))
    timeout = float(kwargs.get("timeout") or PROVIDER_TIMEOUT_S)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            base_url.rstrip("/") + "/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages},
        )
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage") or {}
        return {
            "summary": content,
            "citations": [],
            "mode": "cloud",
            "model": model,
            "usage": usage,
        }


async def ollama_provider(prompt: str, **kwargs: Any) -> Any:
    """7.1 Ollama 本地模型。"""
    import httpx

    host = (kwargs.get("host") or os.environ.get("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
    model = kwargs.get("model") or os.environ.get("OLLAMA_MODEL", "llama3.2")
    timeout = float(kwargs.get("timeout") or PROVIDER_TIMEOUT_S)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            host + "/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        r.raise_for_status()
        data = r.json()
        content = data.get("response") or data.get("message", {}).get("content") or ""
        return {
            "summary": content[:500],
            "citations": [],
            "mode": "ollama",
            "model": model,
        }


async def rules_provider(prompt: str, **kwargs: Any) -> Any:
    text = (prompt or "").strip()
    summary = text[:80] + ("…" if len(text) > 80 else "")
    return {
        "summary": f"[规则兜底] 已处理：{summary}",
        "citations": [],
        "mode": "rules",
    }


# 7.8 热切换模型：进程内注册表，无需重启
_MODEL_REGISTRY: Dict[str, Dict[str, str]] = {}


def set_active_model(provider: str, model: str, **extra: str) -> Dict[str, str]:
    """7.8 换模型不重启。"""
    conf = {"provider": provider, "model": model, **extra}
    _MODEL_REGISTRY[provider] = conf
    logger.info("[model] switch %s -> %s (hot)", provider, model)
    return conf


def get_active_model(provider: str) -> Optional[Dict[str, str]]:
    return _MODEL_REGISTRY.get(provider)


def default_chain() -> DegradationChain:
    """7.2 DeepSeek → Ollama → 规则。"""
    return DegradationChain(
        [
            Provider("deepseek", DEG_FULL, cloud_api_provider),
            Provider("ollama", DEG_FALLBACK_AGENT, ollama_provider),
            Provider("rules", DEG_RULES, rules_provider),
        ]
    )
