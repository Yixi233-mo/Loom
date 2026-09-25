"""N16 R3 — 输出契约 / 指标 / 流式 / ISO 时间。"""

from __future__ import annotations

import asyncio
import unittest

from api.stream_routes import iso_now, iso_ts, sse_events
from observability.metrics import Metrics, get_metrics
from observability.output_contract import (
    OutputContractError,
    check_key_facts,
    complete_with_contract,
    extract_citations,
    extract_output,
    parse_llm_json,
    sanitize_markdown,
    truncate_keep_edges,
)


class TestOutputContract(unittest.TestCase):
    def test_parse_json_and_code_fence(self):
        self.assertEqual(parse_llm_json('{"a":1}'), {"a": 1})
        self.assertEqual(parse_llm_json('```json\n{"a":1}\n```'), {"a": 1})
        with self.assertRaises(OutputContractError):
            parse_llm_json("not json at all")

    def test_retry_once_then_fail(self):
        calls = {"n": 0}

        def bad(_p):
            calls["n"] += 1
            return "still not json"

        with self.assertRaises(OutputContractError):
            asyncio.run(complete_with_contract(bad, "x", retries=1))
        self.assertEqual(calls["n"], 2)

    def test_retry_succeeds(self):
        calls = {"n": 0}

        def flaky(_p):
            calls["n"] += 1
            return '{"ok":true}' if calls["n"] >= 2 else "oops"

        out = asyncio.run(complete_with_contract(flaky, "x", retries=1))
        self.assertTrue(out.ok)
        self.assertEqual(out.data["ok"], True)

    def test_truncate_keep_edges(self):
        s = "A" * 100 + "MID" + "B" * 100
        out, truncated = truncate_keep_edges(s, 50)
        self.assertTrue(truncated)
        self.assertIn("truncated", out)
        self.assertTrue(out.startswith("A"))
        self.assertTrue(out.endswith("B"))

    def test_xss_sanitize(self):
        s = sanitize_markdown('hi <script>alert(1)</script> javascript:alert(1)')
        self.assertNotIn("script", s.lower())
        self.assertNotIn("javascript:", s.lower())

    def test_citations_and_facts(self):
        text = "结果见 chunk_id: abc-1 金额 ¥12.50 日期 2026-13-40"
        self.assertIn("abc-1", extract_citations(text))
        facts = check_key_facts(text)
        self.assertTrue(any(f["type"] == "money" for f in facts))
        date_facts = [f for f in facts if f["type"] == "date"]
        self.assertTrue(date_facts)
        self.assertFalse(date_facts[0]["valid"])

    def test_schema_required(self):
        out = extract_output('{"name":"x"}', schema={"type": "object", "required": ["name", "id"]})
        # schema fail falls back to text with warning
        self.assertTrue(out.warnings or out.data)

    def test_redact_in_output(self):
        out = extract_output('{"key":"sk-abcdefghijklmnop"}')
        self.assertNotIn("sk-abcdefghijklmnop", str(out.data))


class TestMetrics(unittest.TestCase):
    def test_success_rate_and_prom(self):
        m = Metrics()
        m.task_result("done", 120, tokens=10)
        m.task_result("done", 80, tokens=5)
        m.task_result("failed", 200, tokens=0)
        snap = m.snapshot()
        self.assertGreater(snap["success_rate_pct"], 50)
        self.assertEqual(snap["tokens_total"], 15)
        text = m.to_prometheus()
        self.assertIn("loom_success_rate_pct", text)
        self.assertIn("loom_tasks_total", text)

    def test_default_metrics_singleton(self):
        self.assertTrue(hasattr(get_metrics(), "inc"))


class TestStream(unittest.TestCase):
    def test_iso8601_utc(self):
        s = iso_now()
        self.assertTrue(s.endswith("Z"))
        self.assertIn("T", s)
        self.assertEqual(len(s), 20)

    def test_sse_delta_final(self):
        async def collect():
            return [x async for x in sse_events(["ab", "cd"], final_payload={"ok": True})]

        frames = asyncio.run(collect())
        text = "".join(frames)
        self.assertIn("event: delta", text)
        self.assertIn("event: final", text)
        self.assertIn("ok", text)
        self.assertIn("T", iso_ts())


if __name__ == "__main__":
    unittest.main()
