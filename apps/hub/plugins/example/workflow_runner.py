"""示例 Workflow 执行器 — 按编译后的 nodes 顺序执行，支持模板变量。"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional

from dsl.compiler import DSLCompiler

_VAR_RE = re.compile(r"\{\{\s*steps\.([A-Za-z0-9_]+)\.output\s*\}\}")


def _render(text: Optional[str], outputs: Dict[str, Any]) -> str:
    if text is None:
        return ""

    def repl(m: re.Match) -> str:
        key = m.group(1)
        val = outputs.get(key)
        return "" if val is None else str(val)

    return _VAR_RE.sub(repl, text)


class WorkflowRunner:
    """执行 DSLCompiler.compile_workflow 的输出。"""

    def __init__(
        self,
        tools: Dict[str, Callable[..., Any]],
        agents: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None:
        self.tools = tools
        self.agents = agents or {}
        self.compiler = DSLCompiler()

    def run_yaml(self, yaml_path: str) -> Dict[str, Any]:
        wf = self.compiler.compile_workflow(yaml_path)
        return self.run(wf)

    def run(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        outputs: Dict[str, Any] = {}
        results: Dict[str, Any] = {
            "workflow": workflow.get("name"),
            "steps": {},
            "status": "done",
        }
        for node in workflow.get("nodes", []):
            nid = node["id"]
            ntype = node["type"]
            target = node["target"]
            try:
                if ntype == "tool":
                    fn = self.tools.get(target)
                    if fn is None:
                        raise KeyError(f"未注册工具: {target}")
                    args = {
                        k: _render(v, outputs) if isinstance(v, str) else v
                        for k, v in (node.get("args") or {}).items()
                    }
                    out = fn(**args)
                else:
                    fn = self.agents.get(target)
                    prompt = _render(node.get("prompt"), outputs)
                    if fn is None:
                        # 示例内置兜底 agent，保证工作流可跑通
                        out = {"agent": target, "echo_prompt": prompt, "fallback": True}
                    else:
                        out = fn(prompt)
                outputs[nid] = out
                results["steps"][nid] = {"ok": True, "output": out}
            except Exception as e:  # noqa: BLE001 — 示例执行器记录失败并停
                results["status"] = "failed"
                results["steps"][nid] = {"ok": False, "error": str(e)}
                return results
        return results


def run_daily_report(
    store_notes: Optional[list] = None,
) -> Dict[str, Any]:
    """一键跑 plugins/example/workflow.yaml（验收：工作流能被触发执行）。"""
    from pathlib import Path

    from plugins.example.notes_runtime import NotesStore, make_notes_tools

    notes = NotesStore()
    if store_notes:
        for n in store_notes:
            notes.create(n.get("title", ""), n.get("content", ""))

    runner = WorkflowRunner(tools=make_notes_tools(notes))
    wf_path = Path(__file__).resolve().parent / "workflow.yaml"
    return runner.run_yaml(str(wf_path))
