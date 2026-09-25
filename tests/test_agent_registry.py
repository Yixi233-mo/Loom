"""T3 单元测试：Agent Registry — 注册 / 匹配 / 调用 / 异常。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from agent_hub.registry import AgentNotFoundError, AgentRegistry  # noqa: E402


def adapter_factory(tag: str):
    """构造 mock adapter：返回 {tag, prompt, kwargs}。"""

    async def _adapter(prompt: str, **kwargs: Any) -> Dict[str, Any]:
        return {"tag": tag, "prompt": prompt, "kwargs": kwargs}

    return _adapter


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.reg = AgentRegistry()
        self.reg.register("code_reviewer", adapter_factory("code_reviewer"), ["code.review", "file.read"])
        self.reg.register("rag_agent", adapter_factory("rag_agent"), ["rag.query"])
        self.reg.register("shell_agent", adapter_factory("shell_agent"), ["shell.exec", "file.read"])

    def test_register_three_mocks(self):
        names = self.reg.list_agents()
        self.assertEqual(len(names), 3)
        self.assertIn("code_reviewer", names)
        self.assertIn("rag_agent", names)
        self.assertIn("shell_agent", names)

    def test_register_empty_name(self):
        with self.assertRaises(ValueError):
            self.reg.register("", adapter_factory("x"), [])

    def test_register_bad_adapter(self):
        with self.assertRaises(TypeError):
            self.reg.register("bad", "not-callable", [])  # type: ignore

    def test_register_overwrite(self):
        self.reg.register("rag_agent", adapter_factory("v2"), ["rag.query", "rag.write"])
        self.assertEqual(self.reg.capabilities("rag_agent"), ["rag.query", "rag.write"])


class TestMatch(unittest.TestCase):
    def setUp(self):
        self.reg = AgentRegistry()
        self.reg.register("code_reviewer", adapter_factory("code_reviewer"), ["code.review", "file.read"])
        self.reg.register("rag_agent", adapter_factory("rag_agent"), ["rag.query"])
        self.reg.register("shell_agent", adapter_factory("shell_agent"), ["shell.exec", "file.read"])

    def test_match_by_capability(self):
        self.assertEqual(self.reg.match("code.review"), ["code_reviewer"])
        self.assertEqual(self.reg.match("rag.query"), ["rag_agent"])
        self.assertEqual(self.reg.match("shell.exec"), ["shell_agent"])

    def test_match_shared_capability(self):
        hits = self.reg.match("file.read")
        self.assertEqual(sorted(hits), ["code_reviewer", "shell_agent"])

    def test_match_no_hits(self):
        self.assertEqual(self.reg.match("camera"), [])

    def test_capabilities_unknown(self):
        with self.assertRaises(AgentNotFoundError):
            self.reg.capabilities("nope")

    def test_unregister(self):
        self.reg.unregister("rag_agent")
        self.assertEqual(self.reg.list_agents(), ["code_reviewer", "shell_agent"])
        with self.assertRaises(AgentNotFoundError):
            self.reg.unregister("rag_agent")


class TestInvoke(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.reg = AgentRegistry()
        self.reg.register("code_reviewer", adapter_factory("code_reviewer"), ["code.review"])
        self.reg.register("rag_agent", adapter_factory("rag_agent"), ["rag.query"])
        self.reg.register("shell_agent", adapter_factory("shell_agent"), ["shell.exec"])

    async def test_invoke_ok(self):
        result = await self.reg.invoke("code_reviewer", "审查这段代码", depth="full")
        self.assertEqual(result["tag"], "code_reviewer")
        self.assertEqual(result["prompt"], "审查这段代码")
        self.assertEqual(result["kwargs"]["depth"], "full")

    async def test_invoke_each(self):
        for name in ("code_reviewer", "rag_agent", "shell_agent"):
            result = await self.reg.invoke(name, "hi")
            self.assertEqual(result["tag"], name)

    async def test_invoke_unknown(self):
        with self.assertRaises(AgentNotFoundError) as ctx:
            await self.reg.invoke("not_registered", "hi")
        self.assertIn("not_registered", str(ctx.exception))

    async def test_invoke_receives_kwargs(self):
        result = await self.reg.invoke("rag_agent", "q", top_k=5, filters={"lang": "zh"})
        self.assertEqual(result["kwargs"]["top_k"], 5)
        self.assertEqual(result["kwargs"]["filters"], {"lang": "zh"})


if __name__ == "__main__":
    unittest.main()
