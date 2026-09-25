#!/usr/bin/env python3
"""3.8 版本号单一来源校验：package / Cargo / pyproject / tauri.conf。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def versions() -> dict[str, str]:
    out: dict[str, str] = {}
    pkg = ROOT / "package.json"
    if pkg.exists():
        out["package.json"] = str(json.loads(pkg.read_text(encoding="utf-8")).get("version", ""))
    for rel, pat in (
        ("src-tauri/Cargo.toml", r'version\s*=\s*"([^"]+)"'),
        ("pyproject.toml", r'version\s*=\s*"([^"]+)"'),
        ("src-tauri/tauri.conf.json", r'"version"\s*:\s*"([^"]+)"'),
    ):
        p = ROOT / rel
        if p.exists():
            m = re.search(pat, p.read_text(encoding="utf-8", errors="ignore"))
            out[rel] = m.group(1) if m else ""
    return out


def main() -> int:
    vs = versions()
    print("versions:", vs)
    vals = {v for v in vs.values() if v}
    if len(vals) != 1:
        print("FAIL: 版本不一致", vs)
        return 1
    print("OK: 版本一致", vals.pop())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
