"""示例 Workflow 工具与执行辅助（多场景矩阵用）。"""

from __future__ import annotations

from typing import Any, Dict, Optional

from plugins.example.notes_runtime import NotesStore, make_notes_tools
from plugins.example.workflow_runner import WorkflowRunner


def make_matrix_tools(
    store: Optional[NotesStore] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    st = store or NotesStore()
    tools = make_notes_tools(st)
    if extra:
        tools.update(extra)
    return tools


def make_matrix_agents() -> Dict[str, Any]:
    """内置示例 agent，保证矩阵可离线跑通。"""

    def builtin_rag(prompt: str) -> Dict[str, Any]:
        return {"summary": f"RAG: {prompt[:80]}", "citations": []}

    return {"builtin_rag": builtin_rag}


def run_workflow_file(
    yaml_path: str,
    store: Optional[NotesStore] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """执行指定 workflow yaml（示例矩阵入口）。"""
    st = store or NotesStore()
    tools = make_matrix_tools(st)
    if env:
        # 简单 env 占位：把 env 值预写为笔记，供模板引用演示
        for k, v in env.items():
            st.create(k, v)
    runner = WorkflowRunner(tools=tools, agents=make_matrix_agents())
    return runner.run_yaml(yaml_path)
