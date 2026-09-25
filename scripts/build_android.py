#!/usr/bin/env python3
"""Android APK 打包 — Tauri 2 + Gradle（Windows 可用）。

前置：
  - JAVA_HOME（JDK 17+）
  - ANDROID_HOME / ANDROID_SDK_ROOT（含 NDK）
  - rustup target add aarch64-linux-android

用法：
  python scripts/build_android.py            # arm64 debug APK
  python scripts/build_android.py --release  # release（需 keystore.properties）
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GEN = ROOT / "src-tauri" / "gen" / "android"
OUT = ROOT / "dist-bundle"
NATIVE = ROOT / "src-tauri" / "target" / "aarch64-linux-android"


def run(title: str, cmd: list[str], cwd: Path, env: dict | None = None) -> None:
    print(f"\n=== {title} ===", flush=True)
    e = os.environ.copy()
    if env:
        e.update(env)
    r = subprocess.run(cmd, cwd=str(cwd), env=e)
    if r.returncode != 0:
        raise SystemExit(f"{title} failed ({r.returncode})")


def copy_so(profile: str) -> Path:
    """Windows 无符号链接权限时用复制代替 symlink。"""
    so = (NATIVE / profile / "libloom_shell.so").resolve()
    if not so.exists():
        raise SystemExit(f"missing {so} — 先编 Rust：cargo build --target aarch64-linux-android --lib")
    dst_dir = (GEN / "app" / "src" / "main" / "jniLibs" / "arm64-v8a").resolve()
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / "libloom_shell.so"
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    shutil.copy2(so, dst)
    print("copied", so, "->", dst, dst.stat().st_size, "bytes")
    return dst


def copy_frontend_assets() -> None:
    """把 vite dist/ 同步到 app/src/main/assets/（Tauri asset loader）。

    缺失会导致 WebView 无页面，原生层闪退。
    """
    dist = ROOT / "dist"
    assets = GEN / "app" / "src" / "main" / "assets"
    if not (dist / "index.html").exists():
        raise SystemExit(f"missing {dist}/index.html — 先 npm run build")
    if assets.exists():
        shutil.rmtree(assets)
    shutil.copytree(dist, assets)
    n = sum(1 for p in assets.rglob("*") if p.is_file())
    print(f"copied frontend assets: {n} files -> {assets}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--release", action="store_true")
    args = ap.parse_args()
    profile = "release" if args.release else "debug"
    task = "assembleArm64Release" if args.release else "assembleArm64Debug"
    skip = f"rustBuildArm64{'Release' if args.release else 'Debug'}"

    run(
        "Rust aarch64",
        [
            "cargo",
            "build",
            "--package",
            "loom_shell",
            "--manifest-path",
            str(ROOT / "src-tauri" / "Cargo.toml"),
            "--target",
            "aarch64-linux-android",
            "--lib",
        ]
        + (["--release"] if args.release else []),
        ROOT / "src-tauri",
    )

    npm = "npm.cmd" if os.name == "nt" else "npm"
    run("Vite build", [npm, "run", "build"], ROOT)

    # 关键：前端必须进 assets，否则真机闪退
    copy_frontend_assets()
    copy_so(profile)

    run(
        f"Gradle {task}",
        [str(GEN / "gradlew.bat"), task, "-x", skip, "--no-daemon"],
        GEN,
    )

    OUT.mkdir(exist_ok=True)
    copied = []
    for p in (GEN / "app" / "build" / "outputs" / "apk").rglob("*.apk"):
        dest = OUT / p.name
        shutil.copy2(p, dest)
        copied.append(dest)
    print("\n=== 产物 ===")
    for p in copied:
        print(f"  {p}  ({p.stat().st_size / 1024 / 1024:.2f} MB)")
    return 0 if copied else 1


if __name__ == "__main__":
    raise SystemExit(main())
