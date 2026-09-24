"""N5 成本监控测试：Token 熔断 + 字段输出。"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agent_hub.degrade import DegradationChain, Provider  # noqa: E402
from observability.cost import (  # noqa: E402
    DEG_FALLBACK_AGENT,
    DEG_FULL,
    DEG_RULES,
    TOKEN_LIMIT_PER_TASK,
    CircuitOpenError,
    CostMeter,
)
from observability.logging import StructuredLogger, set_logger  # noqa: E402


class TestTokenCircuitBreaker(unittest.TestCase):
    def test_under_limit(self):
        m = CostMeter(task_id="t1", limit=1000)
        m.add_tokens(500)
        self.assertFalse(m.exceeded())
        self.assertEqual(m.tokens_used, 500)

    def test_exactly_limit_ok(self):
        m = CostMeter(task_id="t1", limit=1000)
        m.add_tokens(1000)
        self.assertFalse(m.breaker_open)

    def test_over_limit_trips(self):
        """验收：超限任务被熔断。"""
        m = CostMeter(task_id="t2", limit=1000)
        m.add_tokens(900)
        with self.assertRaises(CircuitOpenError) as ctx:
            m.add_tokens(200)  # 1100 > 1000
        self.assertTrue(m.breaker_open)
        self.assertEqual(ctx.exception.limit, 1000)
        self.assertGreater(ctx.exception.tokens_used, 1000)

    def test_guard_after_trip(self):
        m = CostMeter(task_id="t3", limit=100)
        with self.assertRaises(CircuitOpenError):
            m.add_tokens(500)
        with self.assertRaises(CircuitOpenError):
            m.guard()
        with self.assertRaises(CircuitOpenError):
            m.add_tokens(1)

    def test_default_limit_is_10000(self):
        self.assertEqual(TOKEN_LIMIT_PER_TASK, 10000)
        m = CostMeter()
        self.assertEqual(m.limit, 10000)

    def test_report_fields(self):
        """验收：输出 tokens_used / latency_ms / degradation_level。"""
        m = CostMeter(task_id="t4")
        m.add_tokens(1200)
        m.raise_degradation(DEG_FALLBACK_AGENT)
        rep = m.report()
        d = rep.to_dict()
        self.assertEqual(d["task_id"], "t4")
        self.assertEqual(d["tokens_used"], 1200)
        self.assertIn("latency_ms", d)
        self.assertIsInstance(d["latency_ms"], float)
        self.assertEqual(d["degradation_level"], DEG_FALLBACK_AGENT)
        self.assertIn("estimated_cost_cny", d)
        self.assertFalse(d["breaker_open"])

    def test_report_after_break(self):
        m = CostMeter(task_id="t5", limit=10)
        try:
            m.add_tokens(99)
        except CircuitOpenError:
            pass
        rep = m.report().to_dict()
        self.assertTrue(rep["breaker_open"])
        self.assertGreater(rep["tokens_used"], 10)


class TestDegradeWithCost(unittest.IsolatedAsyncioTestCase):
    async def test_chain_records_degradation_in_meter(self):
        async def fail(p, **k):
            raise RuntimeError("down")

        async def ok(p, **k):
            return {"summary": "ok"}

        chain = DegradationChain(
            [
                Provider("cloud_api", DEG_FULL, fail),
                Provider("ollama", DEG_FALLBACK_AGENT, ok),
            ]
        )
        meter = CostMeter(task_id="n5-chain")
        r = await chain.run("hello", trace_id="n5-chain")
        meter.raise_degradation(r.degradation_level)
        meter.add_tokens(300)
        rep = meter.report().to_dict()
        self.assertEqual(rep["degradation_level"], DEG_FALLBACK_AGENT)
        self.assertEqual(rep["tokens_used"], 300)

    async def test_over_budget_stops(self):
        meter = CostMeter(task_id="n5-budget", limit=500)

        async def heavy(prompt, **kw):
            meter.add_tokens(400)
            return {"ok": True}

        async def rules(prompt, **kw):
            meter.add_tokens(10)  # 若仍熔断会抛
            return {"mode": "rules"}

        # 模拟多次调用直到熔断
        meter.add_tokens(400)
        with self.assertRaises(CircuitOpenError):
            meter.add_tokens(200)
        self.assertTrue(meter.exceeded())
        # 熔断后 guard 拒绝继续
        with self.assertRaises(CircuitOpenError):
            meter.guard()


class TestCostLogFields(unittest.IsolatedAsyncioTestCase):
    async def test_cost_fields_in_structured_log(self):
        log = StructuredLogger()
        set_logger(log)
        try:
            meter = CostMeter(task_id="n5-log")
            meter.add_tokens(800)
            meter.raise_degradation(DEG_RULES)
            rep = meter.report()
            log.emit(
                "cost.report",
                trace_id="n5-log",
                tokens_used=rep.tokens_used,
                latency_ms=rep.latency_ms,
                degradation_level=rep.degradation_level,
            )
            rec = log.records_for("n5-log")[0].to_dict()
            self.assertEqual(rec["tokens_used"], 800)
            self.assertIn("latency_ms", rec)
            self.assertEqual(rec["degradation_level"], DEG_RULES)
        finally:
            set_logger(StructuredLogger())


if __name__ == "__main__":
    unittest.main()
