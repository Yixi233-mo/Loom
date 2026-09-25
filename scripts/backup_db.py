#!/usr/bin/env python3
"""备份 Loom SQLite 数据库（N16 5.3）。

用法：
  python scripts/backup_db.py
  python scripts/backup_db.py --db data/loom.db --out backups/loom-2026-09-25.db
  python scripts/backup_db.py --restore backups/xxx.db --db data/loom.db
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from data import backup_db, resolve_db_path, restore_db


def main() -> int:
    ap = argparse.ArgumentParser(description="Loom 数据库备份/恢复")
    ap.add_argument("--db", default="", help="源数据库路径（默认 LOOM_DB_PATH / data/loom.db）")
    ap.add_argument("--out", default="", help="备份输出路径")
    ap.add_argument("--restore", default="", help="从备份文件恢复到 --db")
    args = ap.parse_args()

    db_path = Path(args.db) if args.db else resolve_db_path(ROOT)

    if args.restore:
        dest = restore_db(args.restore, db_path)
        print(f"restored {args.restore} -> {dest}")
        return 0

    ts = time.strftime("%Y%m%d-%H%M%S")
    out = Path(args.out) if args.out else (ROOT / "backups" / f"loom-{ts}.db")
    path = backup_db(db_path, out)
    print(f"backed up {db_path} -> {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
