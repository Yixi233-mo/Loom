"""T14 单元测试：示例 Workflow 矩阵 — 多场景编译 + 执行。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dsl.compiler import DSLCompiler  # noqa: E402
from dsl.schema import validate_workflow  # noqa: E402
from plugins.example.notes_runtime import NotesStore  # noqa: E402
from plugins.example.workflow_matrix import run_workflow_file  # noqa: E402
from plugins.example.workflow_runner import WorkflowRunner, run_daily_report  # noqa: E402

import yaml  # noqa: E402

WORKFLOWS = ROOT / "plugins" / "example" / "workflows"
LEGACY = ROOT / "plugins" / "example" / "workflow.yaml"

# 矩阵：文件名 → (trigger_type, device)
MATRIX = {
    "daily_report.yaml": ("cron", "pc"),
    "on_feishu_keyword.yaml": ("webhook", "any"),
    "on_new_file.yaml": ("file", "pc"),
    "mobile_to_pc_pdf.yaml": ("webhook", "pc"),
}


class TestWorkflowMatrix(unittest.TestCase):
    def setUp(self):
        self.compiler = DSLCompiler()
        self.store = NotesStore()
        self.store.create("样例", "内容")

    def test_matrix_files_exist(self):
        names = {p.name for p in WORKFLOWS.glob("*.yaml")}
        self.assertEqual(names, set(MATRIX.keys()))

    def test_each_compiles_and_schema_ok(self):
        """验收：每个示例可编译且 schema 合法。"""
        for fname, (ttype, device) in MATRIX.items():
            path = WORKFLOWS / fname
            spec = yaml.safe_load(path.read_text(encoding="utf-8"))
            self.assertEqual(validate_workflow(spec), [], fname)
            compiled = self.compiler.compile_workflow(str(path))
            self.assertEqual(compiled["kind"], "workflow")
            self.assertEqual(compiled["trigger"]["type"], ttype, fname)
            self.assertEqual(compiled["device"], device, fname)
            self.assertGreaterEqual(len(compiled["nodes"]), 1)

    def test_each_runs_to_done(self):
        """验收：每个示例可执行且 status=done。"""
        for fname in MATRIX:
            path = WORKFLOWS / fname
            result = run_workflow_file(str(path), store=self.store)
            self.assertEqual(result["status"], "done", f"{fname}: {result}")
            for nid, step in result["steps"].items():
                self.assertTrue(step["ok"], f"{fname}/{nid}: {step}")

    def test_daily_report_nodes(self):
        result = run_workflow_file(str(WORKFLOWS / "daily_report.yaml"), store=self.store)
        self.assertEqual(
            list(result["steps"].keys()), ["fetch", "summarize", "report"]
        )
        self.assertEqual(result["steps"]["fetch"]["output"]["count"], 1)

    def test_webhook_workflow_captures(self):
        store = NotesStore()
        result = run_workflow_file(
            str(WORKFLOWS / "on_feishu_keyword.yaml"),
            store=store,
        )
        self.assertEqual(result["status"], "done")
        # notes.create 被调用
        self.assertIn("capture", result["steps"])

    def test_file_workflow_steps(self):
        result = run_workflow_file(str(WORKFLOWS / "on_new_file.yaml"), store=self.store)
        self.assertEqual(result["status"], "done")
        self.assertIn("parse", result["steps"])
        self.assertIn("archive", result["steps"])

    def test_mobile_to_pc_workflow(self):
        result = run_workflow_file(str(WORKFLOWS / "mobile_to_pc_pdf.yaml"), store=self.store)
        self.assertEqual(result["status"], "done")
        self.assertEqual(result["workflow"], "mobile_to_pc_pdf")

    def test_legacy_workflow_still_runs(self):
        result = run_daily_report(store_notes=[{"title": "旧版", "content": "x"}])
        self.assertEqual(result["status"], "done")

    def test_trigger_types_covered(self):
        types = {v[0] for v in MATRIX.values()}
        self.assertLessEqual({"cron", "webhook", "file"}, types)


if __name__ == "__main__":
    unittest.main()
