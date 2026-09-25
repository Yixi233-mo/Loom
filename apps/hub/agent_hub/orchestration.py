"""Agent 编排护栏 — 迭代上限 / 重复检测 / 超时 / 工具校验 / 多 Agent 裁决（N16 第 8 章）。"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from observability.resilience import with_timeout

logger = logging.getLogger(__name__)

# 8.2 最大迭代
MAX_ITERATIONS = 10
# 8.3 同工具同参重复次数阈值
DUPLICATE_ACTION_LIMIT = 3
# 8.4 单任务全局超时
TASK_TIMEOUT_S = 120.0


class OrchestrationError(Exception):
    """编排护栏拒绝。"""

    def __init__(self, message: str, code: str = "ORCH") -> None:
        super().__init__(message)
        self.code = code


class ToolNotFoundError(OrchestrationError):
    def __init__(self, tool: str) -> None:
        super().__init__(f"未注册工具: {tool}", code="TOOL_NOT_FOUND")
        self.tool = tool


class ToolValidationError(OrchestrationError):
    def __init__(self, tool: str, detail: str) -> None:
        super().__init__(f"工具参数校验失败 {tool}: {detail}", code="TOOL_INVALID")
        self.tool = tool


class DuplicateActionError(OrchestrationError):
    def __init__(self, tool: str, count: int) -> None:
        super().__init__(
            f"重复动作：工具 {tool} 同参数已连续调用 {count} 次", code="DUPLICATE_ACTION"
        )
        self.tool = tool
        self.count = count


class IterationLimitError(OrchestrationError):
    def __init__(self, limit: int) -> None:
        super().__init__(f"超过最大迭代次数 {limit}", code="MAX_ITERATIONS")
        self.limit = limit


# 8.6 工具参数 Schema（轻量 Pydantic 风格校验）
TOOL_PARAM_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "notes.create": {
        "required": ["title"],
        "types": {"title": str, "content": str},
    },
    "notes.list": {"required": [], "types": {}},
    "notes.delete": {"required": ["note_id"], "types": {"note_id": str}},
    "file.read": {"required": ["path"], "types": {"path": str}},
    "file.write": {"required": ["path", "content"], "types": {"path": str, "content": str}},
    "shell.exec": {"required": ["cmd"], "types": {"cmd": str}},
}


def validate_tool_args(tool: str, args: Dict[str, Any], schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """8.6 参数校验：未知工具 / 缺字段 / 类型错误 → ToolValidationError。"""
    sch = schema if schema is not None else TOOL_PARAM_SCHEMAS.get(tool)
    if sch is None:
        # 未声明 schema 的工具：仅要求 args 是 dict
        if not isinstance(args, dict):
            raise ToolValidationError(tool, "args 必须是对象")
        return dict(args)
    args = dict(args or {})
    for req in sch.get("required", []):
        if req not in args or args[req] in (None, ""):
            raise ToolValidationError(tool, f"缺少必填参数 {req}")
    types = sch.get("types", {})
    for k, expected in types.items():
        if k in args and args[k] is not None and not isinstance(args[k], expected):
            raise ToolValidationError(tool, f"参数 {k} 类型应为 {expected.__name__}")
    return args


def action_fingerprint(tool: str, args: Dict[str, Any]) -> str:
    payload = json.dumps({"tool": tool, "args": args}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class ActionTracker:
    """8.3 重复动作检测：连续 N 次同工具同参 → 拒绝。"""

    def __init__(self, limit: int = DUPLICATE_ACTION_LIMIT) -> None:
        self.limit = limit
        self._last: Optional[str] = None
        self._count = 0

    def check(self, tool: str, args: Dict[str, Any]) -> None:
        fp = action_fingerprint(tool, args)
        if fp == self._last:
            self._count += 1
        else:
            self._last = fp
            self._count = 1
        if self._count >= self.limit:
            raise DuplicateActionError(tool, self._count)

    def reset(self) -> None:
        self._last = None
        self._count = 0


@dataclass
class StepResult:
    step_id: str
    tool: str
    ok: bool
    value: Any = None
    error: str = ""


@dataclass
class RunGuard:
    """单次编排运行的护栏状态。"""

    max_iterations: int = MAX_ITERATIONS
    timeout_s: float = TASK_TIMEOUT_S
    iterations: int = 0
    tracker: ActionTracker = field(default_factory=ActionTracker)
    started_at: float = field(default_factory=time.time)
    steps: List[StepResult] = field(default_factory=list)

    def tick(self) -> None:
        """8.2 迭代计数。"""
        self.iterations += 1
        if self.iterations > self.max_iterations:
            raise IterationLimitError(self.max_iterations)

    def remaining_time(self) -> float:
        return max(0.0, self.timeout_s - (time.time() - self.started_at))


class ToolExecutor:
    """8.5/8.8 工具执行：未注册报错；失败降级不盲重试。"""

    def __init__(
        self,
        tools: Dict[str, Callable[..., Any]],
        max_retries: int = 0,
    ) -> None:
        self.tools = dict(tools or {})
        self.max_retries = max(0, int(max_retries))

    def has(self, tool: str) -> bool:
        return tool in self.tools

    def invoke(self, tool: str, args: Optional[Dict[str, Any]] = None, guard: Optional[RunGuard] = None) -> StepResult:
        if tool not in self.tools:
            # 8.5 未注册工具直接报错
            raise ToolNotFoundError(tool)
        if guard is not None:
            guard.tick()
            guard.tracker.check(tool, args or {})
        validated = validate_tool_args(tool, args or {})
        fn = self.tools[tool]
        try:
            value = fn(**validated) if _accepts_kwargs(fn) else fn(validated)
            sr = StepResult(step_id=f"step-{len(guard.steps) if guard else 0}", tool=tool, ok=True, value=value)
            if guard is not None:
                guard.steps.append(sr)
            return sr
        except Exception as e:  # noqa: BLE001
            # 8.8 有降级、不盲重试（max_retries 默认 0）
            if self.max_retries > 0:
                for i in range(self.max_retries):
                    try:
                        time.sleep(min(0.1 * (2**i), 0.5))
                        value = fn(**validated) if _accepts_kwargs(fn) else fn(validated)
                        sr = StepResult(step_id="step-retry", tool=tool, ok=True, value=value)
                        if guard is not None:
                            guard.steps.append(sr)
                        return sr
                    except Exception:  # noqa: BLE001
                        continue
            sr = StepResult(step_id="step-fail", tool=tool, ok=False, error=str(e))
            if guard is not None:
                guard.steps.append(sr)
            logger.warning("工具失败降级 tool=%s err=%s", tool, e)
            return sr


def _accepts_kwargs(fn: Callable[..., Any]) -> bool:
    import inspect

    try:
        sig = inspect.signature(fn)
    except (TypeError, ValueError):
        return False
    return any(
        p.kind in (p.VAR_KEYWORD, p.VAR_POSITIONAL) or p.default is not inspect.Parameter.empty or p.name != "args"
        for p in sig.parameters.values()
    )


async def run_with_budget(coro: Awaitable[Any], timeout_s: float = TASK_TIMEOUT_S, label: str = "task") -> Any:
    """8.4 单任务全局超时 ≤120s。"""
    return await with_timeout(coro, timeout_s, label=label)


# ---------------------------------------------------------------------------
# 8.9 多 Agent 裁决 / 确认
# ---------------------------------------------------------------------------


@dataclass
class AgentVote:
    agent: str
    value: Any
    confidence: float = 1.0


class MultiAgentAdjudicator:
    """多 Agent 结果裁决：多数一致 / 需确认时挂起。"""

    def __init__(self, confirm_threshold: float = 0.5) -> None:
        self.confirm_threshold = confirm_threshold
        self.pending: Dict[str, List[AgentVote]] = {}

    def collect(self, task_id: str, votes: Sequence[AgentVote]) -> Dict[str, Any]:
        """收集投票并裁决；分歧大则 needs_confirm。"""
        if not votes:
            return {"task_id": task_id, "decision": None, "needs_confirm": False, "votes": []}
        counts: Dict[str, int] = {}
        for v in votes:
            key = json.dumps(v.value, sort_keys=True, ensure_ascii=False, default=str)
            counts[key] = counts.get(key, 0) + 1
        best_key, best_n = max(counts.items(), key=lambda kv: kv[1])
        total = len(votes)
        ratio = best_n / total if total else 0.0
        needs = ratio < (1.0 - self.confirm_threshold) or total < 2
        # 两人对半/平票也需确认
        if total >= 2 and best_n == total - best_n and total % 2 == 0:
            needs = True
        decision = json.loads(best_key) if best_key.startswith(("{", "[", '"')) else best_key
        out = {
            "task_id": task_id,
            "decision": decision,
            "agreement": round(ratio, 3),
            "needs_confirm": needs,
            "votes": [{"agent": v.agent, "confidence": v.confidence} for v in votes],
        }
        self.pending[task_id] = list(votes)
        return out

    def confirm(self, task_id: str, accepted: Any = None) -> Dict[str, Any]:
        votes = self.pending.pop(task_id, [])
        return {"task_id": task_id, "confirmed": True, "value": accepted, "votes": len(votes)}


def build_graph_ascii() -> str:
    """8.1 LangGraph 可编译时 print_ascii 的简化预览。"""
    try:
        from agent_hub.graph import build_hub_graph

        g = build_hub_graph()
        # LangGraph 编译对象可能暴露 get_graph
        graph = getattr(g, "get_graph", None)
        if callable(graph):
            gr = graph()
            ascii_fn = getattr(gr, "draw_ascii", None) or getattr(gr, "print_ascii", None)
            if callable(ascii_fn):
                try:
                    return ascii_fn() or "compiled"
                except Exception:  # noqa: BLE001
                    return "compiled"
        return "compiled"
    except Exception as e:  # noqa: BLE001
        raise OrchestrationError(f"Hub 图编译失败: {e}", code="GRAPH_COMPILE") from e
