"""CHAT 测试 — 对话区尺寸 / 模型对话 / 意图路由 LLM。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from agent_hub.intent_router import (
    HybridIntentRouter,
    LLMIntentClassifier,
    RuleIntentClassifier,
    _parse_intent_json,
)


# JS 服务测试在 test_chat_js；此处覆盖 Python 意图路由
class TestRuleIntent(unittest.TestCase):
    def test_code_and_rag_and_workflow(self):
        r = RuleIntentClassifier()
        self.assertEqual(r.classify("帮我审查代码")["agent"], "claude_code")
        self.assertEqual(r.classify("查一下资料")["agent"], "builtin_rag")
        self.assertEqual(r.classify("每天 9 点执行工作流")["intent"], "workflow")
        self.assertEqual(r.classify("你好呀")["intent"], "chat")


class TestParseIntentJson(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(
            _parse_intent_json('{"intent":"agent_task","agent":"claude_code"}'),
            {"intent": "agent_task", "agent": "claude_code"},
        )
        self.assertEqual(
            _parse_intent_json('xx {"intent":"chat","agent":null} yy'),
            {"intent": "chat", "agent": None},
        )
        self.assertEqual(
            _parse_intent_json('{"intent":"weird","agent":"x"}'),
            {"intent": "chat", "agent": "x"},
        )


class TestLLMIntent(unittest.IsolatedAsyncioTestCase):
    async def test_llm_classify(self):
        async def complete(prompt: str) -> str:
            return '{"intent":"agent_task","agent":"builtin_rag"}'

        c = LLMIntentClassifier(complete)
        out = await c.classify_async("帮我从知识库找文档")
        self.assertEqual(out["intent"], "agent_task")
        self.assertEqual(out["agent"], "builtin_rag")

    async def test_llm_fail_falls_back(self):
        async def complete(prompt: str) -> str:
            raise RuntimeError("llm down")

        c = LLMIntentClassifier(complete)
        out = await c.classify_async("审查代码")
        self.assertEqual(out["agent"], "claude_code")


class TestHybridRouter(unittest.IsolatedAsyncioTestCase):
    async def test_rule_wins_when_not_chat(self):
        async def complete(prompt: str) -> str:
            return '{"intent":"workflow","agent":null}'

        h = HybridIntentRouter(llm=LLMIntentClassifier(complete), use_llm_for_chat=True)
        out = await h.route_async("审查这段代码")
        self.assertEqual(out["agent"], "claude_code")  # 规则命中，不走 LLM

    async def test_llm_used_for_chat(self):
        async def complete(prompt: str) -> str:
            return '{"intent":"agent_task","agent":"builtin_rag"}'

        h = HybridIntentRouter(llm=LLMIntentClassifier(complete))
        out = await h.route_async("随便聊聊天气吧")
        self.assertEqual(out["intent"], "agent_task")
        self.assertEqual(out["agent"], "builtin_rag")

    async def test_llm_disabled_falls_rule(self):
        h = HybridIntentRouter(use_llm_for_chat=False)
        out = await h.route_async("你好")
        self.assertEqual(out["intent"], "chat")


if __name__ == "__main__":
    unittest.main()
