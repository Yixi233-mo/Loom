"""T7 单元测试：Hub Graph — 意图路由 / 状态流转 / 分发。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from agent_hub.graph import (
    AGENT_CODE,
    AGENT_RAG,
    build_hub_graph,
    classify_intent,
    route_by_intent,
    run_hub,
    run_hub_sync,
)
from agent_hub.registry import AgentRegistry


def echo_adapter_factory(tag: str):
    async def _adapter(prompt: str, **kwargs: Any) -> dict[str, Any]:
        return {"tag": tag, "prompt": prompt}

    return _adapter


def make_registry() -> AgentRegistry:
    reg = AgentRegistry()
    reg.register("claude_code", echo_adapter_factory("claude_code"), ["code.gen", "code.review"])
    reg.register("builtin_rag", echo_adapter_factory("builtin_rag"), ["rag.query"])
    return reg


class TestClassify(unittest.TestCase):
    def test_code_review_to_claude(self):
        state = classify_intent({"user_input": "审查代码"})
        self.assertEqual(state["intent"], "agent_task")
        self.assertEqual(state["agent"], AGENT_CODE)

    def test_rag_to_builtin(self):
        state = classify_intent({"user_input": "帮我从内部知识库查一份资料"})
        self.assertEqual(state["intent"], "agent_task")
        self.assertEqual(state["agent"], AGENT_RAG)

    def test_workflow_intent(self):
        state = classify_intent({"user_input": "每天 9 点跑工作流"})
        self.assertEqual(state["intent"], "workflow")

    def test_chat_default(self):
        state = classify_intent({"user_input": "你好"})
        self.assertEqual(state["intent"], "chat")

    def test_route_by_intent(self):
        self.assertEqual(route_by_intent({"intent": "agent_task"}), "agent_task")
        self.assertEqual(route_by_intent({"intent": "workflow"}), "workflow")
        self.assertEqual(route_by_intent({"intent": "chat"}), "chat")
        self.assertEqual(route_by_intent({}), "chat")


class TestGraphRouting(unittest.IsolatedAsyncioTestCase):
    async def test_code_review_routes_to_claude_code(self):
        """验收：用户输入「审查代码」→ 路由到 Claude Code。"""
        reg = make_registry()
        graph = build_hub_graph(registry=reg)
        out = await run_hub(graph, {"user_input": "审查代码"})
        self.assertEqual(out["intent"], "agent_task")
        self.assertEqual(out["agent"], AGENT_CODE)
        self.assertIn("claude_code", out["result"])
        self.assertIn("审查代码", out["result"])

    async def test_rag_routes_to_builtin_agent(self):
        """验收：用户输入「查资料」→ 路由到 Built-in Agent。"""
        reg = make_registry()
        graph = build_hub_graph(registry=reg)
        out = await run_hub(graph, {"user_input": "查资料"})
        self.assertEqual(out["intent"], "agent_task")
        self.assertEqual(out["agent"], AGENT_RAG)
        self.assertIn("builtin_rag", out["result"])
        self.assertIn("查资料", out["result"])

    async def test_chat_path_ends_clean(self):
        reg = make_registry()
        graph = build_hub_graph(registry=reg)
        out = await run_hub(graph, {"user_input": "你好呀"})
        self.assertEqual(out["intent"], "chat")
        self.assertEqual(out["result"], "chat")

    async def test_workflow_path(self):
        reg = make_registry()
        graph = build_hub_graph(registry=reg)
        out = await run_hub(graph, {"user_input": "执行工作流 weekly_report"})
        self.assertEqual(out["intent"], "workflow")
        self.assertIn("workflow:", out["result"])
        self.assertEqual(out["workflow_spec"]["name"], "adhoc")

    async def test_dispatch_failure_fallback(self):
        reg = AgentRegistry()

        async def bad_adapter(prompt: str, **kwargs: Any):
            raise RuntimeError("agent down")

        reg.register("claude_code", bad_adapter, ["code.gen"])
        graph = build_hub_graph(registry=reg)
        out = await run_hub(graph, {"user_input": "审查代码"})
        self.assertIn("fallback", out["result"])

    async def test_no_registry_still_routes(self):
        graph = build_hub_graph(registry=None)
        out = await run_hub(graph, {"user_input": "审查代码"})
        self.assertEqual(out["result"], "routed:claude_code")


class TestSyncHelper(unittest.TestCase):
    def test_run_hub_sync(self):
        reg = make_registry()
        graph = build_hub_graph(registry=reg)
        out = run_hub_sync(graph, {"user_input": "查资料"})
        self.assertEqual(out["agent"], AGENT_RAG)


if __name__ == "__main__":
    unittest.main()
