#!/usr/bin/env python3
"""一键全量测试：Python unittest + Node JS 测试 + Rust cargo test。

用法：
  python scripts/test_all.py
  python scripts/test_all.py --skip-rust
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = os.environ.get("LOOM_PYTHON") or sys.executable
NODE = os.environ.get("MIMO_NODE") or "node"
CARGO = os.environ.get("CARGO") or r"C:\Users\qqqq\.cargo\bin\cargo.exe"
if not Path(CARGO).exists():
    CARGO = "cargo"


def run(title: str, cmd: list[str], cwd: Path, env: dict | None = None) -> int:
    print(f"\n=== {title} ===", flush=True)
    e = os.environ.copy()
    if env:
        e.update(env)
    # Node 测试需要共享 react
    node_modules = os.environ.get("MIMO_NODE_MODULES", "")
    if node_modules:
        e["NODE_PATH"] = node_modules
    r = subprocess.run(cmd, cwd=str(cwd), env=e)
    print(f"--- {title}: {'PASS' if r.returncode == 0 else 'FAIL'} ---", flush=True)
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-rust", action="store_true")
    ap.add_argument("--skip-js", action="store_true")
    args = ap.parse_args()
    failures = 0

    # Python（pytest 优先，回退 unittest）
    pytest_ok = False
    try:
        import importlib.util as _ilu
        pytest_ok = _ilu.find_spec("pytest") is not None
    except Exception:
        pytest_ok = False
    if pytest_ok:
        failures += run("Python pytest", [PY, "-m", "pytest"], ROOT)
    else:
        failures += run(
            "Python unittest",
            [PY, "-m", "unittest", "discover", "-s", "tests"],
            ROOT,
        )

    # Node / JS
    if not args.skip_js:
        js_tests = sorted((ROOT / "tests" / "js").glob("test_*.mjs"))
        # 在线/live 测试默认跳过（无密钥时自动 skip）
        for p in js_tests:
            failures += run(
                f"JS {p.name}",
                [NODE, "--experimental-strip-types", str(p.relative_to(ROOT))],
                ROOT,
            )

    # Rust
    if not args.skip_rust:
        tauri = ROOT / "apps/desktop/src-tauri"
        if (tauri / "Cargo.toml").exists():
            failures += run("Rust cargo test", [CARGO, "test"], tauri)

    print("\n========== SUMMARY ==========")
    if failures == 0:
        print("ALL PASS (Python + JS + Rust)")
        return 0
    print(f"FAILED suites: {failures}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
