"""知识库 — 存储 / 检索 / API / builtin_rag 接线。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from api.knowledge_routes import create_knowledge_router  # noqa: E402
from knowledge.store import KnowledgeStore, answer_from_kb  # noqa: E402


class TestKnowledgeStore(unittest.TestCase):
    def setUp(self):
        self.store = KnowledgeStore(ROOT / "apps" / "hub" / "plugins" / "_test_kb.json")
        self.store.docs.clear()
        self.store.save()

    def tearDown(self):
        try:
            (ROOT / "apps" / "hub" / "plugins" / "_test_kb.json").unlink(missing_ok=True)
        except TypeError:
            p = ROOT / "apps" / "hub" / "plugins" / "_test_kb.json"
            if p.exists():
                p.unlink()

    def test_add_search_remove(self):
        d = self.store.add("部署流程", "使用 docker compose up hub 启动", ["运维"], kb="builtin")
        hits = self.store.search("怎么部署")
        self.assertTrue(hits)
        self.assertEqual(hits[0].doc.id, d.id)
        self.assertTrue(self.store.remove(d.id))
        self.assertFalse(self.store.search("部署"))

    def test_multi_kb(self):
        self.store.ensure_kb("产品文档", "产品文档")
        self.store.add("A", "苹果手机", kb="builtin")
        self.store.add("B", "苹果手机", kb="产品文档")
        hits_b = self.store.search("苹果", kb="产品文档")
        self.assertEqual(len(hits_b), 1)
        self.assertEqual(hits_b[0].doc.kb, "产品文档")

    def test_answer_from_kb_with_citations(self):
        self.store.add("Loom 启动", "npm run start 启动 Hub 与前端", ["入门"])
        out = answer_from_kb(self.store, "怎么启动")
        self.assertIn("知识库", out["summary"] + "x")
        self.assertTrue(out["hits"])
        self.assertTrue(out["citations"])


class TestKnowledgeApi(unittest.TestCase):
    def setUp(self):
        self.store = KnowledgeStore(ROOT / "apps" / "hub" / "plugins" / "_test_kb_api.json")
        self.store.docs.clear()
        self.store.save()
        self.sources_path = ROOT / "apps" / "hub" / "plugins" / "_test_kb_sources.json"
        if self.sources_path.exists():
            self.sources_path.unlink()
        self.app = FastAPI()
        self.app.include_router(
            create_knowledge_router(self.store, sources_path=str(self.sources_path))
        )
        self.client = TestClient(self.app)

    def tearDown(self):
        p = ROOT / "apps" / "hub" / "plugins" / "_test_kb_api.json"
        if p.exists():
            p.unlink()
        if self.sources_path.exists():
            self.sources_path.unlink()

    def test_api_crud_and_search(self):
        r = self.client.post(
            "/api/knowledge/docs",
            json={"title": "启动", "content": "npm run start", "tags": ["入门"], "kb": "builtin"},
        )
        self.assertEqual(r.status_code, 200)
        doc_id = r.json()["item"]["id"]

        r2 = self.client.get("/api/knowledge/docs")
        self.assertEqual(len(r2.json()["items"]), 1)

        r3 = self.client.post("/api/knowledge/search", json={"query": "启动"})
        self.assertEqual(len(r3.json()["hits"]), 1)

        r4 = self.client.delete(f"/api/knowledge/docs/{doc_id}")
        self.assertTrue(r4.json()["ok"])
        r5 = self.client.get("/api/knowledge/docs")
        self.assertEqual(len(r5.json()["items"]), 0)

    def test_create_kb(self):
        r = self.client.post("/api/knowledge/kbs", json={"id": "产品文档", "name": "产品"})
        self.assertEqual(r.status_code, 200)
        ids = [k["id"] for k in r.json()["items"]]
        self.assertIn("产品文档", ids)

    def test_sources_crud_and_federated_hit(self):
        # 添加 vector 外部源（哈希演示，共享 store）
        r = self.client.post(
            "/api/knowledge/sources",
            json={"id": "vec-demo", "kind": "vector", "name": "向量演示"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["item"]["id"], "vec-demo")

        listed = self.client.get("/api/knowledge/sources").json()["items"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["kind"], "vector")
        self.assertTrue(listed[0].get("health"))

        # 测试连通
        t = self.client.post(
            "/api/knowledge/sources/test",
            json={"id": "vec-demo", "kind": "vector"},
        )
        self.assertEqual(t.status_code, 200)
        self.assertTrue(t.json()["ok"])

        # 写入本地知识 → 联邦检索可命中（local + vector）
        self.client.post(
            "/api/knowledge/docs",
            json={"title": "部署流程", "content": "docker compose up hub", "tags": ["运维"]},
        )
        fed = self.client.post(
            "/api/knowledge/federated/search", json={"query": "怎么部署"}
        )
        self.assertEqual(fed.status_code, 200)
        body = fed.json()
        self.assertTrue(body["hits"])
        self.assertTrue(body["citations"])

        # 删除外部源
        d = self.client.delete("/api/knowledge/sources/vec-demo")
        self.assertTrue(d.json()["ok"])
        self.assertEqual(self.client.get("/api/knowledge/sources").json()["items"], [])

        missing = self.client.delete("/api/knowledge/sources/vec-demo")
        self.assertEqual(missing.status_code, 404)

    def test_add_source_invalid_kind(self):
        r = self.client.post(
            "/api/knowledge/sources",
            json={"id": "bad", "kind": "unknown-kind"},
        )
        self.assertEqual(r.status_code, 400)

    def test_import_files_and_detect(self):
        r = self.client.post(
            "/api/knowledge/import/files",
            json={
                "kb": "builtin",
                "files": [
                    {"filename": "install.md", "content": "pip install loom"},
                    {"filename": "logo.png", "content": "xxx"},
                ],
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["count"], 1)
        self.assertTrue(body["skipped"])

        det = self.client.post(
            "/api/knowledge/sources/detect",
            json={"url": "https://x.notion.so/abc"},
        )
        self.assertEqual(det.json()["kind"], "notion")

        auto = self.client.post(
            "/api/knowledge/sources",
            json={"id": "auto-1", "kind": "auto", "endpoint": "https://docs.example.com"},
        )
        self.assertEqual(auto.status_code, 200)
        self.assertEqual(auto.json()["detectedKind"], "docs")


if __name__ == "__main__":
    unittest.main()
