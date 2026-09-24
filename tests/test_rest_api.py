"""N-API / N6 测试：REST /api/* + 调度器接线。"""

from __future__ import annotations

import json
import sys
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.routes import create_api_router, ApiStore  # noqa: E402
from integration.ws_app import create_integrated_app  # noqa: E402
from scripts.run_hub_server import build_demo_stack  # noqa: E402


class TestRestApi(unittest.TestCase):
    def setUp(self):
        self.stack = build_demo_stack()
        self.app = create_integrated_app(self.stack)
        self.app.include_router(create_api_router(self.stack))
        self.client = TestClient(self.app)

    def test_sessions_crud(self):
        r = self.client.get("/api/sessions")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(s["sessionId"] == "sess-demo-1" for s in r.json()))

        r2 = self.client.post("/api/sessions", json={"title": "新"})
        self.assertEqual(r2.status_code, 200)
        sid = r2.json()["sessionId"]

        r3 = self.client.post(
            f"/api/sessions/{sid}/messages",
            json={"role": "user", "content": "你好"},
        )
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.json()["content"], "你好")

        r4 = self.client.get(f"/api/sessions/{sid}")
        self.assertEqual(len(r4.json()["messages"]), 1)

    def test_tasks_trigger_and_list(self):
        r = self.client.post(
            "/api/tasks/trigger",
            json={"workflowName": "daily_report", "device": "pc", "traceId": "api-tr-1"},
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("taskId", body)
        self.assertEqual(body["status"], "done")
        self.assertEqual(body["traceId"], "api-tr-1")

        r2 = self.client.get("/api/tasks")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(len(r2.json()), 1)
        self.assertEqual(r2.json()[0]["taskId"], body["taskId"])

        r3 = self.client.get(f"/api/tasks/{body['taskId']}")
        self.assertEqual(r3.json()["status"], "done")

    def test_agents_list(self):
        r = self.client.get("/api/agents")
        self.assertEqual(r.status_code, 200)
        names = {a["agentName"] for a in r.json()}
        self.assertIn("builtin_rag", names)

    def test_files_upload_delete(self):
        r = self.client.post(
            "/api/files/upload",
            json={"name": "a.pdf", "mime": "application/pdf", "size": 10},
        )
        self.assertEqual(r.status_code, 200)
        fid = r.json()["fileId"]
        self.assertTrue(r.json()["uri"].startswith("hub://files/"))

        r2 = self.client.get("/api/files")
        self.assertEqual(len(r2.json()), 1)

        r3 = self.client.delete(f"/api/files/{fid}")
        self.assertTrue(r3.json()["ok"])
        self.assertEqual(self.client.get("/api/files").json(), [])

    def test_stream_info(self):
        r = self.client.get("/api/stream")
        self.assertEqual(r.json()["ok"], True)


if __name__ == "__main__":
    unittest.main()
