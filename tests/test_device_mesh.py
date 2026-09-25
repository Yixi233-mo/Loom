"""T5 单元测试：Device Mesh — 注册 / 路由 / 在线状态。"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from device_mesh.registry import DeviceMesh, DeviceMeshError  # noqa: E402


class TestRegister(unittest.TestCase):
    def setUp(self):
        self.mesh = DeviceMesh()
        self.mesh.register("pc-1", "pc", ["file.read", "shell.exec"])
        self.mesh.register("tablet-1", "tablet", ["file.read", "notifications"])
        self.mesh.register("mobile-1", "mobile", ["camera", "notifications"])

    def test_register_three_devices(self):
        devices = self.mesh.list_devices()
        self.assertEqual(len(devices), 3)
        ids = {d["device_id"] for d in devices}
        self.assertEqual(ids, {"pc-1", "tablet-1", "mobile-1"})

    def test_register_schema_fields(self):
        d = self.mesh.get("pc-1")
        self.assertEqual(d["device_type"], "pc")
        self.assertEqual(d["capabilities"], ["file.read", "shell.exec"])
        self.assertTrue(d["online"])
        self.assertIsInstance(d["last_seen"], float)

    def test_register_empty_id(self):
        with self.assertRaises(DeviceMeshError):
            self.mesh.register("", "pc", [])

    def test_register_bad_type(self):
        with self.assertRaises(DeviceMeshError):
            self.mesh.register("watch-1", "watch", [])

    def test_register_overwrite(self):
        self.mesh.register("pc-1", "pc", ["shell.exec"])
        self.assertEqual(self.mesh.get("pc-1")["capabilities"], ["shell.exec"])


class TestRoute(unittest.TestCase):
    def setUp(self):
        self.mesh = DeviceMesh()
        self.mesh.register("pc-1", "pc", ["file.read", "shell.exec"])
        self.mesh.register("tablet-1", "tablet", ["file.read", "notifications"])
        self.mesh.register("mobile-1", "mobile", ["camera", "notifications"])

    def test_route_by_device_type(self):
        self.assertEqual(self.mesh.route("pc"), "pc-1")
        self.assertEqual(self.mesh.route("tablet"), "tablet-1")
        self.assertEqual(self.mesh.route("mobile"), "mobile-1")

    def test_route_by_capability(self):
        self.assertEqual(self.mesh.route("pc", "shell.exec"), "pc-1")
        self.assertEqual(self.mesh.route("mobile", "camera"), "mobile-1")
        # tablet-1 / mobile-1 都有 notifications；显式拉开 last_seen 确定胜者
        self.mesh.devices["tablet-1"]["last_seen"] = 1000.0
        self.mesh.devices["mobile-1"]["last_seen"] = 2000.0
        self.assertEqual(self.mesh.route("any", "notifications"), "mobile-1")

    def test_route_any_device_type(self):
        device_id = self.mesh.route("any", "file.read")
        self.assertIn(device_id, {"pc-1", "tablet-1"})

    def test_route_any_no_cap(self):
        device_id = self.mesh.route("any")
        self.assertIn(device_id, {"pc-1", "tablet-1", "mobile-1"})

    def test_route_type_and_cap(self):
        self.assertEqual(self.mesh.route("pc", "file.read"), "pc-1")
        self.assertIsNone(self.mesh.route("mobile", "shell.exec"))

    def test_route_no_candidates(self):
        self.assertIsNone(self.mesh.route("pc", "camera"))
        self.assertIsNone(self.mesh.route("tablet", "shell.exec"))

    def test_route_prefers_latest_last_seen(self):
        self.mesh.devices["pc-1"]["last_seen"] = 3000.0
        self.mesh.devices["tablet-1"]["last_seen"] = 1000.0
        self.mesh.devices["mobile-1"]["last_seen"] = 2000.0
        device_id = self.mesh.route("any", "file.read")
        self.assertEqual(device_id, "pc-1")

    def test_route_bad_type_returns_none(self):
        self.assertIsNone(self.mesh.route("watch"))

    def test_route_empty_mesh(self):
        empty = DeviceMesh()
        self.assertIsNone(empty.route("pc"))
        self.assertIsNone(empty.route("any"))


class TestOnlineState(unittest.TestCase):
    def setUp(self):
        self.mesh = DeviceMesh()
        self.mesh.register("pc-1", "pc", ["file.read", "shell.exec"])
        self.mesh.register("tablet-1", "tablet", ["file.read", "notifications"])
        self.mesh.register("mobile-1", "mobile", ["camera", "notifications"])

    def test_offline_not_routed(self):
        self.mesh.set_online("pc-1", False)
        self.assertIsNone(self.mesh.route("pc", "shell.exec"))
        self.assertEqual(self.mesh.route("any", "file.read"), "tablet-1")

    def test_offline_all_pc(self):
        self.mesh.set_online("pc-1", False)
        self.assertIsNone(self.mesh.route("pc"))

    def test_back_online_routed_again(self):
        self.mesh.set_online("pc-1", False)
        self.assertIsNone(self.mesh.route("pc", "shell.exec"))
        self.mesh.set_online("pc-1", True)
        self.assertEqual(self.mesh.route("pc", "shell.exec"), "pc-1")

    def test_heartbeat_refreshes(self):
        before = self.mesh.get("pc-1")["last_seen"]
        time.sleep(0.01)
        self.mesh.heartbeat("pc-1")
        after = self.mesh.get("pc-1")["last_seen"]
        self.assertGreaterEqual(after, before)
        self.assertTrue(self.mesh.get("pc-1")["online"])

    def test_heartbeat_marks_online(self):
        self.mesh.set_online("pc-1", False)
        self.mesh.heartbeat("pc-1")
        self.assertTrue(self.mesh.get("pc-1")["online"])

    def test_unregister(self):
        self.mesh.unregister("pc-1")
        self.assertEqual(len(self.mesh.list_devices()), 2)
        self.assertIsNone(self.mesh.route("pc", "shell.exec"))

    def test_set_online_unknown(self):
        with self.assertRaises(DeviceMeshError):
            self.mesh.set_online("nope", True)

    def test_heartbeat_unknown(self):
        with self.assertRaises(DeviceMeshError):
            self.mesh.heartbeat("nope")


if __name__ == "__main__":
    unittest.main()
