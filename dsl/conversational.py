"""对话式生成 DSL — 生成 → Schema 校验 → diff → 用户确认才落盘。

对应方案禁止项：
- 禁止未经用户确认执行/落盘对话式生成的 DSL
- 生成后展示 diff，用户确认才写入
"""

from __future__ import annotations

import difflib
import logging
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol

from dsl.schema import validate_workflow

logger = logging.getLogger(__name__)


class DslGenerator(Protocol):
    """生成器协议：自然语言 → DSL YAML 文本。"""

    def generate(self, user_text: str) -> str: ...


class RuleBasedGenerator:
    """规则生成：从自然语言抽取 name/cron/steps，产出 Workflow YAML。

    离线可用；LLM 后端可替换本类。
    """

    def generate(self, user_text: str) -> str:
        text = (user_text or "").strip()
        name = self._extract_name(text)
        cron = self._extract_cron(text)
        steps = self._extract_steps(text)
        lines = [f"name: {name}"]
        if cron:
            lines += ["trigger:", "  type: cron", f'  cron: "{cron}"']
        lines.append("device: pc")
        lines.append("steps:")
        for s in steps:
            lines.append(f"  - id: {s['id']}")
            if s["kind"] == "tool":
                lines.append(f"    tool: {s['target']}")
            else:
                lines.append(f"    agent: {s['target']}")
                if s.get("prompt"):
                    lines.append(f'    prompt: "{s["prompt"]}"')
        return "\n".join(lines) + "\n"

    def _extract_name(self, text: str) -> str:
        for kw, name in [
            ("周报", "weekly_report"),
            ("日报", "daily_report"),
            ("月报", "monthly_report"),
            ("报告", "report_task"),
            ("总结", "summary_task"),
        ]:
            if kw in text:
                return name
        return "adhoc_task"

    def _extract_cron(self, text: str) -> Optional[str]:
        # 每天 9 点 / 每周一早上 等
        if "每周一" in text:
            return "0 9 * * 1"
        if "每天" in text and ("9 点" in text or "9点" in text or "早上9" in text or "早9" in text):
            return "0 9 * * *"
        if "每天" in text:
            return "0 8 * * *"
        if "每小时" in text:
            return "0 * * * *"
        return None

    def _extract_steps(self, text: str) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []
        if any(k in text for k in ("笔记", "notes")):
            steps.append({"id": "fetch", "kind": "tool", "target": "notes.list"})
        if any(k in text for k in ("总结", "汇总", "摘要")):
            steps.append(
                {
                    "id": "summarize",
                    "kind": "agent",
                    "target": "builtin_rag",
                    "prompt": "总结输入内容",
                }
            )
        if any(k in text for k in ("发送", "推送", "飞书")):
            steps.append({"id": "push", "kind": "tool", "target": "notes.create"})
        if not steps:
            steps.append({"id": "run", "kind": "tool", "target": "notes.list"})
        return steps


@dataclass
class DraftProposal:
    """一次待确认的 DSL 草稿（未确认前不落盘）。"""

    draft_id: str
    user_text: str
    yaml_text: str
    path: str  # 目标文件路径
    original: str = ""  # 目标文件原内容（可空=新建）
    confirmed: bool = False
    written: bool = False
    validation_errors: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def ok(self) -> bool:
        return not self.validation_errors

    def diff(self) -> str:
        return "".join(
            difflib.unified_diff(
                self.original.splitlines(keepends=True),
                self.yaml_text.splitlines(keepends=True),
                fromfile=f"a/{self.path}",
                tofile=f"b/{self.path}",
            )
        )

    def summary(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "path": self.path,
            "ok": self.ok,
            "confirmed": self.confirmed,
            "written": self.written,
            "validation_errors": self.validation_errors,
            "diff": self.diff(),
        }


class ConversationalDslService:
    """对话式 DSL：propose（生成+校验+diff）→ confirm（写盘）。"""

    def __init__(
        self,
        generator: Optional[DslGenerator] = None,
        workspace_root: Optional[str | Path] = None,
        on_written: Optional[Callable[[DraftProposal], None]] = None,
    ) -> None:
        self.generator = generator or RuleBasedGenerator()
        self.workspace_root = Path(workspace_root or Path.cwd() / "plugins")
        self.drafts: Dict[str, DraftProposal] = {}
        self.on_written = on_written

    def propose(
        self, user_text: str, filename: str = "", existing_yaml: str = ""
    ) -> DraftProposal:
        """生成草稿 + Schema 校验；不写盘。"""
        yaml_text = self.generator.generate(user_text)
        name = filename or f"draft_{uuid.uuid4().hex[:8]}.yaml"
        path = str(self.workspace_root / name)

        issues = self._validate(yaml_text)
        draft = DraftProposal(
            draft_id=f"d-{uuid.uuid4().hex[:10]}",
            user_text=user_text,
            yaml_text=yaml_text,
            path=path,
            original=existing_yaml,
            validation_errors=issues,
        )
        self.drafts[draft.draft_id] = draft
        logger.info("对话式 DSL 草稿 %s ok=%s path=%s", draft.draft_id, draft.ok, path)
        return draft

    def _validate(self, yaml_text: str) -> List[str]:
        try:
            import yaml

            spec = yaml.safe_load(yaml_text)
        except Exception as e:  # noqa: BLE001
            return [f"YAML 无法解析: {e}"]
        if not isinstance(spec, dict):
            return ["YAML 根节点必须是映射"]
        errs = validate_workflow(spec)
        return [str(e) for e in errs]

    def get(self, draft_id: str) -> DraftProposal:
        if draft_id not in self.drafts:
            raise KeyError(f"未知草稿: {draft_id}")
        return self.drafts[draft_id]

    def confirm_and_write(self, draft_id: str, override_path: Optional[str] = None) -> Path:
        """用户确认后才落盘；未确认/校验失败均拒绝。"""
        draft = self.get(draft_id)
        if draft.written:
            raise RuntimeError("草稿已落盘")
        if not draft.confirmed:
            raise PermissionError("禁止未确认写盘（方案禁止项）")
        if not draft.ok:
            raise ValueError("校验未通过，拒绝写盘: " + "; ".join(draft.validation_errors))

        target = Path(override_path or draft.path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(draft.yaml_text, encoding="utf-8")
        draft.written = True
        draft.path = str(target)
        if self.on_written:
            self.on_written(draft)
        return target

    def confirm(self, draft_id: str) -> DraftProposal:
        """标记用户确认（仍需 confirm_and_write 才落盘）。"""
        draft = self.get(draft_id)
        if not draft.ok:
            raise ValueError("校验未通过，不能确认执行")
        draft.confirmed = True
        return draft

    def reject(self, draft_id: str) -> None:
        draft = self.get(draft_id)
        draft.confirmed = False
        self.drafts.pop(draft_id, None)
