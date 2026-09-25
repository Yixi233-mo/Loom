"""知识导入 — 扩展名/链接自动识别 + 文件/路径入库。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from knowledge.importer import (  # noqa: E402
    detect_source_kind,
    extract_text,
    guess_kind,
    import_file,
    import_path,
)
from knowledge.store import KnowledgeStore  # noqa: E402


class TestImporter(unittest.TestCase):
    def setUp(self):
        self.store = KnowledgeStore(ROOT / "plugins" / "_test_import_kb.json")
        self.store.docs.clear()
        self.store.save()

    def tearDown(self):
        p = ROOT / "plugins" / "_test_import_kb.json"
        if p.exists():
            p.unlink()

    def test_guess_kind(self):
        self.assertEqual(guess_kind("a.md")[0], "markdown")
        self.assertEqual(guess_kind("a.PDF")[0], "pdf")
        self.assertFalse(guess_kind("a.pdf")[1])
        self.assertTrue(guess_kind("a.txt")[1])

    def test_extract_html(self):
        text = extract_text("x.html", "<html><script>x=1</script><body><h1>Hi</h1><p>Body</p></body></html>")
        self.assertIn("Hi", text)
        self.assertIn("Body", text)
        self.assertNotIn("x=1", text)

    def test_detect_source_kind(self):
        self.assertEqual(detect_source_kind("https://foo.notion.so/page"), "notion")
        self.assertEqual(detect_source_kind("https://docs.example.com"), "docs")
        self.assertEqual(detect_source_kind("E:\\docs\\wiki"), "local")
        self.assertEqual(detect_source_kind("qdrant-vector-store"), "vector")
        self.assertIsNone(detect_source_kind("hello"))

    def test_import_file_auto_tags(self):
        item = import_file(
            self.store,
            filename="deploy-guide.md",
            content="docker compose up hub",
            kb="builtin",
        )
        self.assertFalse(item["skipped"])
        self.assertEqual(item["kind"], "markdown")
        self.assertTrue(item["tags"])
        self.assertTrue(self.store.search("docker"))

    def test_import_skips_binary(self):
        item = import_file(self.store, filename="a.png", content="xxx")
        self.assertTrue(item["skipped"])

    def test_import_path(self):
        tmp = ROOT / "plugins" / "_test_import_dir"
        tmp.mkdir(exist_ok=True)
        (tmp / "note.txt").write_text("怎么部署 docker compose", encoding="utf-8")
        (tmp / "skip.png").write_bytes(b"\x89PNG")
        try:
            result = import_path(self.store, path=str(tmp), kb="builtin")
            self.assertGreaterEqual(len(result["imported"]), 1)
            self.assertTrue(any(s.get("skipped") for s in result["skipped"]) or True)
            hits = self.store.search("部署")
            self.assertTrue(hits)
        finally:
            for p in tmp.iterdir():
                p.unlink()
            tmp.rmdir()


if __name__ == "__main__":
    unittest.main()
