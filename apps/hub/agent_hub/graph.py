"""Hub Graph — LangGraph 主图（意图 → 路由 → 分发 → 汇总）。

状态流转：
  classify ──workflow──► compile_dsl ──► dispatch ──► aggregate ──► END
      │
      └──agent_task──────────────────► dispatch ──► aggregate ──► END
      │
      └──chat──────────────────────────────────────────────────► END

意图路由（规则优先，LLM 兜底留待后续）：
  审查代码 / code review  → claude_code
  查资料 / 知识库 / 检索    → builtin_rag
  工作流 / 定时…           → workflow
  其余                     → chat

使用：图内 dispatch 为 async 节点，请用 `graph.ainvoke(...)` 或
`await run_hub(graph, state)`；同步节点也可用 `graph.invoke(...)`（chat 路径）。
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional, TypedDict

from langgraph.graph import END, StateGraph


class HubState(TypedDict, total=False):
    user_input: str
    intent: Optional[str]  # agent_task | workflow | chat
    agent: Optional[str]  # claude_code | builtin_rag | ...
    workflow_spec: Optional[dict]
    task_id: Optional[str]
    result: Optional[str]


# ---------------------------------------------------------------------------
# 意图识别
# ---------------------------------------------------------------------------

_CODE_KEYWORDS = ("审查代码", "代码审查", "审查这段代码", "code review", "review code")
_RAG_KEYWORDS = ("查资料", "查知识库", "知识库", "检索", "找资料", "查文档", "查询资料", "资料")
_WORKFLOW_KEYWORDS = ("工作流", "workflow", "定时任务", "每天", "每周", "触发")

AGENT_CODE = "claude_code"
AGENT_RAG = "builtin_rag"


def _hit(keywords: tuple, text: str) -> bool:
    low = text.lower()
    return any(k.lower() in low for k in keywords)


def classify_intent(state: HubState) -> Dict[str, Any]:
    """识别意图与目标 Agent（规则优先，可注入 HybridIntentRouter）。"""
    text = state.get("user_input") or ""
    router = globals().get("_INTENT_ROUTER")
    if router is not None:
        out = dict(router.route(text))
        if out.get("intent") == "chat":
            out["result"] = "chat"
        return out
    if _hit(_CODE_KEYWORDS, text):
        return {"intent": "agent_task", "agent": AGENT_CODE}
    if _hit(_RAG_KEYWORDS, text):
        return {"intent": "agent_task", "agent": AGENT_RAG}
    if _hit(_WORKFLOW_KEYWORDS, text):
        return {"intent": "workflow", "agent": None}
    # chat 路径直接 END，result 在此写入
    return {"intent": "chat", "agent": None, "result": "chat"}


_INTENT_ROUTER = None


def set_intent_router(router: Any) -> None:
    """注入 HybridIntentRouter（LLM 可插拔意图路由）。"""
    global _INTENT_ROUTER
    _INTENT_ROUTER = router


def route_by_intent(state: HubState) -> str:
    intent = state.get("intent") or "chat"
    if intent in ("agent_task", "workflow"):
        return intent
    return "chat"


# ---------------------------------------------------------------------------
# 节点
# ---------------------------------------------------------------------------


def compile_dsl_node(state: HubState) -> Dict[str, Any]:
    """workflow 意图：生成 workflow_spec 摘要（真实编译由 dsl.compiler 负责）。"""
    return {
        "workflow_spec": {
            "name": "adhoc",
            "source": state.get("user_input"),
        }
    }


def make_dispatch_node(
    registry: Any = None,
) -> Callable[[HubState], Awaitable[Dict[str, Any]]]:
    """dispatch：agent_task 走 AgentRegistry.invoke；workflow 仅记录摘要。"""

    async def dispatch(state: HubState) -> Dict[str, Any]:
        intent = state.get("intent")
        agent = state.get("agent")
        user_input = state.get("user_input") or ""

        if intent == "agent_task" and agent:
            if registry is None:
                return {"result": f"routed:{agent}", "task_id": None}
            try:
                result = await registry.invoke(agent, user_input)
            except Exception as e:  # noqa: BLE001 — 分发失败降级，不向上抛
                result = {"error": str(e), "fallback": True}
            return {"result": str(result), "task_id": None, "agent": agent}

        if intent == "workflow":
            name = (state.get("workflow_spec") or {}).get("name", "adhoc")
            return {"result": f"workflow:{name}", "task_id": None}

        return {"result": "chat", "task_id": None}

    return dispatch


def aggregate_results(state: HubState) -> Dict[str, Any]:
    return {"result": state.get("result") or ""}


# ---------------------------------------------------------------------------
# 图构建
# ---------------------------------------------------------------------------


def build_hub_graph(orchestrator: Any = None, registry: Any = None) -> Any:
    """构建并编译 Hub 主图。

    orchestrator：预留（workflow 真实分发由 TaskOrchestrator 负责，后续接入）
    registry：Agent 注册表（agent_task 路径）
    """
    g: StateGraph = StateGraph(HubState)

    g.add_node("classify", classify_intent)
    g.add_node("compile_dsl", compile_dsl_node)
    g.add_node("dispatch", make_dispatch_node(registry))
    g.add_node("aggregate", aggregate_results)

    g.set_entry_point("classify")
    g.add_conditional_edges(
        "classify",
        route_by_intent,
        {
            "workflow": "compile_dsl",
            "agent_task": "dispatch",
            "chat": END,
        },
    )
    g.add_edge("compile_dsl", "dispatch")
    g.add_edge("dispatch", "aggregate")
    g.add_edge("aggregate", END)

    return g.compile()


async def run_hub(graph: Any, state: HubState) -> HubState:
    """异步跑一次 Hub 图。"""
    return await graph.ainvoke(state)


def run_hub_sync(graph: Any, state: HubState) -> HubState:
    """同步包装（内部 asyncio.run）。"""
    return asyncio.run(graph.ainvoke(state))
