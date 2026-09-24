"""N6 真实触发调度测试 — cron 解析 / 到点触发 / 热更新。"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.run_hub_server import build_demo_stack  # noqa: E402
from task_orchestrator.scheduler import (  # noqa: E402
    TriggerScheduler,
    load_workflows_cron,
    parse_cron,
)


class TestCronParse(unittest.TestCase):
    def test_parse_star_and_numbers(self):
        c = parse_cron("0 9 * * *")
        self.assertIn(0, c.minute)
        self.assertIn(9, c.hour)
        self.assertEqual(set(c.minute), {0})
        self.assertEqual(len(c.hour), 1)

    def test_parse_lists_ranges_steps(self):
        c = parse_cron("0,30 8-10 * * 1-5")
        self.assertEqual(set(c.minute), {0, 30})
        self.assertEqual(set(c.hour), {8, 9, 10})
        c2 = parse_cron("*/15 * * * *")
        self.assertIn(0, c2.minute)
        self.assertIn(15, c2.minute)
        self.assertIn(45, c2.minute)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            parse_cron("0 9 * *")
        with self.assertRaises(ValueError):
            parse_cron("x 9 * * *")

    def test_matches_datetime(self):
        c = parse_cron("0 9 * * *")
        self.assertTrue(c.matches(datetime(2026, 1, 5, 9, 0, 0)))
        self.assertFalse(c.matches(datetime(2026, 1, 5, 9, 1, 0)))
        # 周一=1 in cron when 1-5
        c2 = parse_cron("0 9 * * 1")
        self.assertTrue(c2.matches(datetime(2026, 1, 5, 9, 0)))  # 2026-01-05 is Monday
        self.assertFalse(c2.matches(datetime(2026, 1, 4, 9, 0)))  # Sunday


class TestSchedulerFire(unittest.TestCase):
    def test_tick_fires_daily_report(self):
        fired = []
        sch = TriggerScheduler(fire=lambda n, p: fired.append((n, p)), tick_seconds=0.1)
        sch.add_or_update("daily_report", "0 9 * * *", {"workflow": "daily_report", "device": "pc"})
        self.assertEqual(sch.tick(datetime(2026, 1, 5, 8, 59)), [])
        self.assertEqual(sch.tick(datetime(2026, 1, 5, 9, 0)), ["daily_report"])
        self.assertEqual(fired[0][0], "daily_report")
        self.assertEqual(fired[0][1]["workflow"], "daily_report")

    def test_cron_hot_reload(self):
        """验收：修改 cron 表达式热生效。"""
        fired = []
        sch = TriggerScheduler(fire=lambda n, p: fired.append(n))
        sch.add_or_update("job1", "0 10 * * *")
        self.assertEqual(sch.tick(datetime(2026, 1, 5, 10, 0)), ["job1"])
        # 热更新为 9:00
        sch.add_or_update("job1", "0 9 * * *")
        self.assertEqual(sch.tick(datetime(2026, 1, 5, 10, 0)), [])
        self.assertEqual(sch.tick(datetime(2026, 1, 5, 9, 0)), ["job1"])
        self.assertEqual(len(fired), 2)


class TestN6Integration(unittest.TestCase):
    def test_load_cron_from_workflows(self):
        jobs = load_workflows_cron(str(ROOT / "plugins" / "example" / "workflows"))
        names = {j.name for j in jobs}
        self.assertIn("daily_report", names)
        dr = next(j for j in jobs if j.name == "daily_report")
        self.assertEqual(dr.cron_expr, "0 9 * * *")

    def test_fire_calls_hub_submit(self):
        """验收：daily_report 可按 cron 真实触发执行。"""
        stack = build_demo_stack()
        fired_tasks = []
        sch = TriggerScheduler(
            fire=lambda name, payload: fired_tasks.append(
                stack.submit_workflow(payload or {"name": name, "device": "pc"})
            )
        )
        sch.add_or_update("daily_report", "0 9 * * *", {"name": "daily_report", "device": "pc"})
        sch.tick(datetime(2026, 1, 5, 9, 0))
        self.assertEqual(len(fired_tasks), 1)
        rec = stack.orch.get(fired_tasks[0])
        self.assertEqual(rec["status"].value, "done")
        self.assertEqual(rec["workflow"], "daily_report")


if __name__ == "__main__":
    unittest.main()
