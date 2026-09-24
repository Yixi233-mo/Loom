"""T2 单元测试：JSON Schema 校验 — 缺字段 / 类型错误 / 非法值。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dsl.schema import (  # noqa: E402
    AGENT_SCHEMA,
    PLUGIN_SCHEMA,
    SCHEMAS,
    TRIGGER_SCHEMA,
    WORKFLOW_SCHEMA,
    validate,
    validate_agent,
    validate_plugin,
    validate_trigger,
    validate_workflow,
)

EX = ROOT / "dsl" / "examples"


def load(name: str):
    with open(EX / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


class TestSchemasExist(unittest.TestCase):
    def test_four_independent_schemas(self):
        self.assertEqual(set(SCHEMAS), {"workflow", "plugin", "agent", "trigger"})
        for schema in (WORKFLOW_SCHEMA, PLUGIN_SCHEMA, AGENT_SCHEMA, TRIGGER_SCHEMA):
            self.assertEqual(schema["type"], "object")
            self.assertIn("required", schema)
            self.assertIn("properties", schema)


class TestPositiveExamples(unittest.TestCase):
    """正例：示例文件全部通过校验。"""

    def test_workflow_ok(self):
        self.assertEqual(validate_workflow(load("workflow.yaml")), [])

    def test_plugin_ok(self):
        self.assertEqual(validate_plugin(load("plugin.yaml")), [])

    def test_agent_ok(self):
        self.assertEqual(validate_agent(load("agent.yaml")), [])

    def test_trigger_ok(self):
        self.assertEqual(validate_trigger(load("trigger.yaml")), [])


class TestMissingFields(unittest.TestCase):
    def test_workflow_missing_name(self):
        errors = validate_workflow({"steps": [{"id": "a", "tool": "t"}]})
        self.assertTrue(any("name" in e.message for e in errors))

    def test_workflow_missing_steps(self):
        errors = validate_workflow({"name": "x"})
        self.assertTrue(any("steps" in e.message for e in errors))

    def test_workflow_step_missing_id(self):
        errors = validate_workflow({"name": "x", "steps": [{"tool": "t"}]})
        self.assertTrue(any("id" in e.message for e in errors))

    def test_plugin_missing_name(self):
        errors = validate_plugin({"tools": []})
        self.assertTrue(any("name" in e.message for e in errors))

    def test_plugin_tool_missing_name(self):
        errors = validate_plugin({"name": "p", "tools": [{"description": "d"}]})
        self.assertTrue(any("name" in e.message for e in errors))
        self.assertTrue(any("/tools/0" in e.path for e in errors))

    def test_agent_missing_system_prompt(self):
        errors = validate_agent({"name": "a"})
        self.assertTrue(any("system_prompt" in e.message for e in errors))

    def test_trigger_missing_action(self):
        errors = validate_trigger({"name": "t", "type": "cron"})
        self.assertTrue(any("action" in e.message for e in errors))


class TestTypeErrors(unittest.TestCase):
    def test_workflow_name_not_string(self):
        errors = validate_workflow({"name": 123, "steps": [{"id": "a", "tool": "t"}]})
        self.assertTrue(any("类型错误" in e.message for e in errors))

    def test_workflow_steps_not_array(self):
        errors = validate_workflow({"name": "x", "steps": "not-a-list"})
        self.assertTrue(any("类型错误" in e.message for e in errors))

    def test_plugin_tools_not_array(self):
        errors = validate_plugin({"name": "p", "tools": {}})
        self.assertTrue(any("类型错误" in e.message for e in errors))

    def test_agent_tools_item_not_string(self):
        errors = validate_agent({"name": "a", "system_prompt": "s", "tools": [1, 2]})
        self.assertTrue(any("类型错误" in e.message for e in errors))

    def test_trigger_filter_not_object(self):
        errors = validate_trigger({"name": "t", "type": "cron", "action": {}, "filter": []})
        self.assertTrue(any("类型错误" in e.message for e in errors))

    def test_root_not_object(self):
        errors = validate([1, 2], "workflow")
        self.assertTrue(any("根节点" in e.message for e in errors))


class TestIllegalValues(unittest.TestCase):
    def test_workflow_bad_device(self):
        errors = validate_workflow({
            "name": "x",
            "device": "watch",
            "steps": [{"id": "a", "tool": "t"}],
        })
        self.assertTrue(any("非法值" in e.message for e in errors))

    def test_trigger_bad_type(self):
        errors = validate_trigger({"name": "t", "type": "mqtt", "action": {}})
        self.assertTrue(any("非法值" in e.message for e in errors))

    def test_workflow_empty_name(self):
        errors = validate_workflow({"name": "", "steps": [{"id": "a", "tool": "t"}]})
        self.assertTrue(any("过短" in e.message for e in errors))

    def test_workflow_empty_steps(self):
        errors = validate_workflow({"name": "x", "steps": []})
        self.assertTrue(any("过短" in e.message for e in errors))

    def test_unknown_kind(self):
        errors = validate({}, "spaceship")
        self.assertTrue(any("未知" in e.message for e in errors))

    def test_error_yaml_captures(self):
        """error.yaml（tool+agent 冲突）在 schema 层不拦（是编译期语义），但 type 结构合法。"""
        # schema 允许 tool/agent 共存，由 compiler 拦截；此处仅确认不会误报类型错
        spec = load("error.yaml")
        errors = validate_workflow(spec)
        self.assertFalse(any("类型错误" in e.message for e in errors))


class TestErrorListNotException(unittest.TestCase):
    def test_returns_list(self):
        result = validate_workflow({})
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for e in result:
            self.assertTrue(hasattr(e, "path"))
            self.assertTrue(hasattr(e, "message"))

    def test_valid_returns_empty(self):
        self.assertEqual(validate_agent(load("agent.yaml")), [])


if __name__ == "__main__":
    unittest.main()
