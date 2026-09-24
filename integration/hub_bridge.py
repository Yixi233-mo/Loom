"""Hub Graph 与 TaskOrchestrator 的 workflow 路径接线。"""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict

from langgraph.graph import END, StateGraph

from agent_hub.graph import (
    HubState,
    aggregate_results,
    classify_intent,
    compile_dsl_node,
    route_by_intent,
)


def make_orchestrated_dispatch(
    stack: Any,
) -> Callable[[HubState], Awaitable[Dict[str, Any]]]:
    """dispatch：agent_task 走 Registry；workflow 走 TaskOrchestrator（INT.1）。"""

    async def dispatch(state: HubState) -> Dict[str, Any]:
        intent = state.get("intent")
        agent = state.get("agent")
        user_input = state.get("user_input") or ""

        if intent == "agent_task" and agent:
            try:
                result = await stack.registry.invoke(agent, user_input)
            except Exception as e:  # noqa: BLE001
                result = {"error": str(e), "fallback": True}
            return {"result": str(result), "task_id": None, "agent": agent}

        if intent == "workflow":
            spec = state.get("workflow_spec") or {"name": "adhoc"}
            task_id = await stack.submit_workflow_async(spec)
            record = stack.orch.get(task_id) if task_id else {}
            return {
                "result": f"workflow:{spec.get('name', 'adhoc')}",
                "task_id": task_id,
                "workflow_status": str(record.get("status", "")),
            }

        return {"result": "chat", "task_id": None}

    return dispatch


def build_integrated_hub_graph(stack: Any) -> Any:
    """构建接上 TaskOrchestrator 的 Hub 主图。"""
    g: StateGraph = StateGraph(HubState)
    g.add_node("classify", classify_intent)
    g.add_node("compile_dsl", compile_dsl_node)
    g.add_node("dispatch", make_orchestrated_dispatch(stack))
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
