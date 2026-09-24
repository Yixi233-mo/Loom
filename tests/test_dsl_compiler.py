"""T1 单元测试：覆盖 4 类 DSL 成功编译 + 错误场景。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# 保证从项目根目录可 import dsl
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dsl.compiler import DSLCompiler, DSLParseError  # noqa: E402

EX = ROOT / "dsl" / "examples"


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.c = DSLCompiler()

    def test_compile_ok(self):
        result = self.c.compile_workflow(str(EX / "workflow.yaml"))
        self.assertEqual(result["kind"], "workflow")
        self.assertEqual(result["name"], "weekly_report")
        self.assertEqual(result["device"], "pc")
        self.assertEqual(len(result["nodes"]), 3)
        self.assertEqual(result["nodes"][0]["type"], "tool")
        self.assertEqual(result["nodes"][0]["target"], "excel.read")
        self.assertEqual(result["nodes"][1]["type"], "agent")
        self.assertEqual(result["nodes"][1]["target"], "claude_code")

    def test_missing_steps(self):
        path = EX / "_tmp_wf_no_steps.yaml"
        path.write_text("name: x\ndevice: pc\n", encoding="utf-8")
        try:
            with self.assertRaises(DSLParseError) as ctx:
                self.c.compile_workflow(str(path))
            self.assertIn("steps", ctx.exception.message)
        finally:
            path.unlink(missing_ok=True)

    def test_tool_and_agent_conflict(self):
        with self.assertRaises(DSLParseError) as ctx:
            self.c.compile_workflow(str(EX / "error.yaml"))
        self.assertGreater(ctx.exception.line, 0)
        self.assertIn("tool", ctx.exception.message)

    def test_invalid_device(self):
        path = EX / "_tmp_wf_bad_device.yaml"
        path.write_text(
            "name: x\ndevice: watch\nsteps:\n  - id: a\n    tool: t\n",
            encoding="utf-8",
        )
        try:
            with self.assertRaises(DSLParseError) as ctx:
                self.c.compile_workflow(str(path))
            self.assertIn("device", ctx.exception.message)
        finally:
            path.unlink(missing_ok=True)


class TestPlugin(unittest.TestCase):
    def setUp(self):
        self.c = DSLCompiler()

    def test_compile_ok(self):
        result = self.c.compile_plugin(str(EX / "plugin.yaml"))
        self.assertEqual(result["kind"], "plugin")
        self.assertEqual(result["name"], "notes")
        self.assertEqual(result["version"], "1.0.0")
        self.assertEqual(result["ui"]["type"], "list")
        self.assertEqual(len(result["tools"]), 2)
        self.assertEqual(result["tools"][0]["name"], "notes.list")

    def test_tool_missing_name(self):
        path = EX / "_tmp_plugin_bad.yaml"
        path.write_text(
            "name: p\nversion: 1\ntools:\n  - description: x\n",
            encoding="utf-8",
        )
        try:
            with self.assertRaises(DSLParseError) as ctx:
                self.c.compile_plugin(str(path))
            self.assertIn("name", ctx.exception.message)
            self.assertGreater(ctx.exception.line, 0)
        finally:
            path.unlink(missing_ok=True)


class TestAgent(unittest.TestCase):
    def setUp(self):
        self.c = DSLCompiler()

    def test_compile_ok(self):
        result = self.c.compile_agent(str(EX / "agent.yaml"))
        self.assertEqual(result["kind"], "agent")
        self.assertEqual(result["name"], "code_reviewer")
        self.assertEqual(result["base"], "claude_code")
        self.assertIn("代码审查", result["system_prompt"])
        self.assertEqual(result["tools"], ["filesystem.read", "git.diff"])

    def test_missing_system_prompt(self):
        path = EX / "_tmp_agent_no_prompt.yaml"
        path.write_text("name: a\nbase: b\ntools: []\n", encoding="utf-8")
        try:
            with self.assertRaises(DSLParseError) as ctx:
                self.c.compile_agent(str(path))
            self.assertIn("system_prompt", ctx.exception.message)
        finally:
            path.unlink(missing_ok=True)


class TestTrigger(unittest.TestCase):
    def setUp(self):
        self.c = DSLCompiler()

    def test_compile_ok(self):
        result = self.c.compile_trigger(str(EX / "trigger.yaml"))
        self.assertEqual(result["kind"], "trigger")
        self.assertEqual(result["name"], "on_feishu_message")
        self.assertEqual(result["type"], "webhook")
        self.assertEqual(result["action"]["workflow"], "weekly_report")

    def test_invalid_type(self):
        path = EX / "_tmp_trigger_bad_type.yaml"
        path.write_text(
            "name: t\ntype: mqtt\naction:\n  workflow: w\n",
            encoding="utf-8",
        )
        try:
            with self.assertRaises(DSLParseError) as ctx:
                self.c.compile_trigger(str(path))
            self.assertIn("type", ctx.exception.message)
        finally:
            path.unlink(missing_ok=True)

    def test_missing_action(self):
        path = EX / "_tmp_trigger_no_action.yaml"
        path.write_text("name: t\ntype: cron\n", encoding="utf-8")
        try:
            with self.assertRaises(DSLParseError) as ctx:
                self.c.compile_trigger(str(path))
            self.assertIn("action", ctx.exception.message)
        finally:
            path.unlink(missing_ok=True)


class TestSyntaxError(unittest.TestCase):
    def setUp(self):
        self.c = DSLCompiler()

    def test_yaml_syntax_error_has_line(self):
        with self.assertRaises(DSLParseError) as ctx:
            self.c.compile_workflow(str(EX / "error_syntax.yaml"))
        self.assertIn("error_syntax.yaml", str(ctx.exception))
        self.assertGreater(ctx.exception.line, 0)

    def test_auto_dispatch(self):
        c = DSLCompiler()
        self.assertEqual(c.compile_auto(str(EX / "workflow.yaml"))["kind"], "workflow")
        self.assertEqual(c.compile_auto(str(EX / "plugin.yaml"))["kind"], "plugin")
        self.assertEqual(c.compile_auto(str(EX / "agent.yaml"))["kind"], "agent")
        self.assertEqual(c.compile_auto(str(EX / "trigger.yaml"))["kind"], "trigger")

    def test_unknown_kind(self):
        path = EX / "_tmp_unknown.yaml"
        path.write_text("kind: spaceship\nname: x\n", encoding="utf-8")
        try:
            with self.assertRaises(DSLParseError):
                self.c.compile_auto(str(path))
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
