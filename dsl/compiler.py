"""DSL Compiler — 解析 4 类 DSL，返回结构化 dict。

只解析，不执行 DSL 中的任何代码。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


class DSLParseError(Exception):
    """DSL 解析错误，携带文件名与行号。"""

    def __init__(self, filename: str, line: int, message: str):
        self.filename = filename
        self.line = line
        self.message = message
        super().__init__(f"{filename}:{line}: {message}")

    def __str__(self) -> str:
        return f"{self.filename}:{self.line}: {self.message}"


KIND_WORKFLOW = "workflow"
KIND_PLUGIN = "plugin"
KIND_AGENT = "agent"
KIND_TRIGGER = "trigger"

_VALID_KINDS = {KIND_WORKFLOW, KIND_PLUGIN, KIND_AGENT, KIND_TRIGGER}
_TRIGGER_TYPES = {"cron", "webhook", "keyword", "file"}
_DEVICE_TYPES = {"pc", "tablet", "mobile", "any"}


def _load_yaml(raw: str, filename: str) -> Any:
    """解析 YAML 文本，语法错误转为 DSLParseError（含行号）。"""
    try:
        return yaml.safe_load(raw)
    except yaml.MarkedYAMLError as e:
        mark = e.problem_mark
        line = mark.line + 1 if mark is not None else 0
        problem = e.problem or "YAML 语法错误"
        raise DSLParseError(filename, line, problem) from e
    except yaml.YAMLError as e:
        raise DSLParseError(filename, 0, f"YAML 语法错误: {e}") from e


def _compose_tree(raw: str, filename: str) -> Optional[yaml.Node]:
    try:
        return yaml.compose(raw, Loader=yaml.SafeLoader)
    except yaml.YAMLError as e:
        mark = getattr(e, "problem_mark", None)
        line = mark.line + 1 if mark is not None else 0
        raise DSLParseError(filename, line, f"YAML 语法错误: {e}") from e


def _key_line(raw: str, filename: str, *key_path: str) -> int:
    """按顶层 key 路径查找行号（1-based），找不到则返回 1。"""
    node = _compose_tree(raw, filename)
    for key in key_path:
        if not isinstance(node, yaml.MappingNode):
            return node.start_mark.line + 1 if node is not None else 1
        found = None
        for k, v in node.value:
            if isinstance(k, yaml.ScalarNode) and k.value == key:
                found = v
                break
        if found is None:
            # 找不到 key 时，返回父节点行号
            return node.start_mark.line + 1
        node = found
    if node is not None:
        return node.start_mark.line + 1
    return 1


def _seq_item_line(raw: str, filename: str, list_key: str, index: int) -> int:
    """查找 YAML 中 list_key 列表第 index 项的行号。"""
    node = _compose_tree(raw, filename)
    if not isinstance(node, yaml.MappingNode):
        return 1
    for k, v in node.value:
        if isinstance(k, yaml.ScalarNode) and k.value == list_key and isinstance(v, yaml.SequenceNode):
            if 0 <= index < len(v.value):
                return v.value[index].start_mark.line + 1
            return v.start_mark.line + 1
    return 1


def _detect_kind(spec: Dict[str, Any], filename: str = "<memory>", line: int = 1) -> str:
    """根据结构推断 DSL kind。"""
    if "kind" in spec:
        k = spec["kind"]
        if k in _VALID_KINDS:
            return k
        raise DSLParseError(filename, line, f"未知 DSL kind: {k!r}")
    if "steps" in spec:
        return KIND_WORKFLOW
    if "system_prompt" in spec or ("base" in spec and "name" in spec and "ui" not in spec):
        return KIND_AGENT
    if "action" in spec and "type" in spec:
        return KIND_TRIGGER
    if "ui" in spec or ("tools" in spec and "version" in spec):
        return KIND_PLUGIN
    raise DSLParseError(filename, line, "无法识别 DSL 类型（缺少 kind 或特征字段）")


class DSLCompiler:
    """DSL → 结构化 dict（后续可扩展为 LangGraph 图 + MCP Tools + UI Schema）。"""

    def compile_workflow(self, yaml_path: str) -> Dict[str, Any]:
        """编译 Workflow DSL → {name, trigger, device, nodes}"""
        path = Path(yaml_path)
        raw = path.read_text(encoding="utf-8")
        filename = str(path)
        spec = _load_yaml(raw, filename)
        if not isinstance(spec, dict):
            raise DSLParseError(filename, 1, "Workflow 根节点必须是映射（mapping）")

        if "name" not in spec or not spec["name"]:
            raise DSLParseError(filename, 1, "缺少必填字段: name")
        if "steps" not in spec or not isinstance(spec["steps"], list) or not spec["steps"]:
            raise DSLParseError(filename, _key_line(raw, filename) or 1, "缺少必填字段: steps")

        device = spec.get("device", "any")
        if device not in _DEVICE_TYPES:
            line = _key_line(raw, filename, "device")
            raise DSLParseError(filename, line, f"非法 device: {device!r}，应为 {sorted(_DEVICE_TYPES)}")

        nodes: List[Dict[str, Any]] = []
        for i, step in enumerate(spec["steps"]):
            step_line = _seq_item_line(raw, filename, "steps", i)
            if not isinstance(step, dict):
                raise DSLParseError(filename, step_line, f"steps[{i}] 必须是映射")
            if "id" not in step:
                raise DSLParseError(filename, step_line, f"steps[{i}] 缺少必填字段: id")
            if "tool" not in step and "agent" not in step:
                raise DSLParseError(filename, step_line, f"steps[{i}] 必须包含 tool 或 agent")
            if "tool" in step and "agent" in step:
                raise DSLParseError(filename, step_line, f"steps[{i}] 不能同时包含 tool 和 agent")

            is_tool = "tool" in step
            nodes.append({
                "id": step["id"],
                "type": "tool" if is_tool else "agent",
                "target": step.get("tool") or step.get("agent"),
                "args": step.get("args", {}),
                "prompt": step.get("prompt"),
            })

        result: Dict[str, Any] = {
            "kind": KIND_WORKFLOW,
            "name": spec["name"],
            "trigger": spec.get("trigger"),
            "device": device,
            "nodes": nodes,
        }
        return result

    def compile_plugin(self, yaml_path: str) -> Dict[str, Any]:
        """编译 Plugin DSL → {kind, name, version, ui, tools}"""
        path = Path(yaml_path)
        raw = path.read_text(encoding="utf-8")
        filename = str(path)
        spec = _load_yaml(raw, filename)
        if not isinstance(spec, dict):
            raise DSLParseError(filename, 1, "Plugin 根节点必须是映射（mapping）")

        if "name" not in spec or not spec["name"]:
            raise DSLParseError(filename, 1, "缺少必填字段: name")

        tools = spec.get("tools", [])
        if not isinstance(tools, list):
            line = _key_line(raw, filename, "tools")
            raise DSLParseError(filename, line, "tools 必须是列表")
        for i, tool in enumerate(tools):
            tool_line = _seq_item_line(raw, filename, "tools", i)
            if not isinstance(tool, dict):
                raise DSLParseError(filename, tool_line, f"tools[{i}] 必须是映射")
            if "name" not in tool:
                raise DSLParseError(filename, tool_line, f"tools[{i}] 缺少必填字段: name")

        return {
            "kind": KIND_PLUGIN,
            "name": spec["name"],
            "version": spec.get("version"),
            "ui": spec.get("ui"),
            "tools": tools,
        }

    def compile_agent(self, yaml_path: str) -> Dict[str, Any]:
        """编译 Agent DSL → {kind, name, base, system_prompt, tools}"""
        path = Path(yaml_path)
        raw = path.read_text(encoding="utf-8")
        filename = str(path)
        spec = _load_yaml(raw, filename)
        if not isinstance(spec, dict):
            raise DSLParseError(filename, 1, "Agent 根节点必须是映射（mapping）")

        for key in ("name", "system_prompt"):
            if key not in spec or not spec[key]:
                # 尽量定位到已有字段行号
                line = 1
                for probe in ("name", "base", "system_prompt", "tools"):
                    if probe in spec:
                        line = _key_line(raw, filename, probe)
                        break
                raise DSLParseError(filename, line, f"缺少必填字段: {key}")

        tools = spec.get("tools", [])
        if not isinstance(tools, list):
            line = _key_line(raw, filename, "tools")
            raise DSLParseError(filename, line, "tools 必须是列表")

        return {
            "kind": KIND_AGENT,
            "name": spec["name"],
            "base": spec.get("base"),
            "system_prompt": spec["system_prompt"],
            "tools": tools,
        }

    def compile_trigger(self, yaml_path: str) -> Dict[str, Any]:
        """编译 Trigger DSL → {kind, name, type, source, filter, action}"""
        path = Path(yaml_path)
        raw = path.read_text(encoding="utf-8")
        filename = str(path)
        spec = _load_yaml(raw, filename)
        if not isinstance(spec, dict):
            raise DSLParseError(filename, 1, "Trigger 根节点必须是映射（mapping）")

        for key in ("name", "type", "action"):
            if key not in spec or spec[key] is None:
                line = 1
                for probe in ("name", "type", "source", "action"):
                    if probe in spec:
                        line = _key_line(raw, filename, probe)
                        break
                raise DSLParseError(filename, line, f"缺少必填字段: {key}")

        ttype = spec["type"]
        if ttype not in _TRIGGER_TYPES:
            line = _key_line(raw, filename, "type")
            raise DSLParseError(filename, line, f"非法 type: {ttype!r}，应为 {sorted(_TRIGGER_TYPES)}")

        return {
            "kind": KIND_TRIGGER,
            "name": spec["name"],
            "type": ttype,
            "source": spec.get("source"),
            "filter": spec.get("filter"),
            "action": spec["action"],
        }

    def compile_auto(self, yaml_path: str) -> Dict[str, Any]:
        """根据 DSL 类型自动分发到对应编译方法。"""
        path = Path(yaml_path)
        raw = path.read_text(encoding="utf-8")
        filename = str(path)
        spec = _load_yaml(raw, filename)
        if not isinstance(spec, dict):
            raise DSLParseError(filename, 1, "DSL 根节点必须是映射（mapping）")
        kind = _detect_kind(spec, filename, 1)
        method = {
            KIND_WORKFLOW: self.compile_workflow,
            KIND_PLUGIN: self.compile_plugin,
            KIND_AGENT: self.compile_agent,
            KIND_TRIGGER: self.compile_trigger,
        }[kind]
        return method(yaml_path)
