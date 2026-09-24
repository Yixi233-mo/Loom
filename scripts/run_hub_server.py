"""Loom Hub 服务端入口 — 一键启动的后端进程。

启动：
  python scripts/run_hub_server.py
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from integration.stack import HubStack  # noqa: E402
from integration.ws_app import create_integrated_app  # noqa: E402
from plugins.example.notes_runtime import NotesStore, make_notes_tools  # noqa: E402
from plugins.example.workflow_runner import WorkflowRunner  # noqa: E402

logger = logging.getLogger(__name__)


def build_demo_stack() -> HubStack:
    """演示栈：notes 工具 + builtin_rag + 虚拟 PC + 服务端自动执行。"""
    store = NotesStore()
    store.create("早会", "同步 Loom 进度")
    store.create("想法", "把设备、Agent、任务编织成一体")
    tools = make_notes_tools(store)

    def builtin_rag(prompt: str):
        return {"summary": f"RAG 总结：{prompt[:60]}", "citations": []}

    stack = HubStack(
        tools=tools,
        agents={"builtin_rag": builtin_rag},
        secret=os.environ.get("WS_SECRET", "dev-secret"),
    )
    # 虚拟 PC：保证 device:pc 的工作流可被路由，由服务端执行
    stack.mesh.register("hub-pc-1", "pc", ["file.read", "shell.exec"])
    stack.auto_execute = True
    stack.workflow_dir = ROOT / "plugins" / "example" / "workflows"

    orig_submit = stack.submit_workflow_async

    async def submit_and_run(workflow, trace_id=None):
        task_id = await orig_submit(workflow, trace_id)
        record = stack.orch.get(task_id)
        status = getattr(record.get("status"), "value", record.get("status"))
        if status in {"assigned", "running"} and getattr(stack, "auto_execute", False):
            await execute_on_server(stack, task_id, workflow, trace_id)
        return task_id

    stack.submit_workflow_async = submit_and_run  # type: ignore[method-assign]

    # N8 DSL 热加载：监听 workflows/plugins，工具与 cron 热更
    from dsl.hot_reload import (
        DslHotReloader,
        apply_cron_to_scheduler,
        apply_tools_to_stack,
    )
    from task_orchestrator.scheduler import TriggerScheduler

    sch = TriggerScheduler(
        fire=lambda name, payload: stack.submit_workflow(payload or {"name": name, "device": "any"})
    )
    reloader = DslHotReloader(
        ROOT / "plugins",
        on_reload=lambda cache: (
            apply_tools_to_stack(cache, stack),
            apply_cron_to_scheduler(cache, sch),
        ),
    )
    stack.scheduler = sch
    stack.dsl_reloader = reloader
    return stack


async def execute_on_server(stack, task_id: str, workflow: dict, trace_id=None) -> None:
    """服务端执行工作流并回写任务。"""
    name = (workflow or {}).get("name", "daily_report")
    wf_path = Path(stack.workflow_dir) / f"{name}.yaml"
    if not wf_path.exists():
        wf_path = Path(stack.workflow_dir) / "daily_report.yaml"
    runner = WorkflowRunner(tools=stack.tools, agents=stack.agents)
    result = runner.run_yaml(str(wf_path))
    status = "done" if result.get("status") == "done" else "failed"
    await stack.complete_task_async(task_id, status, result, trace_id=trace_id)


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    mode = os.environ.get("NETWORK_MODE", "local")
    host = "127.0.0.1" if mode == "local" else "0.0.0.0"
    port = int(os.environ.get("WS_PORT", "8765"))

    stack = build_demo_stack()
    app = create_integrated_app(stack)
    # REST 全套：/api/* + /api/llm/*
    from api.routes import mount_api
    mount_api(app, stack)
    logger.info("Loom Hub 启动: ws://%s:%s/ws  health=/health", host, port)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
