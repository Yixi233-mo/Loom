#!/usr/bin/env python3
"""lint 入口：Python py_compile +（可选）ruff；Rust cargo fmt --check。

用法：
  python scripts/lint_all.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = os.environ.get("LOOM_PYTHON") or sys.executable
CARGO = os.environ.get("CARGO") or r"C:\Users\qqqq\.cargo\bin\cargo.exe"
if not Path(CARGO).exists():
    CARGO = "cargo"


def lint_python() -> int:
    print("\n=== Python lint ===", flush=True)
    errors = 0
    for p in sorted(ROOT.rglob("*.py")):
        s = str(p)
        if "node_modules" in s or "target" in s or "_fix" in s:
            continue
        try:
            # 只做语法编译检查，避免写 __pycache__（CI/只读盘上可能 PermissionError）
            source = Path(p).read_text(encoding="utf-8")
            compile(source, str(p), "exec", dont_inherit=True)
        except SyntaxError as e:
            print(f"SYNTAX FAIL {p}: {e}")
            errors += 1
        except Exception as e:  # noqa: BLE001
            print(f"READ FAIL {p}: {e}")
            errors += 1
    # ruff 可选
    ruff = shutil.which("ruff")
    if ruff:
        r = subprocess.run(
            [ruff, "check", "--config", str(ROOT / "apps/hub/ruff.toml"), "apps", "scripts", "tests"],
            cwd=str(ROOT),
        )
        if r.returncode != 0:
            errors += 1
    else:
        print("(ruff 未安装，已用 py_compile 语法检查；目标栈为 Ruff，可 pip install ruff)")
    print(f"--- Python lint: {'PASS' if errors == 0 else 'FAIL'} ---")
    return errors


def lint_rust() -> int:
    print("\n=== Rust cargo fmt --check ===", flush=True)
    tauri = ROOT / "apps/desktop/src-tauri"
    if not (tauri / "Cargo.toml").exists():
        print("(no Cargo.toml, skip)")
        return 0
    r = subprocess.run([CARGO, "fmt", "--all", "--", "--check"], cwd=str(tauri))
    print(f"--- Rust fmt: {'PASS' if r.returncode == 0 else 'FAIL'} ---")
    return 0 if r.returncode == 0 else 1


def lint_ts() -> int:
    print("\n=== TS/JS 基础检查 ===", flush=True)
    # 无 ESLint 时跳过；检查关键文件存在
    ok = (ROOT / "apps" / "web" / "src" / "shell" / "schema-renderer.impl.ts").exists()
    print(f"--- TS check: {'PASS' if ok else 'FAIL'} ---")
    return 0 if ok else 1


def main() -> int:
    n = lint_python() + lint_rust() + lint_ts()
    print("\n========== LINT SUMMARY ==========")
    if n == 0:
        print("ALL PASS")
        return 0
    print(f"FAILED checks: {n}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
