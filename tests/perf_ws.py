"""T8.7 性能测试：100 设备并发注册 < 1s。

运行：python tests/perf_ws.py
"""

from __future__ import annotations

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from device_mesh.ws_server import HubRuntime, create_app, make_signature  # noqa: E402

SECRET = "perf-secret"
N = 100


def register_once(i: int) -> bool:
    rt = HubRuntime(secret=SECRET)
    client = TestClient(create_app(rt))
    did = f"dev-{i}"
    ts = time.time()
    payload = {
        "type": "register",
        "device_id": did,
        "device_type": "pc",
        "capabilities": ["file.read"],
        "ts": ts,
        "signature": make_signature(did, "pc", ts, SECRET),
    }
    with client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps(payload))
        resp = json.loads(ws.receive_text())
        return resp.get("type") == "registered"


def main() -> int:
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=50) as ex:
        results = list(ex.map(register_once, range(N)))
    elapsed = time.perf_counter() - start
    ok = sum(1 for r in results if r)
    print(f"并发注册 {ok}/{N} 成功，耗时 {elapsed:.3f}s")
    if elapsed < 1.0 and ok == N:
        print("PASS: 100 设备并发注册 < 1s")
        return 0
    print("FAIL: 超时或存在失败注册")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
