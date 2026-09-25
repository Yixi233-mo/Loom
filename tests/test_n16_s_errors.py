"""S1 统一错误契约。"""

from __future__ import annotations

import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.errors import install_error_contract, make_error


class TestErrorContract(unittest.TestCase):
    def test_make_error_shape(self):
        b = make_error(404, "session not found", trace_id="tr-1")
        self.assertEqual(b["code"], "NOT_FOUND")
        self.assertIn("message", b)
        self.assertEqual(b["trace_id"], "tr-1")

    def test_http_exception_wrapped(self):
        app = FastAPI()
        install_error_contract(app)

        @app.get("/x")
        def x():
            from fastapi import HTTPException

            raise HTTPException(404, "nope")

        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/x")
        self.assertEqual(r.status_code, 404)
        body = r.json()
        self.assertEqual(body["code"], "NOT_FOUND")
        self.assertIn("trace_id", body)
        self.assertEqual(body["message"], "nope")

    def test_unhandled_is_500_contract(self):
        app = FastAPI()
        install_error_contract(app)

        @app.get("/boom")
        def boom():
            raise RuntimeError("x")

        c = TestClient(app, raise_server_exceptions=False)
        r = c.get("/boom")
        self.assertEqual(r.status_code, 500)
        self.assertEqual(r.json()["code"], "INTERNAL")


if __name__ == "__main__":
    unittest.main()
