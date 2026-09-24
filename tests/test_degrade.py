"""N4 降级链测试：Cloud → Ollama → 规则兜底。"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent_hub.degrade import (  # noqa: E402
    DegradationChain,
    DegradeResult,
    Provider,
    default_chain,
    rules_provider,
)
from observability.logging import (  # noqa: E402
    DEG_FALLBACK_AGENT,
    DEG_FULL,
    DEG_RULES,
    StructuredLogger,
    set_logger,
)


async def ok_cloud(prompt: str, **kw):
    return {"summary": "cloud-ok", "level": 0}


async def fail_cloud(prompt: str, **kw):
    raise RuntimeError("API 不可用")


async def ok_ollama(prompt: str, **kw):
    return {"summary": "ollama-ok", "level": 1}


async def fail_ollama(prompt: str, **kw):
    raise RuntimeError("Ollama 挂了")


async def ok_rules(prompt: str, **kw):
    return {"summary": "rules-ok", "level": 2}


class TestDegradationChain(unittest.IsolatedAsyncioTestCase):
    async def test_cloud_ok_no_degrade(self):
        chain = DegradationChain(
            [Provider("cloud_api", DEG_FULL, ok_cloud), Provider("rules", DEG_RULES, ok_rules)]
        )
        r = await chain.run("hi")
        self.assertEqual(r.provider, "cloud_api")
        self.assertEqual(r.degradation_level, DEG_FULL)
        self.assertFalse(r.used_fallback)

    async def test_api_down_switch_ollama(self):
        """验收：模拟 API 不可用，自动切 Ollama。"""
        chain = DegradationChain(
            [
                Provider("cloud_api", DEG_FULL, fail_cloud),
                Provider("ollama", DEG_FALLBACK_AGENT, ok_ollama),
                Provider("rules", DEG_RULES, ok_rules),
            ]
        )
        r = await chain.run("审查代码", trace_id="n4-1")
        self.assertEqual(r.provider, "ollama")
        self.assertEqual(r.degradation_level, DEG_FALLBACK_AGENT)
        self.assertTrue(r.used_fallback)
        self.assertTrue(any("API 不可用" in e for e in r.errors))
        self.assertEqual(r.value["summary"], "ollama-ok")

    async def test_all_down_rules_level2(self):
        """验收：全不可用时返回规则兜底（degradation_level=2）。"""
        chain = DegradationChain(
            [
                Provider("cloud_api", DEG_FULL, fail_cloud),
                Provider("ollama", DEG_FALLBACK_AGENT, fail_ollama),
                Provider("rules", DEG_RULES, rules_provider),
            ]
        )
        r = await chain.run("帮我总结一下", trace_id="n4-2")
        self.assertEqual(r.provider, "rules")
        self.assertEqual(r.degradation_level, DEG_RULES)
        self.assertEqual(r.degradation_level, 2)
        self.assertIn("规则兜底", r.value["summary"])
        self.assertEqual(len(r.errors), 2)

    async def test_default_chain_falls_to_rules(self):
        # 默认 chain 的 cloud/ollama 均未配置 → 规则
        r = await asyncio.wait_for(default_chain().run("你好"), timeout=5)
        self.assertEqual(r.provider, "rules")
        self.assertEqual(r.degradation_level, DEG_RULES)

    async def test_switch_logged(self):
        log = StructuredLogger()
        set_logger(log)
        try:
            chain = DegradationChain(
                [
                    Provider("cloud_api", DEG_FULL, fail_cloud),
                    Provider("ollama", DEG_FALLBACK_AGENT, ok_ollama),
                ]
            )
            r = await chain.run("x", trace_id="n4-log")
            events = log.chain_for("n4-log")
            self.assertIn("degrade.attempt", events)
            self.assertIn("degrade.switch", events)
            recs = log.records_for("n4-log")
            self.assertTrue(any(e.agent_name == "ollama" for e in recs))
        finally:
            set_logger(StructuredLogger())


if __name__ == "__main__":
    unittest.main()
