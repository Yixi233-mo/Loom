"""应用层韧性 — 超时 / 指数退避 / 异常隔离（N16 第 4 章）。"""

from __future__ import annotations

import asyncio
import functools
import logging
import signal
import time
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional, Tuple, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# 4.4 外部调用超时
HTTP_TIMEOUT_S = 30.0
LLM_TIMEOUT_S = 120.0
MCP_TIMEOUT_S = 30.0

# 4.5 指数退避
RETRY_MAX = 3
RETRY_BASE_DELAY = 0.5
RETRY_MAX_DELAY = 8.0


class TimeoutBudgetError(TimeoutError):
    """超过调用预算。"""


class DependencyNotReady(RuntimeError):
    """依赖未就绪（4.8）。"""


@dataclass
class RetryResult:
    value: Any
    attempts: int
    latency_ms: float


def compute_backoff(attempt: int, base: float = RETRY_BASE_DELAY, cap: float = RETRY_MAX_DELAY) -> float:
    """attempt 从 1 开始：0.5, 1, 2, 4… 封顶 RETRY_MAX_DELAY。"""
    if attempt < 1:
        attempt = 1
    return min(base * (2 ** (attempt - 1)), cap)


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    retries: int = RETRY_MAX,
    retry_on: Tuple[Type[BaseException], ...] = (Exception,),
    base_delay: float = RETRY_BASE_DELAY,
    max_delay: float = RETRY_MAX_DELAY,
    on_retry: Optional[Callable[[int, BaseException], None]] = None,
) -> T:
    """指数退避重试，最多 retries 次尝试（含首次）。"""
    last: BaseException | None = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            return await fn()
        except retry_on as e:  # noqa: PERF203
            last = e
            if attempt >= retries:
                break
            delay = compute_backoff(attempt, base_delay, max_delay)
            if on_retry:
                on_retry(attempt, e)
            logger.warning("retry attempt=%s/%s after %s: %s", attempt, retries, delay, e)
            await asyncio.sleep(delay)
    assert last is not None
    raise last


async def with_timeout(
    coro: Awaitable[T],
    timeout: float,
    label: str = "call",
) -> T:
    """4.4 强制超时预算。"""
    try:
        return await asyncio.wait_for(coro, timeout=timeout)
    except asyncio.TimeoutError as e:
        raise TimeoutBudgetError(f"{label} 超时 {timeout}s") from e


class GracefulShutdown:
    """4.3 SIGTERM/SIGINT 优雅停机，目标 ≤30s。"""

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout
        self._event = asyncio.Event()
        self._cleanups: list[Callable[[], Awaitable[None]]] = []
        self._installed = False

    @property
    def event(self) -> asyncio.Event:
        return self._event

    def add_cleanup(self, fn: Callable[[], Awaitable[None]]) -> None:
        self._cleanups.append(fn)

    def request_stop(self, *_args: Any) -> None:
        logger.info("收到停机信号，开始优雅退出（预算 %.0fs）", self.timeout)
        self._event.set()

    def install(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        if self._installed:
            return
        try:
            loop = loop or asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(sig, self.request_stop)
                except (NotImplementedError, RuntimeError, ValueError):
                    signal.signal(sig, lambda *_: self.request_stop())
            self._installed = True
        except Exception:  # noqa: BLE001 — 信号注册失败不阻塞启动
            logger.warning("信号处理注册失败，停机依赖外部 kill")

    async def run_cleanups(self) -> None:
        start = time.time()
        for fn in self._cleanups:
            try:
                await with_timeout(fn(), self.timeout, label="cleanup")
            except Exception as e:  # noqa: BLE001
                logger.warning("cleanup 失败: %s", e)
            if time.time() - start > self.timeout:
                logger.warning("停机预算已用尽，剩余清理跳过")
                break
        logger.info("优雅停机完成，用时 %.2fs", time.time() - start)


def isolate_task_failure(label: str = "task") -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """4.7 单任务失败隔离：异常只记日志，不冒泡到调度器。"""

    def deco(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                logger.error("[%s] 任务失败已隔离: %s", label, e, exc_info=True)
                return None

        return wrapper

    return deco


@dataclass
class ReadyStatus:
    ok: bool
    checks: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "checks": self.checks}


def check_dependencies(
    *,
    db_ok: bool = True,
    model_ok: bool = True,
    secrets_ok: bool = True,
    extra: Optional[dict[str, Any]] = None,
) -> ReadyStatus:
    """4.2 就绪检查：依赖未就绪时明确标记（4.8）。"""
    checks: dict[str, Any] = {
        "database": {"ok": bool(db_ok)},
        "model": {"ok": bool(model_ok)},
        "secrets": {"ok": bool(secrets_ok)},
    }
    if extra:
        checks.update(extra)
    ok = all(bool(v.get("ok")) for v in checks.values())
    if not ok:
        bad = [k for k, v in checks.items() if not v.get("ok")]
        logger.warning("依赖未就绪: %s", ", ".join(bad))
    return ReadyStatus(ok=ok, checks=checks)
