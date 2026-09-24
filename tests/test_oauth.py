"""N11 OAuth 测试 — 未授权无法注册 / 过期续期。"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.auth_routes import create_auth_router  # noqa: E402
from auth.oauth import AuthError, OAuthService, TokenExpired, extract_bearer  # noqa: E402
from device_mesh.ws_server import _verify_signature, make_signature  # noqa: E402


class TestTokenIssueVerify(unittest.TestCase):
    def setUp(self):
        self.oauth = OAuthService(secret="s1", access_ttl=2, refresh_ttl=10)

    def test_issue_and_verify(self):
        pair = self.oauth.issue_tokens("pc-1", "pc")
        self.assertTrue(pair.access_token)
        self.assertTrue(pair.refresh_token)
        claims = self.oauth.verify_access(pair.access_token)
        self.assertEqual(claims["sub"], "pc-1")
        self.assertEqual(claims["typ"], "access")

    def test_bad_signature_rejected(self):
        pair = self.oauth.issue_tokens("pc-1", "pc")
        other = OAuthService(secret="s2")
        with self.assertRaises(AuthError):
            other.verify_access(pair.access_token)

    def test_empty_device_id(self):
        with self.assertRaises(AuthError):
            self.oauth.issue_tokens("", "pc")


class TestUnauthorizedRegister(unittest.TestCase):
    """验收：未授权设备无法注册。"""

    def test_allow_register_requires_token(self):
        oauth = OAuthService(secret="s1")
        with self.assertRaises(AuthError):
            oauth.allow_register(None)
        with self.assertRaises(AuthError):
            oauth.allow_register("")
        with self.assertRaises(AuthError):
            oauth.allow_register("not-a-token")

    def test_expired_access_denies_register(self):
        oauth = OAuthService(secret="s1", access_ttl=0)
        pair = oauth.issue_tokens("pc-1", "pc")
        time.sleep(0.01)
        with self.assertRaises((AuthError, TokenExpired)):
            oauth.allow_register(pair.access_token)

    def test_forged_token_denied(self):
        oauth = OAuthService(secret="s1")
        forged = "eyJzdWIiOiJoYWNrZXIifQ.forgedsig"
        with self.assertRaises(AuthError):
            oauth.allow_register(forged)


class TestRefresh(unittest.TestCase):
    """验收：token 过期可续期。"""

    def test_refresh_rotates_and_extends(self):
        oauth = OAuthService(secret="s1", access_ttl=1, refresh_ttl=60)
        pair1 = oauth.issue_tokens("pc-1", "mobile")
        time.sleep(1.05)
        with self.assertRaises(TokenExpired):
            oauth.verify_access(pair1.access_token)

        pair2 = oauth.refresh(pair1.refresh_token)
        # 新 access 可用
        claims = oauth.verify_access(pair2.access_token)
        self.assertEqual(claims["sub"], "pc-1")
        self.assertEqual(claims["device_type"], "mobile")
        # 旧 refresh 轮换吊销
        with self.assertRaises(AuthError):
            oauth.verify_refresh(pair1.refresh_token)

    def test_refresh_expired_refresh_fails(self):
        oauth = OAuthService(secret="s1", access_ttl=1, refresh_ttl=0)
        pair = oauth.issue_tokens("pc-1", "pc")
        time.sleep(0.01)
        with self.assertRaises((AuthError, TokenExpired)):
            oauth.refresh(pair.refresh_token)

    def test_access_cannot_be_used_as_refresh(self):
        oauth = OAuthService(secret="s1")
        pair = oauth.issue_tokens("pc-1", "pc")
        with self.assertRaises(AuthError):
            oauth.refresh(pair.access_token)


class TestAuthApi(unittest.TestCase):
    def setUp(self):
        self.oauth = OAuthService(secret="api-s")
        app = FastAPI()
        app.include_router(create_auth_router(self.oauth))
        self.client = TestClient(app)

    def test_token_and_refresh_endpoints(self):
        r = self.client.post(
            "/api/auth/token", json={"deviceId": "web-1", "deviceType": "tablet"}
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("access_token", body)
        self.assertIn("refresh_token", body)

        r2 = self.client.post(
            "/api/auth/refresh", json={"refreshToken": body["refresh_token"]}
        )
        self.assertEqual(r2.status_code, 200)
        self.assertIn("access_token", r2.json())

        r3 = self.client.get(
            "/api/auth/whoami",
            headers={"Authorization": "Bearer " + r2.json()["access_token"]},
        )
        self.assertEqual(r3.json()["deviceId"], "web-1")

    def test_whoami_unauthorized(self):
        r = self.client.get("/api/auth/whoami")
        self.assertEqual(r.status_code, 401)

    def test_refresh_bad_token_401(self):
        r = self.client.post("/api/auth/refresh", json={"refreshToken": "bad"})
        self.assertEqual(r.status_code, 401)


class TestExtractBearer(unittest.TestCase):
    def test_extract(self):
        self.assertEqual(extract_bearer("Bearer abc"), "abc")
        self.assertEqual(extract_bearer("bearer abc"), "abc")
        self.assertEqual(extract_bearer("abc"), "abc")
        self.assertIsNone(extract_bearer(None))


if __name__ == "__main__":
    unittest.main()
