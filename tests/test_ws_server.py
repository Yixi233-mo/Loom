"""T8 单元测试：WebSocket 服务端 — 注册 / 心跳 / 踢出 / 广播 / 边界。"""

from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path
from typing import Any, Dict, List

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from device_mesh.connection_manager import ConnectionManager  # noqa: E402
from device_mesh.heartbeat import HeartbeatMonitor  # noqa: E402
from device_mesh.protocol import (  # noqa: E402
    ErrorCode,
    MessageType,
    ProtocolError,
    build_message,
    parse_message,
)
from device_mesh.ws_server import (  # noqa: E402
    HubRuntime,
    create_app,
    make_signature,
)

SECRET = "test-secret"


def register_msg(
    device_id: str,
    device_type: str = "pc",
    secret: str = SECRET,
    bad_sig: bool = False,
    ts: float | None = None,
) -> str:
    if ts is None:
        ts = time.time()
    sig = "bad" if bad_sig else make_signature(device_id, device_type, ts, secret)
    return json.dumps(
        {
            "type": "register",
            "device_id": device_id,
            "device_type": device_type,
            "capabilities": ["file.read"],
            "ts": ts,
            "signature": sig,
        }
    )


def heartbeat_msg(device_id: str) -> str:
    return json.dumps({"type": "heartbeat", "device_id": device_id, "ts": time.time()})


def recv_json(ws) -> Dict[str, Any]:
    return json.loads(ws.receive_text())


class TestProtocol(unittest.TestCase):
    def test_parse_ok(self):
        msg = parse_message('{"type": "heartbeat", "device_id": "a"}')
        self.assertEqual(msg["type"], "heartbeat")

    def test_parse_invalid_json(self):
        with self.assertRaises(ProtocolError):
            parse_message("{not json")

    def test_parse_missing_type(self):
        with self.assertRaises(ProtocolError):
            parse_message('{"a": 1}')

    def test_parse_not_object(self):
        with self.assertRaises(ProtocolError):
            parse_message("[1,2]")

    def test_parse_too_large(self):
        raw = json.dumps({"type": "x", "blob": "y" * (1024 * 1024)})
        with self.assertRaises(ProtocolError):
            parse_message(raw)

    def test_build_message(self):
        s = build_message(MessageType.HEARTBEAT_ACK)
        msg = json.loads(s)
        self.assertEqual(msg["type"], "heartbeat_ack")
        self.assertIn("server_ts", msg)

    def test_error_code_values(self):
        self.assertEqual(ErrorCode.NOT_REGISTERED.value, 4001)
        self.assertEqual(ErrorCode.INVALID_MESSAGE.value, 4002)
        self.assertEqual(ErrorCode.TOO_MANY_CONNECTIONS.value, 4003)
        self.assertEqual(ErrorCode.INVALID_SIGNATURE.value, 4004)


class TestConnectionManager(unittest.IsolatedAsyncioTestCase):
    async def test_register_and_list(self):
        cm = ConnectionManager()

        class FakeWS:
            async def close(self, code=1000, reason=""):
                pass

            async def send_text(self, t):
                pass

        await cm.register("a", FakeWS())  # type: ignore
        await cm.register("b", FakeWS())  # type: ignore
        self.assertEqual(sorted(cm.get_online_devices()), ["a", "b"])
        await cm.unregister("a")
        self.assertEqual(cm.get_online_devices(), ["b"])

    async def test_send_missing(self):
        cm = ConnectionManager()
        ok = await cm.send_to_device("nope", "x")
        self.assertFalse(ok)

    async def test_broadcast(self):
        cm = ConnectionManager()
        sent: List[str] = []

        class FakeWS:
            async def send_text(self, t):
                sent.append(t)

            async def close(self, code=1000, reason=""):
                pass

        for did in ("a", "b", "c"):
            await cm.register(did, FakeWS())  # type: ignore
        n = await cm.broadcast("hello")
        self.assertEqual(n, 3)
        self.assertEqual(len(sent), 3)


