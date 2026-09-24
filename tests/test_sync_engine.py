"""T9 单元测试：Sync Engine — 并发写 / 增量拉取 / 广播 / 乐观锁。"""

from __future__ import annotations

import asyncio
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Tuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sync.sync_engine import (  # noqa: E402
    EVENT_KEY_DELETED,
    EVENT_KEY_UPDATED,
    SyncConflictError,
    SyncEngine,
)


class TestBasicKV(unittest.IsolatedAsyncioTestCase):
    async def test_put_get(self):
        eng = SyncEngine()
        entry = await eng.put("notes:1", {"title": "hello"}, device_id="pc-1")
        self.assertEqual(entry["key"], "notes:1")
        self.assertEqual(entry["value"], {"title": "hello"})
        self.assertEqual(entry["updated_by"], "pc-1")
        self.assertEqual(entry["version"], 1)

        got = eng.get("notes:1")
        self.assertEqual(got["value"], {"title": "hello"})
        self.assertEqual(got["version"], 1)

    async def test_get_missing(self):
        eng = SyncEngine()
        self.assertIsNone(eng.get("nope"))
        self.assertIsNone(eng.get_version("nope"))

    async def test_overwrite_increments_version(self):
        eng = SyncEngine()
        e1 = await eng.put("k", 1, "pc-1")
        e2 = await eng.put("k", 2, "pc-2")
        self.assertEqual(e1["version"], 1)
        self.assertEqual(e2["version"], 2)
        self.assertEqual(eng.get("k")["value"], 2)
        self.assertEqual(eng.get_version("k"), 2)

    async def test_delete(self):
        eng = SyncEngine()
        await eng.put("k", {"a": 1}, "pc-1")
        entry = await eng.delete("k", "pc-2")
        self.assertTrue(entry["deleted"])
        self.assertIsNone(eng.get("k"))
        self.assertGreaterEqual(entry["version"], 2)

    async def test_global_version_monotonic(self):
        eng = SyncEngine()
        v0 = eng.latest_version()
        await eng.put("a", 1, "pc")
        v1 = eng.latest_version()
        await eng.put("b", 2, "pc")
        v2 = eng.latest_version()
        self.assertEqual([v0, v1, v2], [0, 1, 2])


class TestConcurrentWrites(unittest.IsolatedAsyncioTestCase):
    async def test_two_devices_same_key_versions_increments(self):
        """验收：两设备并发写同一 key，版本号正确递增。"""
        eng = SyncEngine()

        async def write(dev: str, val: int) -> Dict[str, Any]:
            return await eng.put("shared", val, dev)

        r1, r2 = await asyncio.gather(write("pc-1", 1), write("mobile-1", 2))
        versions = sorted([r1["version"], r2["version"]])
        self.assertEqual(versions, [1, 2])
        self.assertEqual(eng.get_version("shared"), 2)
        self.assertIn(eng.get("shared")["updated_by"], {"pc-1", "mobile-1"})
        self.assertIn(eng.get("shared")["value"], [1, 2])

    async def test_many_writes_unique_versions(self):
        eng = SyncEngine()

        async def write(i: int):
            return await eng.put("hot", i, f"dev-{i % 3}")

        results = await asyncio.gather(*(write(i) for i in range(20)))
        versions = sorted(r["version"] for r in results)
        self.assertEqual(versions, list(range(1, 21)))
        self.assertEqual(eng.latest_version(), 20)

    async def test_cross_key_versions_share_counter(self):
        eng = SyncEngine()
        e1 = await eng.put("a", 1, "pc")
        e2 = await eng.put("b", 2, "pc")
        e3 = await eng.put("a", 3, "pc")
        self.assertEqual([e1["version"], e2["version"], e3["version"]], [1, 2, 3])


