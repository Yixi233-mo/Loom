"""INT 集成测试：Hub↔Orchestrator / Sync→WS / 真链路 E2E。"""

from __future__ import annotations

import asyncio
import json
import sys
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from device_mesh.ws_server import make_signature as sign
from integration.hub_bridge import build_integrated_hub_graph
from integration.stack import HubStack
from integration.ws_app import create_integrated_app
from plugins.example.notes_runtime import NotesStore, make_notes_tools

SECRET = "itest-secret"


def make_stack() -> HubStack:
    store = NotesStore()
    store.create("样例", "内容")
    tools = make_notes_tools(store)

    def builtin_rag(prompt: str):
        return {"summary": f"RAG:{prompt[:30]}"}

    return HubStack(tools=tools, agents={"builtin_rag": builtin_rag}, secret=SECRET)


def register_msg(device_id: str, device_type: str) -> str:
    ts = time.time()
    return json.dumps(
        {
            "type": "register",
            "device_id": device_id,
            "device_type": device_type,
            "capabilities": ["file.read"],
            "ts": ts,
            "signature": sign(device_id, device_type, ts, SECRET),
        }
    )


def recv_json(ws):
    return json.loads(ws.receive_text())


def recv_until(ws, msg_type: str, max_reads: int = 10):
    """读到指定 type 为止（跳过 sync_broadcast 等广播）。"""
    last = None
    for _ in range(max_reads):
        last = recv_json(ws)
        if last.get("type") == msg_type:
            return last
    raise AssertionError(f"未读到 {msg_type}，最后消息: {last}")


class FakeWS:
    def __init__(self):
        self.sent = []

    async def send_text(self, t):
        self.sent.append(t)

    async def close(self, code=1000, reason=""):
        pass

    def types(self):
        return [json.loads(t).get("type") for t in self.sent]


class TestHubToOrchestrator(unittest.TestCase):
    """INT.1 — Hub workflow 路径接入 TaskOrchestrator。"""

    def test_submit_workflow_assigns_and_records(self):
        stack = make_stack()
        stack.mesh.register("pc-1", "pc", ["shell.exec"])
        task_id = stack.submit_workflow({"name": "daily_report", "device": "pc"})
        record = stack.orch.get(task_id)
        self.assertEqual(record["assigned_to"], "pc-1")
        self.assertIn(record["status"].value, {"assigned", "running"})
        self.assertTrue(any(e["stage"] == "submit" for e in stack.trace_log))

    def test_integrated_graph_workflow_sets_task_id(self):
        stack = make_stack()
        stack.mesh.register("pc-1", "pc", ["shell.exec"])
        graph = build_integrated_hub_graph(stack)
        out = asyncio.run(graph.ainvoke({"user_input": "执行工作流 weekly_report"}))
        self.assertEqual(out["intent"], "workflow")
        self.assertTrue(out.get("task_id"))
        self.assertIn("workflow:", out.get("result", ""))
        record = stack.orch.get(out["task_id"])
        self.assertIn(
            record["status"].value, {"assigned", "running", "done", "failed"}
        )

    def test_agent_path_still_works(self):
        stack = make_stack()
        graph = build_integrated_hub_graph(stack)
        out = asyncio.run(graph.ainvoke({"user_input": "审查代码"}))
        self.assertEqual(out["agent"], "claude_code")


class TestSyncToWsBroadcast(unittest.TestCase):
    """INT.3 — SyncEngine 变更 → sync_broadcast；任务下发 → task_dispatch。"""

    def test_sync_put_broadcasts_to_connected(self):
        stack = make_stack()
        ws = FakeWS()
        asyncio.run(stack.cm.register("tablet-1", ws))
        asyncio.run(stack.sync.put(key="k1", value={"v": 1}, device_id="pc-1"))

        self.assertTrue(len(ws.sent) >= 1)
        msg = json.loads(ws.sent[-1])
        self.assertEqual(msg["type"], "sync_broadcast")
        self.assertIn("event", msg)
        self.assertEqual(msg["data"]["key"], "k1")

    def test_complete_task_broadcasts_result(self):
        stack = make_stack()
        pc = FakeWS()
        tablet = FakeWS()
        asyncio.run(stack.cm.register("pc-1", pc))
        asyncio.run(stack.cm.register("tablet-1", tablet))
        stack.mesh.register("pc-1", "pc", ["shell.exec"])

        task_id = stack.submit_workflow({"name": "t", "device": "pc"}, trace_id="tr-1")
        # submit 同步包装会 dispatch 到 pc
        self.assertIn("task_dispatch", pc.types())

        stack.complete_task(task_id, "done", {"ok": 1}, trace_id="tr-1")
        self.assertIn("sync_broadcast", tablet.types())
        self.assertIn("sync_broadcast", pc.types())


