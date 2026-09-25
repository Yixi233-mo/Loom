"""N3 结构化日志测试：单任务完整追溯。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from observability.cost import TOKEN_LIMIT_PER_TASK, CostMeter
from observability.logging import (
    DEG_RULES,
    StructuredLogger,
    new_trace_id,
)

from scripts.run_hub_server import build_demo_stack


class TestStructuredLogger(unittest.TestCase):
    def test_emit_has_required_fields(self):
        log = StructuredLogger()
        tid = new_trace_id()
        log.emit(
            "hub.submit",
            trace_id=tid,
            device_id="mobile-1",
            agent_name="claude_code",
            workflow_name="daily_report",
            dsl_version="1.0.0",
            task_status="running",
            tokens_used=42,
            latency_ms=12.5,
            degradation_level=0,
            note="x",
        )
        d = log.records_for(tid)[0].to_dict()
        self.assertEqual(d["trace_id"], tid)
        for key in (
            "device_id",
            "agent_name",
            "workflow_name",
            "dsl_version",
            "task_status",
            "tokens_used",
            "latency_ms",
            "degradation_level",
        ):
            self.assertIn(key, d, key)
        self.assertEqual(d["note"], "x")

    def test_span_records_latency(self):
        log = StructuredLogger()
        tid = new_trace_id()
        with log.span("agent.invoke", trace_id=tid, agent_name="builtin_rag") as s:
            s.set(task_status="done", tokens_used=10)
        rec = log.records_for(tid)[0]
        self.assertEqual(rec.event, "agent.invoke")
        self.assertIsNotNone(rec.latency_ms)
        self.assertGreaterEqual(rec.latency_ms, 0)
        self.assertEqual(rec.tokens_used, 10)

    def test_records_for_isolated(self):
        log = StructuredLogger()
        a, b = new_trace_id(), new_trace_id()
        log.emit("e1", trace_id=a)
        log.emit("e2", trace_id=b)
        log.emit("e3", trace_id=a)
        self.assertEqual(log.chain_for(a), ["e1", "e3"])
        self.assertEqual(log.chain_for(b), ["e2"])


class TestSingleTaskTraceability(unittest.TestCase):
    """验收：单次任务能在日志中完整追溯。"""

    def test_full_chain_same_trace_id(self):
        log = StructuredLogger()
        stack = build_demo_stack()
        stack.log = log

        tid = new_trace_id()
        stack.submit_workflow(
            {"name": "daily_report", "device": "pc"}, trace_id=tid
        )
        recs = log.records_for(tid)
        self.assertGreaterEqual(len(recs), 2)
        events = log.chain_for(tid)
        self.assertIn("hub.submit", events)
        # 自动执行 → hub.complete
        self.assertIn("hub.complete", events)

        # 同一 trace_id
        for r in recs:
            self.assertEqual(r.trace_id, tid)

        # 必埋字段可在链路中找到
        blob = json.dumps([r.to_dict() for r in recs], ensure_ascii=False)
        self.assertIn("workflow_name", blob)
        self.assertIn("daily_report", blob)
        self.assertIn("latency_ms", blob)
        self.assertIn("task_status", blob)

        # 任务最终状态可追溯
        done = [r for r in recs if r.task_status == "done"]
        self.assertTrue(done)

    def test_e2e_style_chain(self):
        """E2E 场景：手机触发 → 执行 → 广播，共用同一 trace_id。"""
        log = StructuredLogger()
        stack = build_demo_stack()
        stack.log = log

        tid = "e2e-n3-1"
        stack._emit = None  # type: ignore
        # 模拟三阶段
        stack._trace(tid, "trigger", device="mobile-1", workflow_name="daily_report")
        task_id = stack.submit_workflow(
            {"name": "daily_report", "device": "pc"}, trace_id=tid
        )
        stack._trace(tid, "broadcast", device="tablet-1", task_id=task_id)

        chain = log.chain_for(tid)
        names = set(chain)
        self.assertIn("hub.trigger", names)
        self.assertIn("hub.submit", names)
        self.assertIn("hub.broadcast", names)
        self.assertIn("hub.complete", names)
        for r in log.records_for(tid):
            self.assertEqual(r.trace_id, tid)

    def test_two_tasks_distinct_traces(self):
        log = StructuredLogger()
        stack = build_demo_stack()
        stack.log = log
        t1 = stack.submit_workflow({"name": "daily_report", "device": "pc"})
        t2 = stack.submit_workflow({"name": "daily_report", "device": "pc"})
        self.assertNotEqual(t1, t2)
        self.assertGreater(len(log.records_for(t1)), 0)
        self.assertGreater(len(log.records_for(t2)), 0)
        self.assertEqual(log.records_for(t1)[0].trace_id, t1)


class TestCostFields(unittest.TestCase):
    def test_cost_meter_snapshot(self):
        from observability.cost import CircuitOpenError

        m = CostMeter()
        m.add_tokens(300)
        m.raise_degradation(DEG_RULES)
        snap = m.snapshot()
        self.assertEqual(snap["tokens_used"], 300)
        self.assertEqual(snap["degradation_level"], DEG_RULES)
        self.assertFalse(m.exceeded())
        with self.assertRaises(CircuitOpenError):
            m.add_tokens(TOKEN_LIMIT_PER_TASK)
        self.assertTrue(m.exceeded())


if __name__ == "__main__":
    unittest.main()