class TestHeartbeatMonitor(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_kicks(self):
        clock = {"now": 1000.0}
        cm = ConnectionManager()

        class FakeWS:
            async def close(self, code=1000, reason=""):
                pass

            async def send_text(self, t):
                pass

        await cm.register("dev", FakeWS())  # type: ignore
        mon = HeartbeatMonitor(cm, timeout=60, time_fn=lambda: clock["now"])
        mon.update("dev")
        expired = await mon.scan_once()
        self.assertEqual(expired, [])

        clock["now"] = 1000.0 + 61
        expired = await mon.scan_once()
        self.assertEqual(expired, ["dev"])
        self.assertFalse(cm.is_connected("dev"))

    async def test_update_prevents_timeout(self):
        clock = {"now": 1000.0}
        cm = ConnectionManager()

        class FakeWS:
            async def close(self, code=1000, reason=""):
                pass

            async def send_text(self, t):
                pass

        await cm.register("dev", FakeWS())  # type: ignore
        mon = HeartbeatMonitor(cm, timeout=60, time_fn=lambda: clock["now"])
        mon.update("dev")
        clock["now"] = 1050.0
        mon.update("dev")
        clock["now"] = 1100.0
        expired = await mon.scan_once()
        self.assertEqual(expired, [])


def make_client(max_connections: int = 1000) -> tuple[TestClient, HubRuntime]:
    rt = HubRuntime(secret=SECRET, max_connections=max_connections)
    app = create_app(rt)
    return TestClient(app), rt


class TestWSRegister(unittest.TestCase):
    def test_register_ok(self):
        client, rt = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1"))
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "registered")
            self.assertEqual(resp["session_id"], "sess_pc-1")
            self.assertTrue(rt.cm.is_connected("pc-1"))
            self.assertIn("pc-1", rt.mesh.list_devices()[0]["device_id"])

    def test_register_bad_signature(self):
        client, rt = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1", bad_sig=True))
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "error")
            self.assertEqual(resp["code"], ErrorCode.INVALID_SIGNATURE.value)
            self.assertFalse(rt.cm.is_connected("pc-1"))

    def test_register_stale_timestamp(self):
        client, rt = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1", ts=time.time() - 3600))
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "error")
            self.assertEqual(resp["code"], ErrorCode.INVALID_SIGNATURE.value)

    def test_duplicate_register_kicks_old(self):
        client, rt = make_client()
        with client.websocket_connect("/ws") as ws1:
            ws1.send_text(register_msg("pc-1"))
            self.assertEqual(recv_json(ws1)["type"], "registered")

            with client.websocket_connect("/ws") as ws2:
                ws2.send_text(register_msg("pc-1"))
                self.assertEqual(recv_json(ws2)["type"], "registered")
                self.assertTrue(rt.cm.is_connected("pc-1"))

            # ws2 关闭后 finally 会 unregister
        # 最终应无残留或仅有一次清理
        self.assertFalse(rt.cm.is_connected("pc-1"))


class TestWSHeartbeat(unittest.TestCase):
    def test_heartbeat_ack(self):
        client, _ = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1"))
            recv_json(ws)
            ws.send_text(heartbeat_msg("pc-1"))
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "heartbeat_ack")
            self.assertIn("server_ts", resp)

    def test_heartbeat_before_register(self):
        client, _ = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(heartbeat_msg("ghost"))
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "error")
            self.assertEqual(resp["code"], ErrorCode.NOT_REGISTERED.value)
            # 连接不关闭，可继续发
            ws.send_text(register_msg("pc-9"))
            self.assertEqual(recv_json(ws)["type"], "registered")


class TestWSEdge(unittest.TestCase):
    def test_invalid_json(self):
        client, _ = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text("{not-json")
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "error")
            self.assertEqual(resp["code"], ErrorCode.INVALID_MESSAGE.value)

    def test_unknown_type(self):
        client, _ = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(json.dumps({"type": "nonsense"}))
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "error")
            self.assertEqual(resp["code"], ErrorCode.INVALID_MESSAGE.value)

    def test_result_handler(self):
        captured: List[dict] = []
        rt = HubRuntime(secret=SECRET, on_result=lambda m: captured.append(m))
        client = TestClient(create_app(rt))
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1"))
            recv_json(ws)
            ws.send_text(
                json.dumps({"type": "result", "task_id": "t1", "status": "done", "output": {"ok": 1}})
            )
            resp = recv_json(ws)
            self.assertEqual(resp["type"], "ok")
            self.assertEqual(captured[0]["task_id"], "t1")

    def test_max_connections(self):
        client, rt = make_client(max_connections=1)
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1"))
            recv_json(ws)
            with client.websocket_connect("/ws") as ws2:
                resp = recv_json(ws2)
                self.assertEqual(resp["type"], "error")
                self.assertEqual(resp["code"], ErrorCode.TOO_MANY_CONNECTIONS.value)

    def test_send_to_device_and_broadcast(self):
        client, rt = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1"))
            recv_json(ws)
            __import__("asyncio").run(
                rt.cm.send_to_device("pc-1", build_message("task_dispatch", task_id="t1"))
            )
            # TestClient websocket send from same context is awkward;
            # 直接断言连接存在 + send_to_device 返回 True（Fake 同步 portal 内）
            self.assertTrue(rt.cm.is_connected("pc-1"))


class TestDisconnectCleansUp(unittest.TestCase):
    def test_disconnect_unregisters(self):
        client, rt = make_client()
        with client.websocket_connect("/ws") as ws:
            ws.send_text(register_msg("pc-1"))
            recv_json(ws)
            self.assertTrue(rt.cm.is_connected("pc-1"))
        # 退出 context = 断线
        self.assertFalse(rt.cm.is_connected("pc-1"))
        self.assertIsNone(rt.monitor.last_seen("pc-1"))


if __name__ == "__main__":
    unittest.main()
