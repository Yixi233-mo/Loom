"""N2 联调测试：页面触发 → 后端执行 → 收结果（真 WS 协议）。"""

from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from device_mesh.ws_server import make_signature as sign  # noqa: E402
from integration.ws_app import create_integrated_app  # noqa: E402
from scripts.run_hub_server import build_demo_stack  # noqa: E402

SECRET = "dev-secret"


def register_msg(device_id: str, device_type: str) -> str:
    ts = time.time()
    return json.dumps(
        {
            "type": "register",
            "device_id": device_id,
            "device_type": device_type,
            "capabilities": ["notifications"],
            "ts": ts,
            "signature": sign(device_id, device_type, ts, SECRET),
        }
    )


def recv_json(ws):
    return json.loads(ws.receive_text())


def recv_until(ws, types: set, max_reads: int = 20):
    """读到任一指定 type 为止，返回 (msg, seen_list)。"""
    seen = []
    last = None
    for _ in range(max_reads):
        last = recv_json(ws)
        seen.append(last)
        if last.get("type") in types:
            return last, seen
    raise AssertionError(f"未读到 {types}，已见 {[m.get('type') for m in seen]}，最后: {last}")


class TestN2LiveLoop(unittest.TestCase):
    def test_web_trigger_backend_execute_recv_result(self):
        """验收：页面触发任务 → 后端执行 → 页面收到结果。"""
        stack = build_demo_stack()
        app = create_integrated_app(stack)
        client = TestClient(app)

        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("web-shell-1", "tablet"))
            reg = recv_json(ws)
            self.assertEqual(reg["type"], "registered")

            ws.send_text(
                json.dumps(
                    {
                        "type": "trigger",
                        "workflow": {"name": "daily_report", "device": "pc"},
                        "trace_id": "n2-live-1",
                    }
                )
            )

            # 服务端在 trigger 返回前可能已广播结果；两则都要收到
            got_ack = False
            got_result = False
            types = []
            for _ in range(20):
                msg = recv_json(ws)
                types.append(msg["type"])
                if msg["type"] == "trigger_ack":
                    got_ack = True
                    self.assertEqual(msg["trace_id"], "n2-live-1")
                if msg["type"] == "sync_broadcast":
                    data = msg.get("data") or {}
                    blob = json.dumps(data, ensure_ascii=False)
                    if "done" in blob or "n2-live-1" in blob or data.get("task_id"):
                        got_result = True
                if got_ack and got_result:
                    break

            self.assertTrue(got_ack, f"未收到 trigger_ack, types={types}")
            self.assertTrue(got_result, f"未收到结果广播, types={types}")

        tasks = stack.orch.list_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]["status"].value, "done")
        self.assertTrue(any(e.get("stage") == "complete" for e in stack.trace_log))

    def test_one_script_stack_has_notes_and_rag(self):
        stack = build_demo_stack()
        self.assertTrue(stack.tools.get("notes.list"))
        self.assertTrue(stack.agents.get("builtin_rag"))
        self.assertTrue(getattr(stack, "auto_execute", False))
        self.assertEqual(stack.mesh.get("hub-pc-1")["device_type"], "pc")


class TestN2StartScriptFiles(unittest.TestCase):
    def test_start_scripts_exist(self):
        root = ROOT
        self.assertTrue((root / "scripts" / "start.ps1").exists())
        self.assertTrue((root / "scripts" / "run_hub_server.py").exists())
        pkg = json.loads((root / "package.json").read_text(encoding="utf-8"))
        self.assertIn("start", pkg["scripts"])
        self.assertIn("start:hub", pkg["scripts"])

    def test_ws_client_module_exists(self):
        self.assertTrue((ROOT / "src" / "hub" / "ws-client.ts").exists())


if __name__ == "__main__":
    unittest.main()
