"""输出契约与后处理（N16 第 9 章）。

9.1 LLM 输出 JSON Schema · 9.2 解析失败重试 1 次 · 9.3 仍失败明确错误
9.4 超长截断留头尾 · 9.5 敏感脱敏 · 9.6 Markdown XSS 过滤
9.7 引用 chunk_id · 9.8 关键事实二次校验
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from observability.security import redact_secrets

# 9.4 默认上限
MAX_OUTPUT_CHARS = 8000
MAX_FACT_ITEMS = 20

# 9.6 危险 HTML / 协议
_XSS_RE = re.compile(
    r"<\s*/?\s*(script|iframe|object|embed|link|meta|style|form|svg)\b[^>]*>|javascript\s*:|onerror\s*=|onload\s*=|data:text/html",
    re.IGNORECASE,
)

# 9.8 金额 / 日期
_MONEY_RE = re.compile(r"(?:¥|￥|\$|人民币)\s*([0-9]+(?:[.,][0-9]{1,2})?)")
_DATE_RE = re.compile(r"(20\d{2})[-/年](\d{1,2})[-/月](\d{1,2})")

# 9.7 chunk 引用
_CHUNK_RE = re.compile(r"chunk[_-]?id\s*[=:：]\s*([A-Za-z0-9_\-]+)", re.IGNORECASE)


class OutputContractError(Exception):
    """9.3 输出解析仍失败。"""

    def __init__(self, message: str, code: str = "OUTPUT_INVALID") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class ParsedOutput:
    ok: bool
    data: Any
    raw: str
    citations: List[str] = field(default_factory=list)
    facts: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "data": self.data,
            "citations": self.citations,
            "facts": self.facts,
            "warnings": self.warnings,
            "truncated": self.truncated,
        }


def sanitize_markdown(text: str) -> str:
    """9.6 过滤 XSS 危险模式（渲染前）。"""
    if not text:
        return text
    # 先删 script/style 整块
    out = re.sub(
        r"<\s*(script|style)\b[^>]*>[\s\S]*?<\s*/\s*\1\s*>",
        "",
        text,
        flags=re.IGNORECASE,
    )
    out = _XSS_RE.sub("", out)
    return out


def truncate_keep_edges(text: str, limit: int = MAX_OUTPUT_CHARS) -> Tuple[str, bool]:
    """9.4 超长截断：留头尾。"""
    s = text or ""
    if len(s) <= limit:
        return s, False
    head = int(limit * 0.6)
    tail = limit - head - 20
    return s[:head] + "\n…[truncated]…\n" + s[-tail:], True


def extract_citations(text: str, extra: Optional[Sequence[str]] = None) -> List[str]:
    """9.7 引用 chunk_id。"""
    ids = _CHUNK_RE.findall(text or "")
    if extra:
        ids.extend(extra)
    # 去重保序
    seen = set()
    out = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def check_key_facts(text: str) -> List[Dict[str, Any]]:
    """9.8 金额/日期二次校验标记。"""
    facts: List[Dict[str, Any]] = []
    for m in _MONEY_RE.finditer(text or ""):
        facts.append({"type": "money", "value": m.group(1), "span": m.group(0)[:40]})
    for m in _DATE_RE.finditer(text or ""):
        y, mo, d = m.group(1), m.group(2), m.group(3)
        ok = 1 <= int(mo) <= 12 and 1 <= int(d) <= 31
        facts.append(
            {
                "type": "date",
                "value": f"{y}-{mo.zfill(2)}-{d.zfill(2)}",
                "valid": ok,
                "span": m.group(0)[:40],
            }
        )
        if len(facts) >= MAX_FACT_ITEMS:
            break
    return facts


def parse_llm_json(raw: str) -> Any:
    """从 LLM 文本中提取 JSON 对象/数组。"""
    text = (raw or "").strip()
    if not text:
        raise OutputContractError("空输出", code="OUTPUT_EMPTY")
    # 整段 JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 代码块
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        try:
            return json.loads(fence.group(1).strip())
        except json.JSONDecodeError as e:
            raise OutputContractError(f"JSON 代码块解析失败: {e}") from e
    # 首个 { 或 [ 到末个 } 或 ]
    for a, b in (("{", "}"), ("[", "]")):
        i, j = text.find(a), text.rfind(b)
        if 0 <= i < j:
            try:
                return json.loads(text[i : j + 1])
            except json.JSONDecodeError:
                continue
    raise OutputContractError("输出不是合法 JSON")


def extract_output(
    raw: str,
    *,
    schema: Optional[Dict[str, Any]] = None,
    limit: int = MAX_OUTPUT_CHARS,
    sanitize: bool = True,
    require_json: bool = False,
) -> ParsedOutput:
    """9.1–9.8 一站式后处理（JSON 优先；纯文本走安全/截断/引用）。"""
    text = raw or ""
    warnings: List[str] = []
    truncated = False
    if sanitize:
        text = sanitize_markdown(text)
    text, truncated = truncate_keep_edges(text, limit)
    citations = extract_citations(text)
    facts = check_key_facts(text)
    for f in facts:
        if f.get("type") == "date" and not f.get("valid"):
            warnings.append(f"日期可疑: {f.get('value')}")

    data: Any
    try:
        data = parse_llm_json(text)
        if schema:
            validate_output_schema(data, schema)
    except SchemaValidationError as e:
        if require_json:
            raise
        warnings.append(str(e))
        data = {"text": text, "schema_error": str(e)}
    except OutputContractError:
        if require_json:
            raise
        data = {"text": text}

    if isinstance(data, dict):
        data = {k: redact_secrets(str(v)) if isinstance(v, str) else v for k, v in data.items()}

    return ParsedOutput(
        ok=True,
        data=data,
        raw=text,
        citations=citations,
        facts=facts,
        warnings=warnings,
        truncated=truncated,
    )


class SchemaValidationError(OutputContractError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="SCHEMA_INVALID")


def validate_output_schema(data: Any, schema: Dict[str, Any]) -> None:
    """9.1 轻量 Schema：required / type(object|array|string|number|boolean)。"""
    stype = schema.get("type")
    if stype == "object" and not isinstance(data, dict):
        raise SchemaValidationError(f"期望 object，得到 {type(data).__name__}")
    if stype == "array" and not isinstance(data, list):
        raise SchemaValidationError(f"期望 array，得到 {type(data).__name__}")
    if stype == "string" and not isinstance(data, str):
        raise SchemaValidationError("期望 string")
    if stype in ("number", "integer") and not isinstance(data, (int, float)):
        raise SchemaValidationError("期望 number")
    if stype == "boolean" and not isinstance(data, bool):
        raise SchemaValidationError("期望 boolean")
    if isinstance(data, dict):
        for key in schema.get("required", []):
            if key not in data:
                raise SchemaValidationError(f"缺少字段 {key}")
        props = schema.get("properties") or {}
        for k, sub in props.items():
            if k in data and isinstance(sub, dict):
                validate_output_schema(data[k], sub)


async def complete_with_contract(
    complete_fn: Callable[[str], Any],
    prompt: str,
    *,
    schema: Optional[Dict[str, Any]] = None,
    retries: int = 1,
) -> ParsedOutput:
    """9.2 解析失败重试 1 次；9.3 仍失败抛 OutputContractError。"""
    last_err: Optional[Exception] = None
    attempts = max(1, retries + 1)
    for i in range(attempts):
        raw = complete_fn(prompt)
        if hasattr(raw, "__await__"):
            raw = await raw  # type: ignore[misc]
        raw_s = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
        try:
            out = extract_output(raw_s, schema=schema, require_json=True)
            return out
        except OutputContractError as e:
            last_err = e
            continue
    raise OutputContractError(
        f"输出解析失败（已试 {attempts} 次）: {last_err}", code="OUTPUT_INVALID"
    )
