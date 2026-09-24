"""意图路由 — 规则优先，可插拔 LLM 分类器。"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional, Protocol

logger = logging.getLogger(__name__)

# 规则（与 agent_hub.graph 对齐）
_CODE_KEYWORDS = ("审查代码", "代码审查", "审查这段代码", "code review", "review code")
_RAG_KEYWORDS = (
    "查资料",
    "查知识库",
    "知识库",
    "检索",
    "找资料",
    "查文档",
    "查询资料",
    "资料",
)
_WORKFLOW_KEYWORDS = ("工作流", "workflow", "定时任务", "每天", "每周", "触发")


class IntentClassifier(Protocol):
    def classify(self, text: str) -> Dict[str, Any]:
        """返回 {"intent": "agent_task|workflow|chat", "agent": str|None}"""
        ...


class RuleIntentClassifier:
    def classify(self, text: str) -> Dict[str, Any]:
        low = (text or "").lower()
        if any(k.lower() in low or k in (text or "") for k in _CODE_KEYWORDS):
            return {"intent": "agent_task", "agent": "claude_code"}
        if any(k.lower() in low or k in (text or "") for k in _RAG_KEYWORDS):
            return {"intent": "agent_task", "agent": "builtin_rag"}
        if any(k.lower() in low or k in (text or "") for k in _WORKFLOW_KEYWORDS):
            return {"intent": "workflow", "agent": None}
        return {"intent": "chat", "agent": None}


class LLMIntentClassifier:
    """用自定义 LLM 做意图分类（可插拔到 Hub）。"""

    def __init__(self, complete_fn, fallback: Optional[IntentClassifier] = None):
        self.complete_fn = complete_fn  # async (text) -> str
        self.fallback = fallback or RuleIntentClassifier()

    def classify(self, text: str) -> Dict[str, Any]:
        """同步包装；事件循环内请用 classify_async。"""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                raise RuntimeError("use classify_async")
            return loop.run_until_complete(self.classify_async(text))
        except RuntimeError:
            return asyncio.run(self.classify_async(text))

    async def classify_async(self, text: str) -> Dict[str, Any]:
        prompt = (
            "把用户输入分类为 JSON，仅输出 JSON：\n"
            '{"intent":"agent_task|workflow|chat","agent":"claude_code|builtin_rag|null"}\n'
            "规则：代码审查→agent_task/claude_code；查资料→agent_task/builtin_rag；"
            "定时/工作流→workflow；闲聊→chat。\n"
            f"用户输入：{text}"
        )
        try:
            raw = await self.complete_fn(prompt)
            return _parse_intent_json(raw)
        except Exception as e:  # noqa: BLE001
            logger.warning("LLM 意图分类失败，回退规则: %s", e)
            return self.fallback.classify(text)


def _parse_intent_json(raw: str) -> Dict[str, Any]:
    m = re.search(r"\{[^}]+\}", raw or "")
    if not m:
        raise ValueError(f"无 JSON: {raw!r}")
    data = json.loads(m.group(0))
    intent = data.get("intent") or "chat"
    if intent not in ("agent_task", "workflow", "chat"):
        intent = "chat"
    agent = data.get("agent")
    if agent in (None, "null", ""):
        agent = None
    return {"intent": intent, "agent": agent}


class HybridIntentRouter:
    """规则优先；规则置信度低（chat）时可选用 LLM。"""

    def __init__(
        self,
        rule: Optional[RuleIntentClassifier] = None,
        llm: Optional[LLMIntentClassifier] = None,
        use_llm_for_chat: bool = True,
    ):
        self.rule = rule or RuleIntentClassifier()
        self.llm = llm
        self.use_llm_for_chat = use_llm_for_chat

    def route(self, text: str) -> Dict[str, Any]:
        r = self.rule.classify(text)
        if r.get("intent") != "chat" or not (self.use_llm_for_chat and self.llm):
            return r
        try:
            return self.llm.classify(text)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            return r

    async def route_async(self, text: str) -> Dict[str, Any]:
        r = self.rule.classify(text)
        if r.get("intent") != "chat" or not (self.use_llm_for_chat and self.llm):
            return r
        try:
            return await self.llm.classify_async(text)  # type: ignore[union-attr]
        except Exception:  # noqa: BLE001
            return r
