"""JSON Schema 校验 — 4 类 DSL 的 Schema 定义与校验函数。

优先使用官方 `jsonschema` 库（目标技术栈）；未安装时回退最小校验器。
校验失败返回错误列表，不抛异常。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

try:
    import jsonschema as _js

    _HAS_JSONSCHEMA = True
except ImportError:  # pragma: no cover
    _js = None
    _HAS_JSONSCHEMA = False

# ---------------------------------------------------------------------------
# Schema 定义（标准 JSON Schema 格式）
# ---------------------------------------------------------------------------

WORKFLOW_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "steps"],
    "additionalProperties": True,
    "properties": {
        "kind": {"type": "string", "enum": ["workflow"]},
        "name": {"type": "string", "minLength": 1},
        "trigger": {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["cron", "webhook", "keyword", "file"],
                },
            },
        },
        "device": {"type": "string", "enum": ["pc", "tablet", "mobile", "any"]},
        "steps": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["id"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "tool": {"type": "string", "minLength": 1},
                    "agent": {"type": "string", "minLength": 1},
                    "args": {"type": "object"},
                    "prompt": {"type": "string"},
                },
            },
        },
    },
}

PLUGIN_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["name"],
    "additionalProperties": True,
    "properties": {
        "kind": {"type": "string", "enum": ["plugin"]},
        "name": {"type": "string", "minLength": 1},
        "version": {"type": "string"},
        "ui": {"type": "object"},
        "tools": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {"type": "string", "minLength": 1},
                    "description": {"type": "string"},
                    "parameters": {"type": "object"},
                },
            },
        },
    },
}

AGENT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "system_prompt"],
    "additionalProperties": True,
    "properties": {
        "kind": {"type": "string", "enum": ["agent"]},
        "name": {"type": "string", "minLength": 1},
        "base": {"type": "string"},
        "system_prompt": {"type": "string", "minLength": 1},
        "tools": {"type": "array", "items": {"type": "string"}},
    },
}

TRIGGER_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["name", "type", "action"],
    "additionalProperties": True,
    "properties": {
        "kind": {"type": "string", "enum": ["trigger"]},
        "name": {"type": "string", "minLength": 1},
        "type": {"type": "string", "enum": ["cron", "webhook", "keyword", "file"]},
        "source": {"type": "string"},
        "filter": {"type": "object"},
        "action": {"type": "object"},
    },
}

SCHEMAS: Dict[str, Dict[str, Any]] = {
    "workflow": WORKFLOW_SCHEMA,
    "plugin": PLUGIN_SCHEMA,
    "agent": AGENT_SCHEMA,
    "trigger": TRIGGER_SCHEMA,
}


@dataclass
class ValidationError:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


# ---------------------------------------------------------------------------
# 最小 JSON Schema 校验器（jsonschema 不可用时的回退）
# ---------------------------------------------------------------------------

_TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
    "null": type(None),
}


def _check_type(value: Any, expected: str) -> bool:
    py = _TYPE_MAP.get(expected)
    if py is None:
        return True
    if expected in ("number", "integer") and isinstance(value, bool):
        return False
    return isinstance(value, py)


def _validate_value(value: Any, schema: Dict[str, Any], path: str, errors: List[ValidationError]) -> None:
    if not isinstance(schema, dict):
        return
    if "type" in schema and not _check_type(value, schema["type"]):
        errors.append(
            ValidationError(path, f"类型错误: 期望 {schema['type']}，实际 {type(value).__name__}")
        )
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(ValidationError(path, f"非法值: {value!r}，应为 {schema['enum']}"))
    if isinstance(value, str) and "minLength" in schema and len(value) < schema["minLength"]:
        errors.append(ValidationError(path, f"字符串过短: 长度 {len(value)} < minLength {schema['minLength']}"))
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value or value[req] is None:
                errors.append(ValidationError(f"{path}/{req}", f"缺少必填字段: {req}"))
        for key, sub in props.items():
            if key in value:
                _validate_value(value[key], sub, f"{path}/{key}", errors)
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(ValidationError(path, f"列表过短: 长度 {len(value)} < minItems {schema['minItems']}"))
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for i, item in enumerate(value):
                _validate_value(item, items_schema, f"{path}/{i}", errors)


def _fmt_jsonschema_error(err: Any) -> str:
    """把 jsonschema 英文错误映射为与内置校验器一致的中文文案。"""
    v = err.validator
    msg = err.message or ""
    if v == "required":
        # message like: 'name' is a required property
        key = (err.message or "").split("'")[1] if "'" in (err.message or "") else ""
        return f"缺少必填字段: {key}" if key else msg
    if v == "type":
        expected = err.validator_value
        return f"类型错误: 期望 {expected}"
    if v == "enum":
        return f"非法值: 应为 {err.validator_value}"
    if v == "minLength":
        return f"字符串过短: minLength {err.validator_value}"
    if v == "minItems":
        return f"列表过短: minItems {err.validator_value}"
    return msg


def _validate_with_jsonschema(spec: Any, schema: Dict[str, Any]) -> List[ValidationError]:
    validator = _js.Draft202012Validator(schema)
    errors: List[ValidationError] = []
    for err in sorted(validator.iter_errors(spec), key=lambda e: list(e.absolute_path)):
        path = "/" + "/".join(str(p) for p in err.absolute_path) if err.absolute_path else "/"
        errors.append(ValidationError(path, _fmt_jsonschema_error(err)))
    return errors


def validate(spec: Any, kind: str) -> List[ValidationError]:
    """按 kind 校验 spec，返回错误列表（空列表 = 合法）。不抛异常。"""
    schema = SCHEMAS.get(kind)
    if schema is None:
        return [ValidationError("/", f"未知 DSL kind: {kind!r}")]
    if not isinstance(spec, dict):
        return [ValidationError("/", f"根节点必须是对象，实际 {type(spec).__name__}")]
    if _HAS_JSONSCHEMA:
        return _validate_with_jsonschema(spec, schema)
    errors: List[ValidationError] = []
    _validate_value(spec, schema, "", errors)
    return errors


def validate_workflow(spec: Any) -> List[ValidationError]:
    return validate(spec, "workflow")


def validate_plugin(spec: Any) -> List[ValidationError]:
    return validate(spec, "plugin")


def validate_agent(spec: Any) -> List[ValidationError]:
    return validate(spec, "agent")


def validate_trigger(spec: Any) -> List[ValidationError]:
    return validate(spec, "trigger")


def backend_name() -> str:
    """当前校验后端：jsonschema | builtin"""
    return "jsonschema" if _HAS_JSONSCHEMA else "builtin"
