"""N9 对话式生成 DSL 测试 — 校验门禁 + diff + 确认才落盘。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from dsl.conversational import (
    ConversationalDslService,
    RuleBasedGenerator,
)


class TestRuleBasedGenerator(unittest.TestCase):
    def test_generate_daily_report(self):
        g = RuleBasedGenerator()
        y = g.generate("每天 9 点把笔记总结成日报")
        self.assertIn("name: daily_report", y)
        self.assertIn('cron: "0 9 * * *"', y)
        self.assertIn("notes.list", y)
        self.assertIn("builtin_rag", y)

    def test_generate_weekly(self):
        g = RuleBasedGenerator()
        y = g.generate("每周一生成周报并发送")
        self.assertIn("weekly_report", y)
        self.assertIn("0 9 * * 1", y)


class TestConversationalFlow(unittest.TestCase):
    def setUp(self):
        self.out = ROOT / "apps" / "hub" / "plugins" / "_n9_out"
        self.svc = ConversationalDslService(workspace_root=self.out)

    def tearDown(self):
        import shutil

        if self.out.exists():
            shutil.rmtree(self.out)

    def test_propose_validates_and_shows_diff(self):
        draft = self.svc.propose("每天 9 点把笔记总结成日报", filename="daily.yaml")
        self.assertTrue(draft.ok)
        self.assertIn("name: daily_report", draft.yaml_text)
        self.assertIn("---", draft.diff())
        self.assertIn("+++", draft.diff())
        self.assertFalse(draft.written)

    def test_confirm_required_before_write(self):
        """验收：未确认不写盘。"""
        draft = self.svc.propose("每天总结笔记", filename="guard.yaml")
        with self.assertRaises(PermissionError):
            self.svc.confirm_and_write(draft.draft_id)
        self.assertFalse(Path(self.out / "guard.yaml").exists())

        self.svc.confirm(draft.draft_id)
        path = self.svc.confirm_and_write(draft.draft_id)
        self.assertTrue(path.exists())
        self.assertTrue(draft.written)
        text = path.read_text(encoding="utf-8")
        self.assertIn("name:", text)

    def test_generated_dsl_passes_schema(self):
        """验收：生成的 DSL 通过 Schema 校验。"""
        for text in (
            "每天 9 点把笔记总结成日报",
            "每周一生成周报并发送",
            "每小时检查一次",
            "随便说点啥",
        ):
            draft = self.svc.propose(text)
            self.assertTrue(draft.ok, f"{text} -> {draft.validation_errors}")

    def test_invalid_generator_blocked(self):
        class BadGen:
            def generate(self, user_text: str) -> str:
                return "device: pc\nsteps: []\n"  # 缺 name

        svc = ConversationalDslService(generator=BadGen(), workspace_root=self.out)
        draft = svc.propose("bad")
        self.assertFalse(draft.ok)
        self.assertTrue(draft.validation_errors)
        svc.confirm  # noqa: B018 — 可调用存在
        with self.assertRaises(ValueError):
            svc.confirm(draft.draft_id)
        # 未确认 → PermissionError
        with self.assertRaises(PermissionError):
            svc.confirm_and_write(draft.draft_id)
        # 强行标记确认后仍因校验失败拒绝写盘
        draft.confirmed = True
        with self.assertRaises(ValueError):
            svc.confirm_and_write(draft.draft_id)
        self.assertFalse((self.out / "exist.yaml").exists())

    def test_double_write_rejected(self):
        draft = self.svc.propose("每天日报", filename="once.yaml")
        self.svc.confirm(draft.draft_id)
        self.svc.confirm_and_write(draft.draft_id)
        with self.assertRaises(RuntimeError):
            self.svc.confirm_and_write(draft.draft_id)

    def test_existing_file_diff(self):
        old = "name: old_task\ndevice: pc\nsteps:\n  - id: a\n    tool: t\n"
        draft = self.svc.propose("每天日报", filename="exist.yaml", existing_yaml=old)
        d = draft.diff()
        self.assertIn("-name: old_task", d.replace("\n", "\n-"))
        self.assertIn("name:", draft.yaml_text)


if __name__ == "__main__":
    unittest.main()
