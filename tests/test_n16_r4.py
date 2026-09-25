"""R4 部署 / 版本 / 发布材料。"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class TestDeployArtifacts(unittest.TestCase):
    def test_dockerfile_and_compose(self):
        df = (ROOT / "deploy" / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("python", df)
        self.assertIn("run_hub_server", df)
        compose = (ROOT / "deploy" / "docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("loom/hub:0.1.0", compose)
        self.assertIn("restart: unless-stopped", compose)
        self.assertIn("data", compose)
        self.assertIn("plugins", compose)

    def test_env_example_exists(self):
        t = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("WS_SECRET", t)
        self.assertIn("LOOM_MASTER_KEY", t)

    def test_install_changelog(self):
        self.assertTrue((ROOT / "docs" / "INSTALL.md").exists())
        self.assertTrue((ROOT / "docs" / "CHANGELOG.md").exists())
        self.assertIn("npm run start", (ROOT / "docs" / "INSTALL.md").read_text(encoding="utf-8"))

    def test_release_workflow(self):
        t = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")
        self.assertIn('tags:', t)
        self.assertIn("v*", t)
        self.assertIn("windows-msi", t)
        self.assertIn("android-apk", t)
        self.assertIn("docker", t)
        self.assertIn("CHANGELOG.md", t)
        self.assertIn("notify-failure", t)

    def test_versions_consistent(self):
        import os

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_versions.py")],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
        self.assertEqual(r.returncode, 0, str(r.stdout) + str(r.stderr))
        self.assertTrue("OK" in (r.stdout or ""))

    def test_rollback_docs(self):
        t = (ROOT / "docs" / "RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("回滚", t)


if __name__ == "__main__":
    unittest.main()