class TestOptimisticLock(unittest.IsolatedAsyncioTestCase):
    async def test_expected_version_match(self):
        eng = SyncEngine()
        e1 = await eng.put("k", 1, "pc-1", expected_version=0)
        self.assertEqual(e1["version"], 1)
        e2 = await eng.put("k", 2, "pc-2", expected_version=1)
        self.assertEqual(e2["version"], 2)

    async def test_expected_version_conflict(self):
        eng = SyncEngine()
        await eng.put("k", 1, "pc-1", expected_version=0)
        with self.assertRaises(SyncConflictError) as ctx:
            await eng.put("k", 2, "pc-2", expected_version=0)
        self.assertEqual(ctx.exception.expected, 0)
        self.assertEqual(ctx.exception.actual, 1)
        # 值仍为第一次写入
        self.assertEqual(eng.get("k")["value"], 1)

    async def test_expected_version_missing_key(self):
        eng = SyncEngine()
        with self.assertRaises(SyncConflictError):
            await eng.put("k", 1, "pc", expected_version=5)


class TestIncrementalPull(unittest.IsolatedAsyncioTestCase):
    async def test_offline_device_pulls_increment(self):
        """验收：离线设备上线后能拉取增量。"""
        eng = SyncEngine()
        # 离线期间其它设备写了 3 次
        await eng.put("a", 1, "pc-1")
        await eng.put("b", 2, "pc-1")
        await eng.put("a", 3, "tablet-1")

        # 离线设备记住的 version = 1（只见过第一次）
        changes = eng.changes(since_version=1)
        self.assertEqual(len(changes), 2)
        self.assertEqual([c["key"] for c in changes], ["b", "a"])
        self.assertEqual([c["version"] for c in changes], [2, 3])

        # 无增量
        self.assertEqual(eng.changes(since_version=3), [])
        # 全量
        self.assertEqual(len(eng.changes(since_version=0)), 3)

    async def test_changes_includes_latest_value(self):
        eng = SyncEngine()
        await eng.put("k", {"v": 1}, "pc-1")
        await eng.put("k", {"v": 2}, "pc-2")
        changes = eng.changes(since_version=1)
        self.assertEqual(changes[0]["value"], {"v": 2})
        self.assertEqual(changes[0]["version"], 2)

    async def test_delete_appears_in_changes(self):
        eng = SyncEngine()
        await eng.put("k", 1, "pc")
        await eng.delete("k", "pc")
        changes = eng.changes(since_version=1)
        self.assertEqual(len(changes), 1)
        self.assertTrue(changes[0].get("deleted"))


class TestBroadcast(unittest.IsolatedAsyncioTestCase):
    async def test_put_broadcasts(self):
        events: List[Tuple[str, dict]] = []

        def on_broadcast(event: str, data: dict) -> None:
            events.append((event, data))

        eng = SyncEngine(on_broadcast=on_broadcast)
        entry = await eng.put("k", {"x": 1}, "pc-1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0][0], EVENT_KEY_UPDATED)
        self.assertEqual(events[0][1]["key"], "k")
        self.assertEqual(events[0][1]["version"], entry["version"])

    async def test_delete_broadcasts(self):
        events: List[Tuple[str, dict]] = []
        eng = SyncEngine(on_broadcast=lambda e, d: events.append((e, d)))
        await eng.put("k", 1, "pc")
        await eng.delete("k", "pc")
        self.assertEqual(events[0][0], EVENT_KEY_UPDATED)
        self.assertEqual(events[1][0], EVENT_KEY_DELETED)

    async def test_async_broadcast(self):
        events: List[str] = []

        async def on_broadcast(event: str, data: dict) -> None:
            events.append(event)

        eng = SyncEngine(on_broadcast=on_broadcast)
        await eng.put("k", 1, "pc")
        self.assertEqual(events, [EVENT_KEY_UPDATED])

    async def test_broadcast_error_does_not_break_put(self):
        def boom(event: str, data: dict) -> None:
            raise RuntimeError("broadcast down")

        eng = SyncEngine(on_broadcast=boom)
        entry = await eng.put("k", 1, "pc")
        self.assertEqual(entry["version"], 1)
        self.assertEqual(eng.get("k")["value"], 1)

    async def test_no_broadcast_when_conflict(self):
        events: List[str] = []
        eng = SyncEngine(on_broadcast=lambda e, d: events.append(e))
        await eng.put("k", 1, "pc", expected_version=0)
        with self.assertRaises(SyncConflictError):
            await eng.put("k", 2, "pc", expected_version=0)
        self.assertEqual(events, [EVENT_KEY_UPDATED])


if __name__ == "__main__":
    unittest.main()
