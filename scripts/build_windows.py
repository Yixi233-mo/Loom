#!/usr/bin/env python3
"""Windows 打包 — 前端 + Tauri，产出 .msi / .nsis 安装包。

用法：
  python scripts/build_windows.py            # msi + nsis
  python scripts/build_windows.py --msi      # 仅 msi
  python scripts/build_windows.py --nsis     # 仅 nsis
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUNDLE = ROOT / "apps/desktop/src-tauri" / "target" / "release" / "bundle"
OUT = ROOT / "dist-bundle"


def run(title: str, cmd: list[str], cwd: Path) -> None:
    print(f"\n=== {title} ===", flush=True)
    r = subprocess.run(cmd, cwd=str(cwd))
    if r.returncode != 0:
        raise SystemExit(f"{title} failed ({r.returncode})")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--msi", action="store_true", help="仅 MSI")
    ap.add_argument("--nsis", action="store_true", help="仅 NSIS")
    args = ap.parse_args()
    bundles = []
    if args.msi or not args.nsis:
        bundles.append("msi")
    if args.nsis or not args.msi:
        bundles.append("nsis")

    npx = "npx.cmd" if os.name == "nt" else "npx"
    run("Tauri build", [npx, "@tauri-apps/cli", "build", "--bundles", ",".join(bundles)], ROOT)

    OUT.mkdir(exist_ok=True)
    copied = []
    for pat in ("**/*.msi", "**/*.exe"):
        for p in BUNDLE.glob(pat):
            if "setup" in p.name.lower() or p.suffix == ".msi":
                dest = OUT / p.name
                shutil.copy2(p, dest)
                copied.append(dest)

    print("\n=== 产物 ===")
    for p in copied:
        print(f"  {p}  ({p.stat().st_size / 1024 / 1024:.2f} MB)")
    if not copied:
        print("  (无)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
