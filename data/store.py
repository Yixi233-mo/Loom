"""数据层 — SQLite WAL / 路径可配 / 自动建目录建表 / 索引 / 迁移（N16 第 5 章）。"""

from __future__ import annotations

import os
import shutil
import sqlite3
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# 5.2 默认路径可配
DEFAULT_DB_REL = "data/loom.db"
ENV_DB_PATH = "LOOM_DB_PATH"
ENV_DATA_DIR = "LOOM_DATA_DIR"

SCHEMA_VERSION = 1


def default_data_dir(root: Optional[str | Path] = None) -> Path:
    base = Path(root) if root else Path(os.environ.get(ENV_DATA_DIR, "."))
    return (base / "data").resolve()


def resolve_db_path(root: Optional[str | Path] = None) -> Path:
    """5.2 路径可配，默认 ./data/loom.db。"""
    env = os.environ.get(ENV_DB_PATH, "").strip()
    if env:
        p = Path(env)
    else:
        p = default_data_dir(root) / "loom.db"
    return p


def ensure_parent(path: Path) -> None:
    """5.7 数据目录自动创建。"""
    path.parent.mkdir(parents=True, exist_ok=True)


# 5.5 迁移：版本号 → SQL 序列
MIGRATIONS: Dict[int, Sequence[str]] = {
    1: (
        """
        CREATE TABLE IF NOT EXISTS kv (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            version INTEGER NOT NULL,
            updated_by TEXT NOT NULL,
            updated_at REAL NOT NULL
        )
        """,
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
        """,
        """
        CREATE TABLE IF NOT EXISTS meta (
            name TEXT PRIMARY KEY,
            value INTEGER NOT NULL
        )
        """,
        "INSERT OR IGNORE INTO meta(name, value) VALUES ('global_version', 0)",
        # 5.9 查询索引
        "CREATE INDEX IF NOT EXISTS idx_changelog_key ON changelog(key)",
        "CREATE INDEX IF NOT EXISTS idx_changelog_version ON changelog(version)",
        "CREATE INDEX IF NOT EXISTS idx_changelog_updated ON changelog(updated_at)",
    ),
}


@dataclass
class DbInfo:
    path: str
    journal_mode: str
    schema_version: int
    size_bytes: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "journal_mode": self.journal_mode,
            "schema_version": self.schema_version,
            "size_bytes": self.size_bytes,
        }


class Database:
    """线程安全 SQLite 封装：WAL + 迁移 + 索引。"""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            ensure_parent(Path(self.path))
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._apply_pragmas()
        self.migrate()

    def _apply_pragmas(self) -> None:
        """5.1 WAL + 并发友好。"""
        cur = self._conn.cursor()
        try:
            cur.execute("PRAGMA journal_mode=WAL")
        except sqlite3.Error:
            pass
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA foreign_keys=ON")
        self._conn.commit()

    @property
    def conn(self) -> sqlite3.Connection:
        return self._conn

    def migrate(self) -> int:
        """5.5 按版本应用迁移；返回当前 schema 版本。"""
        with self._lock:
            cur = self._conn.cursor()
            cur.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " version INTEGER PRIMARY KEY,"
                " applied_at REAL NOT NULL)"
            )
            self._conn.commit()
            applied = {
                int(r["version"])
                for r in cur.execute("SELECT version FROM schema_migrations")
            }
            for ver in sorted(MIGRATIONS):
                if ver in applied:
                    continue
                for sql in MIGRATIONS[ver]:
                    cur.execute(sql)
                cur.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (ver, time.time()),
                )
                self._conn.commit()
            return self.schema_version()

    def schema_version(self) -> int:
        with self._lock:
            row = self._conn.execute(
                "SELECT MAX(version) AS v FROM schema_migrations"
            ).fetchone()
            return int(row["v"] or 0) if row else 0

    def execute(self, sql: str, params: Sequence[Any] | Dict[str, Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cur = self._conn.execute(sql, params)
            self._conn.commit()
            return cur

    def query(self, sql: str, params: Sequence[Any] = ()) -> List[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, params).fetchall())

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def info(self) -> DbInfo:
        row = self._conn.execute("PRAGMA journal_mode").fetchone()
        mode = str(row[0]) if row else "unknown"
        size = Path(self.path).stat().st_size if self.path != ":memory:" and Path(self.path).exists() else 0
        return DbInfo(
            path=self.path,
            journal_mode=mode,
            schema_version=self.schema_version(),
            size_bytes=size,
        )

    def backup(self, dest: str | Path) -> Path:
        """5.3/5.8 在线备份到 dest。"""
        dest_path = Path(dest)
        ensure_parent(dest_path)
        if dest_path.exists():
            dest_path.unlink()
        with self._lock:
            tgt = sqlite3.connect(str(dest_path))
            try:
                self._conn.backup(tgt)
            finally:
                tgt.close()
        return dest_path


def backup_db(src: str | Path, dest: str | Path) -> Path:
    """独立备份入口（5.3）。"""
    src_path = Path(src)
    if not src_path.exists():
        raise FileNotFoundError(f"数据库不存在: {src_path}")
    dest_path = Path(dest)
    ensure_parent(dest_path)
    # 优先在线 backup API；失败则文件复制
    try:
        db = Database(":memory:")
        # 用源库连接做 backup
        conn = sqlite3.connect(str(src_path))
        try:
            tgt = sqlite3.connect(str(dest_path))
            try:
                conn.backup(tgt)
            finally:
                tgt.close()
        finally:
            conn.close()
        db.close()
        return dest_path
    except sqlite3.Error:
        shutil.copy2(src_path, dest_path)
        return dest_path


def restore_db(src: str | Path, dest: str | Path) -> Path:
    """5.8 从备份恢复（覆盖 dest）。"""
    src_path, dest_path = Path(src), Path(dest)
    if not src_path.exists():
        raise FileNotFoundError(f"备份不存在: {src_path}")
    ensure_parent(dest_path)
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(dest_path) + suffix)
        if p.exists():
            p.unlink()
    shutil.copy2(src_path, dest_path)
    return dest_path
