"""T6 单元测试：Task Orchestrator — 路由 / 排队 / 超时 / 状态机。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from device_mesh.registry import DeviceMesh  # noqa: E402
from task_orchestrator.engine import (  # noqa: E402
    InvalidTransitionError,
    TaskError,
    TaskOrchestrator,
    TaskStatus,
)


def make_mesh_with_pc() -> DeviceMesh:
    mesh = DeviceMesh()
    mesh.register("pc-1", "pc", ["file.read", "shell.exec"])
    mesh.register("tablet-1", "tablet", ["file.read"])
    mesh.register("mobile-1", "mobile", ["camera"])
    return mesh


class TestSubmitRoute(unittest.TestCase):
    def setUp(self):
        self.mesh = make_mesh_with_pc()
        self.orch = TaskOrchestrator(self.mesh)

    def test_submit_assigns_matching_device(self):
        task_id = self.orch.submit({"name": "weekly_report", "device": "pc"})
        record = self.orch.get(task_id)
        self.assertEqual(record["status"], TaskStatus.ASSIGNED)
        self.assertEqual(record["assigned_to"], "pc-1")
        self.assertEqual(record["workflow"], "weekly_report")
        self.assertEqual(record["device"], "pc")
        self.assertIsNone(record["error"])

    def test_submit_any_device(self):
        task_id = self.orch.submit({"name": "t", "device": "any"})
        self.assertEqual(self.orch.get(task_id)["status"], TaskStatus.ASSIGNED)

    def test_submit_mobile(self):
        task_id = self.orch.submit({"name": "t", "device": "mobile"})
        record = self.orch.get(task_id)
        self.assertEqual(record["assigned_to"], "mobile-1")

    def test_submit_schema_fields(self):
        task_id = self.orch.submit({"name": "t", "device": "pc"})
        record = self.orch.get(task_id)
        self.assertEqual(record["task_id"], task_id)
        self.assertIn("created_at", record)
        self.assertEqual(record["result"], {})


class TestQueueWhenOffline(unittest.TestCase):
    def setUp(self):
        self.mesh = make_mesh_with_pc()
        self.orch = TaskOrchestrator(self.mesh)

    def test_offline_goes_pending(self):
        self.mesh.set_online("pc-1", False)
        task_id = self.orch.submit({"name": "need_pc", "device": "pc"})
        record = self.orch.get(task_id)
        self.assertEqual(record["status"], TaskStatus.PENDING)
        self.assertIsNone(record["assigned_to"])

    def test_dispatch_after_online(self):
        self.mesh.set_online("pc-1", False)
        task_id = self.orch.submit({"name": "need_pc", "device": "pc"})
        self.assertEqual(self.orch.get(task_id)["status"], TaskStatus.PENDING)

        dispatched = self.orch.dispatch_pending()
        self.assertEqual(dispatched, [])  # 仍离线

        self.mesh.set_online("pc-1", True)
        dispatched = self.orch.dispatch_pending()
        self.assertEqual(dispatched, [task_id])
        self.assertEqual(self.orch.get(task_id)["status"], TaskStatus.ASSIGNED)
        self.assertEqual(self.orch.get(task_id)["assigned_to"], "pc-1")

    def test_multiple_pending_dispatch(self):
        self.mesh.set_online("pc-1", False)
        t1 = self.orch.submit({"name": "a", "device": "pc"})
        t2 = self.orch.submit({"name": "b", "device": "pc"})
        self.assertEqual(sorted(self.orch.pending_ids()), sorted([t1, t2]))

        self.mesh.set_online("pc-1", True)
        dispatched = self.orch.dispatch_pending()
        self.assertEqual(sorted(dispatched), sorted([t1, t2]))

    def test_no_device_stays_pending(self):
        mesh = DeviceMesh()  # 空网格
        orch = TaskOrchestrator(mesh)
        task_id = orch.submit({"name": "t", "device": "pc"})
        self.assertEqual(orch.get(task_id)["status"], TaskStatus.PENDING)
        self.assertEqual(orch.dispatch_pending(), [])


class TestStateMachine(unittest.TestCase):
    def setUp(self):
        self.mesh = make_mesh_with_pc()
        self.orch = TaskOrchestrator(self.mesh)
        self.task_id = self.orch.submit({"name": "t", "device": "pc"})

    def test_happy_path(self):
        self.assertEqual(self.orch.get(self.task_id)["status"], TaskStatus.ASSIGNED)
        self.orch.mark_running(self.task_id)
        self.assertEqual(self.orch.get(self.task_id)["status"], TaskStatus.RUNNING)
        self.orch.mark_done(self.task_id, {"ok": True})
        record = self.orch.get(self.task_id)
        self.assertEqual(record["status"], TaskStatus.DONE)
        self.assertEqual(record["result"], {"ok": True})

    def test_assigned_can_fail(self):
        self.orch.mark_failed(self.task_id, "设备崩溃")
        record = self.orch.get(self.task_id)
        self.assertEqual(record["status"], TaskStatus.FAILED)
        self.assertEqual(record["error"], "设备崩溃")

    def test_pending_can_fail(self):
        self.mesh.set_online("mobile-1", False)
        tid = self.orch.submit({"name": "x", "device": "mobile"})
        self.orch.mark_failed(tid, "放弃")
        self.assertEqual(self.orch.get(tid)["status"], TaskStatus.FAILED)

    def test_illegal_skip_running(self):
        with self.assertRaises(InvalidTransitionError):
            self.orch.mark_done(self.task_id)

    def test_illegal_done_to_running(self):
        self.orch.mark_running(self.task_id)
        self.orch.mark_done(self.task_id)
        with self.assertRaises(InvalidTransitionError):
            self.orch.mark_running(self.task_id)

    def test_illegal_double_done(self):
        self.orch.mark_running(self.task_id)
        self.orch.mark_done(self.task_id)
        with self.assertRaises(InvalidTransitionError):
            self.orch.mark_done(self.task_id)

    def test_illegal_pending_to_running(self):
        self.mesh.set_online("pc-1", False)
        tid = self.orch.submit({"name": "q", "device": "pc"})
        with self.assertRaises(InvalidTransitionError):
            self.orch.mark_running(tid)

    def test_illegal_failed_to_done(self):
        self.orch.mark_failed(self.task_id)
        with self.assertRaises(InvalidTransitionError):
            self.orch.mark_done(self.task_id)

    def test_unknown_task(self):
        with self.assertRaises(TaskError):
            self.orch.get("nope")
        with self.assertRaises(TaskError):
            self.orch.mark_running("nope")


class TestTimeout(unittest.TestCase):
    def setUp(self):
        self.mesh = make_mesh_with_pc()
        self.orch = TaskOrchestrator(self.mesh, timeout_seconds=300.0)

    def test_timeout_marks_failed(self):
        task_id = self.orch.submit({"name": "t", "device": "pc"})
        created = self.orch.get(task_id)["created_at"]
        timed_out = self.orch.check_timeouts(now=created + 301.0)
        self.assertEqual(timed_out, [task_id])
        record = self.orch.get(task_id)
        self.assertEqual(record["status"], TaskStatus.FAILED)
        self.assertIn("超时", record["error"])

    def test_no_timeout_before_limit(self):
        task_id = self.orch.submit({"name": "t", "device": "pc"})
        created = self.orch.get(task_id)["created_at"]
        timed_out = self.orch.check_timeouts(now=created + 299.0)
        self.assertEqual(timed_out, [])
        self.assertEqual(self.orch.get(task_id)["status"], TaskStatus.ASSIGNED)

    def test_timeout_running_also(self):
        task_id = self.orch.submit({"name": "t", "device": "pc"})
        self.orch.mark_running(task_id)
        created = self.orch.get(task_id)["created_at"]
        timed_out = self.orch.check_timeouts(now=created + 400.0)
        self.assertEqual(timed_out, [task_id])
        self.assertEqual(self.orch.get(task_id)["status"], TaskStatus.FAILED)

    def test_done_not_timeout(self):
        task_id = self.orch.submit({"name": "t", "device": "pc"})
        self.orch.mark_running(task_id)
        self.orch.mark_done(task_id, {"ok": 1})
        created = self.orch.get(task_id)["created_at"]
        timed_out = self.orch.check_timeouts(now=created + 9999.0)
        self.assertEqual(timed_out, [])
        self.assertEqual(self.orch.get(task_id)["status"], TaskStatus.DONE)

    def test_pending_not_timeout(self):
        self.mesh.set_online("pc-1", False)
        task_id = self.orch.submit({"name": "t", "device": "pc"})
        created = self.orch.get(task_id)["created_at"]
        timed_out = self.orch.check_timeouts(now=created + 9999.0)
        # pending 等待设备上线，不因超时失败（仍可被分发）
        self.assertEqual(timed_out, [])
        self.assertEqual(self.orch.get(task_id)["status"], TaskStatus.PENDING)


class TestListFilter(unittest.TestCase):
    def test_list_by_status(self):
        mesh = make_mesh_with_pc()
        orch = TaskOrchestrator(mesh)
        a = orch.submit({"name": "a", "device": "pc"})
        mesh.set_online("tablet-1", False)
        b = orch.submit({"name": "b", "device": "tablet"})
        self.assertEqual(len(orch.list_tasks()), 2)
        self.assertEqual(orch.list_tasks(TaskStatus.ASSIGNED)[0]["task_id"], a)
        self.assertEqual(orch.list_tasks(TaskStatus.PENDING)[0]["task_id"], b)


if __name__ == "__main__":
    unittest.main()
