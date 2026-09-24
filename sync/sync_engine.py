"""Sync Engine — 版本号同步 + 状态广播。

存储：SQLite（内存或文件）。
- kv：每 key 当前值
- changelog：append-only 变更流，支撑离线增量拉取
并发写同一 key：事务内全局版本原子递增。
广播：每次成功写入/删除触发 on_broadcast(event, data)。
"""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from typing import Any, Callable, Dict, List, Optional

EVENT_KEY_UPDATED = "key.updated"
EVENT_KEY_DELETED = "key.deleted"

BroadcastFn = Callable[[str, Dict[str, Any]], Any]


class SyncConflictError(Exception):
    """乐观锁冲突：expected_version 与当前版本不一致。"""

    def __init__(self, key: str, expected: Optional[int], actual: Optional[int]):
        self.key = key
        self.expected = expected
        self.actual = actual
        super().__init__(
            f"同步冲突 key={key} expected_version={expected} actual={actual}"
        )


class SyncEngine:
    """中心同步存储：KV + 全局版本号 + 变更日志。"""

    def __init__(
        self,
        db_path: str = ":memory:",
        on_broadcast: Optional[BroadcastFn] = None,
    ) -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = asyncio.Lock()
        self._on_broadcast = on_broadcast
        self._init_db()

    def _init_db(self) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                version INTEGER NOT NULL,
                updated_by TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS changelog (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                op TEXT NOT NULL,
                value TEXT,
                version INTEGER NOT NULL,
                updated_by TEXT NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS meta (
                name TEXT PRIMARY KEY,
                value INTEGER NOT NULL
            )
            """
        )
        cur.execute(
            "INSERT OR IGNORE INTO meta(name, value) VALUES ('global_version', 0)"
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # 读
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        row = self._conn.execute(
            "SELECT key, value, version, updated_by, updated_at FROM kv WHERE key = ?",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_entry(row)

    def get_version(self, key: str) -> Optional[int]:
        row = self._conn.execute(
            "SELECT version FROM kv WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else int(row["version"])

    def latest_version(self) -> int:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE name = 'global_version'"
        ).fetchone()
        return int(row["value"]) if row else 0

    def changes(self, since_version: int = 0) -> List[Dict[str, Any]]:
        """增量拉取：返回 version > since_version 的变更日志（按 version 升序）。

        包含 put 与 delete；离线设备可按此流重放。
        """
        rows = self._conn.execute(
            """
            SELECT key, op, value, version, updated_by, updated_at
            FROM changelog WHERE version > ?
            ORDER BY version ASC, seq ASC
            """,
            (since_version,),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for r in rows:
            entry: Dict[str, Any] = {
                "key": r["key"],
                "op": r["op"],
                "version": r["version"],
                "updated_by": r["updated_by"],
                "updated_at": r["updated_at"],
            }
            if r["op"] == "delete":
                entry["value"] = None
                entry["deleted"] = True
            else:
                entry["value"] = json.loads(r["value"]) if r["value"] is not None else None
            out.append(entry)
        return out

    def all_keys(self) -> List[str]:
        rows = self._conn.execute("SELECT key FROM kv ORDER BY key").fetchall()
        return [r["key"] for r in rows]

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> Dict[str, Any]:
        return {
            "key": row["key"],
            "value": json.loads(row["value"]),
            "version": row["version"],
            "updated_by": row["updated_by"],
            "updated_at": row["updated_at"],
        }

    # ------------------------------------------------------------------
    # 写
    # ------------------------------------------------------------------

    def _next_version(self) -> int:
        self._conn.execute(
            "UPDATE meta SET value = value + 1 WHERE name = 'global_version'"
        )
        row = self._conn.execute(
            "SELECT value FROM meta WHERE name = 'global_version'"
        ).fetchone()
        return int(row["value"])

    def _append_changelog(
        self,
        key: str,
        op: str,
        value: Any,
        version: int,
        device_id: str,
        now: float,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO changelog(key, op, value, version, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                key,
                op,
                json.dumps(value, ensure_ascii=False) if value is not None else None,
                version,
                device_id,
                now,
            ),
        )

    def _put_sync(
        self,
        key: str,
        value: Any,
        device_id: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        current = self.get_version(key)
        if expected_version is not None:
            if current is None and expected_version != 0:
                raise SyncConflictError(key, expected_version, 0)
            if current is not None and expected_version != current:
                raise SyncConflictError(key, expected_version, current)

        version = self._next_version()
        now = time.time()
        self._conn.execute(
            """
            INSERT INTO kv(key, value, version, updated_by, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                version = excluded.version,
                updated_by = excluded.updated_by,
                updated_at = excluded.updated_at
            """,
            (key, json.dumps(value, ensure_ascii=False), version, device_id, now),
        )
        self._append_changelog(key, "put", value, version, device_id, now)
        self._conn.commit()
        return {
            "key": key,
            "value": value,
            "version": version,
            "updated_by": device_id,
            "updated_at": now,
            "op": "put",
        }

    def _delete_sync(self, key: str, device_id: str) -> Optional[Dict[str, Any]]:
        existing = self.get(key)
        if existing is None:
            return None
        version = self._next_version()
        now = time.time()
        self._conn.execute("DELETE FROM kv WHERE key = ?", (key,))
        self._append_changelog(key, "delete", None, version, device_id, now)
        self._conn.commit()
        return {
            "key": key,
            "value": None,
            "version": version,
            "updated_by": device_id,
            "updated_at": now,
            "deleted": True,
            "op": "delete",
        }

    async def put(
        self,
        key: str,
        value: Any,
        device_id: str,
        expected_version: Optional[int] = None,
    ) -> Dict[str, Any]:
        """写入 KV，版本原子递增；成功后广播 key.updated。"""
        async with self._lock:
            entry = self._put_sync(key, value, device_id, expected_version)
        await self._emit(EVENT_KEY_UPDATED, entry)
        return entry

    async def delete(self, key: str, device_id: str) -> Optional[Dict[str, Any]]:
        async with self._lock:
            entry = self._delete_sync(key, device_id)
        if entry is not None:
            await self._emit(EVENT_KEY_DELETED, entry)
        return entry

    # ------------------------------------------------------------------
    # 广播
    # ------------------------------------------------------------------

    async def _emit(self, event: str, data: Dict[str, Any]) -> None:
        if self._on_broadcast is None:
            return
        try:
            result = self._on_broadcast(event, data)
            if asyncio.iscoroutine(result):
                await result
        except Exception:  # noqa: BLE001 — 广播失败不影响写入
            pass

    def close(self) -> None:
        self._conn.close()
