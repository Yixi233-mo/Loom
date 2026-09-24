"""T13 单元测试：示例插件 — UI 可显示 / 工作流可触发执行。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dsl.compiler import DSLCompiler  # noqa: E402
from dsl.schema import validate_plugin, validate_workflow  # noqa: E402
from plugins.example.notes_runtime import NotesStore, make_notes_tools  # noqa: E402
from plugins.example.workflow_runner import WorkflowRunner, run_daily_report  # noqa: E402

import yaml  # noqa: E402

EXAMPLE = ROOT / "plugins" / "example"


class TestPluginDsl(unittest.TestCase):
    def test_plugin_yaml_schema_ok(self):
        spec = yaml.safe_load((EXAMPLE / "plugin.yaml").read_text(encoding="utf-8"))
        self.assertEqual(validate_plugin(spec), [])

    def test_workflow_yaml_schema_ok(self):
        spec = yaml.safe_load((EXAMPLE / "workflow.yaml").read_text(encoding="utf-8"))
        self.assertEqual(validate_workflow(spec), [])

    def test_plugin_compiles(self):
        compiled = DSLCompiler().compile_plugin(str(EXAMPLE / "plugin.yaml"))
        self.assertEqual(compiled["name"], "notes")
        self.assertEqual(compiled["ui"]["type"], "list")
        self.assertEqual(compiled["ui"]["props"]["title"], "笔记列表")
        tool_names = [t["name"] for t in compiled["tools"]]
        self.assertIn("notes.list", tool_names)
        self.assertIn("notes.create", tool_names)

    def test_plugin_ui_schema_for_renderer(self):
        """验收素材：plugin.ui 可交给 SchemaRenderer 显示。"""
        compiled = DSLCompiler().compile_plugin(str(EXAMPLE / "plugin.yaml"))
        ui = compiled["ui"]
        self.assertEqual(ui["type"], "list")
        self.assertIn("title", ui["props"])
        self.assertIn("source", ui["props"])

    def test_plugin_json_manifest(self):
        import json

        data = json.loads((EXAMPLE / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "notes")
        self.assertEqual(data["ui"]["type"], "list")


class TestNotesTools(unittest.TestCase):
    def test_notes_create_and_list(self):
        store = NotesStore()
        tools = make_notes_tools(store)
        tools["notes.create"](title="第一条", content="内容A")
        tools["notes.create"](title="第二条")
        listed = tools["notes.list"]()
        self.assertEqual(listed["count"], 2)
        self.assertEqual(listed["notes"][0]["title"], "第一条")

    def test_daily_report_tool(self):
        store = NotesStore()
        tools = make_notes_tools(store)
        tools["notes.create"](title="T1", content="C1")
        report = tools["notes.daily_report"]()
        self.assertIn("日报", report["report"])
        self.assertIn("T1", report["report"])
        self.assertEqual(report["count"], 1)


class TestWorkflowExecution(unittest.TestCase):
    def test_daily_report_runs_end_to_end(self):
        """验收：工作流能被触发执行。"""
        store = NotesStore()
        store.create("早会", "同步进度")
        tools = make_notes_tools(store)
        runner = WorkflowRunner(
            tools=tools,
            agents={
                "builtin_rag": lambda prompt: {"summary": f"已总结: {prompt[:20]}"},
            },
        )
        result = runner.run_yaml(str(EXAMPLE / "workflow.yaml"))
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["workflow"], "daily_report")
        self.assertIn("fetch", result["steps"])
        self.assertIn("summarize", result["steps"])
        self.assertTrue(result["steps"]["fetch"]["ok"])
        self.assertTrue(result["steps"]["summarize"]["ok"])
        # 模板注入：summarize 的 prompt 含 fetch 输出
        summary = result["steps"]["summarize"]["output"]
        self.assertIn("已总结", summary["summary"])

    def test_run_daily_report_helper(self):
        result = run_daily_report(
            store_notes=[{"title": "n1", "content": "c1"}]
        )
        self.assertEqual(result["status"], "done")
        fetch_out = result["steps"]["fetch"]["output"]
        self.assertEqual(fetch_out["count"], 1)

    def test_unknown_tool_fails_gracefully(self):
        runner = WorkflowRunner(tools={})
        result = runner.run(
            {
                "name": "bad",
                "nodes": [{"id": "a", "type": "tool", "target": "nope", "args": {}}],
            }
        )
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["steps"]["a"]["ok"])

    def test_agent_fallback_when_unregistered(self):
        runner = WorkflowRunner(tools={})
        result = runner.run(
            {
                "name": "wf",
                "nodes": [
                    {
                        "id": "a",
                        "type": "agent",
                        "target": "builtin_rag",
                        "prompt": "hello",
                    }
                ],
            }
        )
        self.assertEqual(result["status"], "done")
        self.assertTrue(result["steps"]["a"]["output"]["fallback"])


if __name__ == "__main__":
    unittest.main()