class TestWebSocketRealE2E(unittest.TestCase):
    """INT.2 — WebSocket 真链路：手机触发 → PC 下发 → 回写 → Sync 可查。"""

    def test_mobile_trigger_pc_dispatch_tablet_broadcast(self):
        stack = make_stack()
        app = create_integrated_app(stack)
        client = TestClient(app)

        with client.websocket_connect("/ws") as mobile:
            mobile.send_text(register_msg("mobile-1", "mobile"))
            self.assertEqual(recv_json(mobile)["type"], "registered")

            with client.websocket_connect("/ws") as pc:
                pc.send_text(register_msg("pc-1", "pc"))
                self.assertEqual(recv_json(pc)["type"], "registered")

                mobile.send_text(
                    json.dumps(
                        {
                            "type": "trigger",
                            "workflow": {"name": "mobile_to_pc_pdf", "device": "pc"},
                            "trace_id": "e2e-ws-1",
                        }
                    )
                )
                ack = recv_until(mobile, "trigger_ack")
                self.assertEqual(ack["assigned_to"], "pc-1")
                self.assertEqual(ack["trace_id"], "e2e-ws-1")
                self.assertEqual(ack["status"], "running")
                task_id = ack["task_id"]

                dispatch = recv_until(pc, "task_dispatch")
                self.assertEqual(dispatch["task_id"], task_id)
                self.assertEqual(dispatch["trace_id"], "e2e-ws-1")

                pc.send_text(
                    json.dumps(
                        {
                            "type": "result",
                            "task_id": task_id,
                            "status": "done",
                            "output": {"steps": {"extract": {"ok": True}}},
                            "trace_id": "e2e-ws-1",
                        }
                    )
                )
                recv_until(pc, "ok")

        record = stack.orch.get(task_id)
        self.assertEqual(record["status"].value, "done")

        changes = stack.sync.changes(since_version=0)
        self.assertTrue(any("e2e-ws-1" in str(c.get("value")) for c in changes))
        self.assertTrue(any(task_id in str(c.get("value")) for c in changes))

    def test_tablet_receives_sync_broadcast_when_online(self):
        stack = make_stack()
        pc = FakeWS()
        tablet = FakeWS()
        asyncio.run(stack.cm.register("pc-1", pc))
        asyncio.run(stack.cm.register("tablet-1", tablet))
        stack.mesh.register("pc-1", "pc", ["shell.exec"])

        task_id = stack.submit_workflow({"name": "t", "device": "pc"}, trace_id="tr-b")
        stack.complete_task(task_id, "done", {"ok": True}, trace_id="tr-b")

        self.assertIn("task_dispatch", pc.types())
        self.assertIn("sync_broadcast", tablet.types())
        self.assertIn("sync_broadcast", pc.types())

    def test_trigger_queues_when_pc_offline(self):
        stack = make_stack()
        app = create_integrated_app(stack)
        client = TestClient(app)

        with client.websocket_connect("/ws") as mobile:
            mobile.send_text(register_msg("mobile-1", "mobile"))
            recv_json(mobile)
            mobile.send_text(
                json.dumps(
                    {
                        "type": "trigger",
                        "workflow": {"name": "x", "device": "pc"},
                        "trace_id": "tr-q",
                    }
                )
            )
            ack = recv_until(mobile, "trigger_ack")
            self.assertEqual(ack["status"], "pending")

        with client.websocket_connect("/ws") as pc:
            pc.send_text(register_msg("pc-1", "pc"))
            recv_json(pc)
            dispatched = stack.dispatch_pending()
            self.assertTrue(dispatched)
            msg = recv_until(pc, "task_dispatch")
            self.assertIn("task_id", msg)


if __name__ == "__main__":
    unittest.main()
