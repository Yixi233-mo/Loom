"""LLM 功能测试：加密 / 配置 / 拉取模型 / API。"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from llm.client import LLMBackedGenerator, LLMClient  # noqa: E402
from llm.config import LLMConfigStore  # noqa: E402
from llm.crypto import CryptoError, decrypt, encrypt, mask_secret  # noqa: E402


class TestCrypto(unittest.TestCase):
    def test_encrypt_decrypt_roundtrip(self):
        tok = encrypt("sk-secret-key-123", "master")
        self.assertNotIn("sk-secret-key-123", tok)
        self.assertEqual(decrypt(tok, "master"), "sk-secret-key-123")

    def test_wrong_key_fails(self):
        tok = encrypt("abc", "m1")
        with self.assertRaises(CryptoError):
            decrypt(tok, "m2")

    def test_mask(self):
        self.assertEqual(mask_secret(""), "")
        self.assertEqual(mask_secret("short"), "***")
        self.assertTrue(mask_secret("sk-abcdefghijk").startswith("sk-a"))


class TestConfigStore(unittest.TestCase):
    def setUp(self):
        self.path = ROOT / "apps" / "hub" / "plugins" / "_llm_cfg.json"
        self.store = LLMConfigStore(self.path, master_key="m")

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_upsert_encrypts_api_key(self):
        p = self.store.upsert(
            name="DeepSeek",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-test-abc",
            default_model="deepseek-chat",
        )
        self.assertTrue(p.api_key_enc)
        self.assertNotIn("sk-test-abc", p.api_key_enc)
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn("sk-test-abc", raw)
        self.assertIn("***", p.to_public()["apiKeyMasked"])

    def test_reload_decrypts(self):
        self.store.upsert("A", "https://x/v1", api_key="sk-reload")
        store2 = LLMConfigStore(self.path, master_key="m")
        pid = list(store2.providers)[0]
        self.assertEqual(store2.api_key_plain(pid), "sk-reload")

    def test_select_model(self):
        p = self.store.upsert("A", "https://x/v1", api_key="k")
        self.store.set_models(p.provider_id, ["m1", "m2"])
        self.store.upsert(
            "A", "https://x/v1", api_key="", default_model="m2", provider_id=p.provider_id
        )
        self.assertEqual(self.store.providers[p.provider_id].default_model, "m2")
        self.assertEqual(self.store.providers[p.provider_id].models, ["m1", "m2"])


class TestLLMClient(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_models_openai_shape(self):
        class FakeHttp:
            async def get_json(self, url, headers):
                return {"data": [{"id": "deepseek-chat"}, {"id": "deepseek-reasoner"}]}

            async def post_json(self, url, headers, body):
                return {}

        c = LLMClient(http=FakeHttp())  # type: ignore[arg-type]
        models = await c.fetch_models("https://api.x/v1", "sk-1")
        self.assertEqual(models, ["deepseek-chat", "deepseek-reasoner"])

    async def test_fetch_models_fallback_path(self):
        calls = []

        class FakeHttp:
            async def get_json(self, url, headers):
                calls.append(url)
                if "/v1/models" in url:
                    raise RuntimeError("404")
                return {"models": [{"name": "qwen-max"}]}

            async def post_json(self, url, headers, body):
                return {}

        c = LLMClient(http=FakeHttp())  # type: ignore[arg-type]
        models = await c.fetch_models("https://api.y/v1", "")
        self.assertEqual(models, ["qwen-max"])
        self.assertTrue(any(u.endswith("/models") for u in calls))

    async def test_llm_generator(self):
        class FakeHttp:
            async def get_json(self, url, headers):
                return {"data": []}

            async def post_json(self, url, headers, body):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "name: t\ndevice: pc\nsteps:\n  - id: a\n    tool: notes.list\n"
                            }
                        }
                    ]
                }

        gen = LLMBackedGenerator(
            LLMClient(http=FakeHttp()),  # type: ignore[arg-type]
            "https://api.z/v1",
            "sk",
            "m1",
        )
        out = await gen.generate_async("生成日报")
        self.assertIn("name: t", out)


class TestLlmApi(unittest.TestCase):
    def setUp(self):
        from api.llm_routes import create_llm_router
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        self.path = ROOT / "apps" / "hub" / "plugins" / "_llm_api.json"
        self.store = LLMConfigStore(self.path, master_key="m")

        class FakeHttp:
            async def get_json(self, url, headers):
                return {"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}]}

            async def post_json(self, url, headers, body):
                return {}

        self.app = FastAPI()
        self.app.include_router(create_llm_router(self.store, LLMClient(http=FakeHttp())))  # type: ignore[arg-type]
        self.client = TestClient(self.app)

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def test_save_masked_and_fetch_models(self):
        r = self.client.post(
            "/api/llm/providers",
            json={
                "name": "OpenAI",
                "baseUrl": "https://api.openai.com/v1",
                "apiKey": "sk-live-secret",
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertNotIn("sk-live-secret", json.dumps(body))
        self.assertTrue(body["hasApiKey"])
        pid = body["providerId"]

        r2 = self.client.post(f"/api/llm/providers/{pid}/fetch-models")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["models"], ["gpt-4o", "gpt-4o-mini"])

        r3 = self.client.post(
            f"/api/llm/providers/{pid}/select", json={"model": "gpt-4o"}
        )
        self.assertEqual(r3.json()["defaultModel"], "gpt-4o")

        r4 = self.client.get(f"/api/llm/providers/{pid}/models")
        self.assertIn("gpt-4o", r4.json()["models"])


if __name__ == "__main__":
    unittest.main()
