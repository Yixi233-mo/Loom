"""T15 端到端测试：手机触发 → PC 执行 → 平板查看 + trace_id 贯穿。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from plugins.example.notes_runtime import NotesStore, make_notes_tools  # noqa: E402
from tests.e2e.orchestrator import E2EOrchestrator  # noqa: E402

WORKFLOW = ROOT / "plugins" / "example" / "workflows" / "mobile_to_pc_pdf.yaml"


def make_orch() -> E2EOrchestrator:
    store = NotesStore()
    store.create("预置", "PDF 路径示例")
    return E2EOrchestrator(
        workflow_yaml=str(WORKFLOW),
        tools=make_notes_tools(store),
        agents={
            "builtin_rag": lambda p: {"summary": f"RAG: {p[:40]}", "citations": []},
        },
    )


class TestE2EClosedLoop(unittest.TestCase):
    def test_mobile_trigger_pc_execute_tablet_view(self):
        """验收：完整闭环 — 手机触发 → Hub 路由 → PC 执行 → 平板查看。"""
        orch = make_orch()
        orch.register_device("mobile-1", "mobile", ["camera", "notifications"])
        orch.register_device("pc-1", "pc", ["file.read", "shell.exec"])
        orch.register_device("tablet-1", "tablet", ["file.read", "notifications"])

        trace_id = orch.trigger_from_mobile(
            "mobile-1",
            {"workflow": "mobile_to_pc_pdf", "pdf": "spec.pdf"},
        )

        stages = orch.stages(trace_id)
        self.assertIn("trigger", stages)
        self.assertIn("route", stages)
        self.assertIn("execute", stages)
        self.assertIn("broadcast", stages)
        self.assertIn("view", stages)

        # 手机触发
        trigger = [e for e in orch.events_for(trace_id) if e.stage == "trigger"][0]
        self.assertEqual(trigger.device, "mobile-1")

        # 路由到 PC
        route = [e for e in orch.events_for(trace_id) if e.stage == "route"][0]
        self.assertEqual(route.detail["assigned_to"], "pc-1")

        # PC 执行成功
        execute = [e for e in orch.events_for(trace_id) if e.stage == "execute"][-1]
        self.assertEqual(execute.device, "pc-1")
        self.assertEqual(execute.detail["status"], "done")

        # 平板查看到结果
        views = [e for e in orch.events_for(trace_id) if e.stage == "view"]
        view_devices = {e.device for e in views}
        self.assertIn("tablet-1", view_devices)
        self.assertIn("mobile-1", view_devices)
        self.assertEqual(views[0].detail["summary"]["trace_id"], trace_id)
        self.assertEqual(views[0].detail["summary"]["status"], "done")

        # 结果已进 Sync（可拉取）
        sync_keys = orch.sync.all_keys()
        self.assertTrue(any(k.startswith("task:") and k.endswith(":result") for k in sync_keys))

    def test_result_visible_on_tablet(self):
        orch = make_orch()
        orch.register_device("mobile-1", "mobile", ["notifications"])
        orch.register_device("pc-1", "pc", ["shell.exec"])
        orch.register_device("tablet-1", "tablet", ["notifications"])

        trace_id = orch.trigger_from_mobile("mobile-1", {"workflow": "mobile_to_pc_pdf"})
        summary = orch.results[trace_id]
        self.assertEqual(summary["status"], "done")
        self.assertIn("steps", summary)
        self.assertIn("extract", summary["steps"])


class TestTraceId(unittest.TestCase):
    def test_trace_id_spans_all_stages(self):
        """验收：有 trace_id 贯穿全链路。"""
        orch = make_orch()
        orch.register_device("mobile-1", "mobile", ["notifications"])
        orch.register_device("pc-1", "pc", ["shell.exec"])
        orch.register_device("tablet-1", "tablet", ["notifications"])

        trace_id = orch.trigger_from_mobile("mobile-1", {"workflow": "mobile_to_pc_pdf"})
        events = orch.events_for(trace_id)
        self.assertGreaterEqual(len(events), 4)
        for ev in events:
            self.assertEqual(ev.trace_id, trace_id)

        # 同一 trace_id 覆盖 trigger/route/execute/broadcast/view
        stages = set(orch.stages(trace_id))
        self.assertEqual(
            stages, {"trigger", "route", "execute", "broadcast", "view"}
        )

    def test_custom_trace_id(self):
        orch = make_orch()
        orch.register_device("mobile-1", "mobile", ["notifications"])
        orch.register_device("pc-1", "pc", ["shell.exec"])

        tid = "trace-e2e-001"
        got = orch.trigger_from_mobile(
            "mobile-1", {"workflow": "mobile_to_pc_pdf"}, trace_id=tid
        )
        self.assertEqual(got, tid)
        for ev in orch.events_for(tid):
            self.assertEqual(ev.trace_id, tid)

    def test_two_tasks_distinct_traces(self):
        orch = make_orch()
        orch.register_device("mobile-1", "mobile", ["notifications"])
        orch.register_device("pc-1", "pc", ["shell.exec"])

        t1 = orch.trigger_from_mobile("mobile-1", {"workflow": "mobile_to_pc_pdf"})
        t2 = orch.trigger_from_mobile("mobile-1", {"workflow": "mobile_to_pc_pdf"})
        self.assertNotEqual(t1, t2)
        self.assertEqual(len(orch.events_for(t1)), len(orch.events_for(t2)))

    def test_trace_events_persist_in_sync(self):
        orch = make_orch()
        orch.register_device("mobile-1", "mobile", ["notifications"])
        orch.register_device("pc-1", "pc", ["shell.exec"])
        orch.register_device("tablet-1", "tablet", ["notifications"])

        trace_id = orch.trigger_from_mobile("mobile-1", {"workflow": "mobile_to_pc_pdf"})
        # Sync 中可按增量拉取（模拟离线上线）
        changes = orch.sync.changes(since_version=0)
        self.assertTrue(any(trace_id in str(c.get("value")) for c in changes))


class TestOfflineQueueE2E(unittest.TestCase):
    def test_pc_offline_queues_then_runs(self):
        """扩展：PC 离线时排队，上线后自动分发执行。"""
        orch = make_orch()
        orch.register_device("mobile-1", "mobile", ["notifications"])
        orch.register_device("pc-1", "pc", ["shell.exec"])
        orch.mesh.set_online("pc-1", False)

        trace_id = orch.trigger_from_mobile("mobile-1", {"workflow": "mobile_to_pc_pdf"})
        self.assertEqual(orch.results[trace_id]["status"], "pending")

        # PC 上线 → 分发
        orch.mesh.set_online("pc-1", True)
        dispatched = orch.orch.dispatch_pending()
        self.assertGreaterEqual(len(dispatched), 1)
        task_id = orch.results[trace_id]["task_id"]
        self.assertIn(task_id, dispatched)
        self.assertEqual(orch.orch.get(task_id)["assigned_to"], "pc-1")


if __name__ == "__main__":
    unittest.main()
