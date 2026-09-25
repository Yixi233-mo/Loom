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
sys.path.insert(0, str(ROOT / "apps" / "hub"))

from integration.stack import HubStack
from integration.ws_app import create_integrated_app
from knowledge.store import KnowledgeStore
from plugins.example.notes_runtime import NotesStore, make_notes_tools
from plugins.example.workflow_runner import WorkflowRunner

logger = logging.getLogger(__name__)


def build_demo_stack() -> HubStack:
    """演示栈：notes 工具 + builtin_rag + 虚拟 PC + 服务端自动执行。"""
    store = NotesStore()
    store.create("早会", "同步 Loom 进度")
    store.create("想法", "把设备、Agent、任务编织成一体")
    tools = make_notes_tools(store)

    kb = KnowledgeStore(ROOT / "apps" / "hub" / "plugins" / "knowledge.json")
    from knowledge.federated import FederatedKnowledge

    fed = FederatedKnowledge(kb, sources_path=ROOT / "apps" / "hub" / "plugins" / "knowledge_sources.json")

    def builtin_rag(prompt: str):
        return fed.answer(prompt)

    stack = HubStack(
        tools=tools,
        agents={"builtin_rag": builtin_rag},
        secret=os.environ.get("WS_SECRET", "dev-secret"),
    )
    # 虚拟 PC：保证 device:pc 的工作流可被路由，由服务端执行
    stack.mesh.register("hub-pc-1", "pc", ["file.read", "shell.exec"])
    stack.auto_execute = True
    stack.workflow_dir = ROOT / "apps" / "hub" / "plugins" / "example" / "workflows"

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
        ROOT / "apps" / "hub" / "plugins",
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
    import asyncio

    import uvicorn

    logging.basicConfig(level=logging.INFO)
    # 2.3 / 2.7 启动密钥审计：默认 WS_SECRET 告警，生产缺密钥报错
    from auth.secrets import warn_if_default_secret

    report = warn_if_default_secret()
    if report.errors and report.is_production:
        for e in report.errors:
            logger.error("启动拒绝：%s", e)
        raise SystemExit(2)

    mode = os.environ.get("NETWORK_MODE", "local")
    host = "127.0.0.1" if mode == "local" else "0.0.0.0"
    port = int(os.environ.get("WS_PORT", "8765"))

    stack = build_demo_stack()
    app = create_integrated_app(stack)
    # REST 全套：/api/* + /api/llm/*
    from api.routes import mount_api
    from api.stream_routes import mount_stream_api

    mount_api(app, stack)
    mount_stream_api(app)
    logger.info("Loom Hub 启动: ws://%s:%s/ws  health=/health  ready=/ready", host, port)
    from auth.secrets import audit_secrets
    from observability.resilience import check_dependencies

    sec = audit_secrets()
    ready = check_dependencies(
        db_ok=True,
        model_ok=bool(stack.agents),
        secrets_ok=sec.ok,
    )
    if ready.ok:
        logger.info("依赖就绪: %s", ready.checks)
    else:
        logger.warning("依赖未就绪: %s", ready.checks)

    # 4.3 优雅停机：SIGTERM 时清理热加载/调度器
    from observability.resilience import GracefulShutdown

    shutdown = GracefulShutdown(timeout=30.0)

    async def _cleanup() -> None:
        for name in ("dsl_reloader", "scheduler"):
            obj = getattr(stack, name, None)
            stop = getattr(obj, "stop", None)
            if callable(stop):
                try:
                    r = stop()
                    if asyncio.iscoroutine(r):
                        await r
                    logger.info("已停止 %s", name)
                except Exception as e:  # noqa: BLE001
                    logger.warning("停止 %s 失败: %s", name, e)

    shutdown.add_cleanup(_cleanup)

    config = uvicorn.Config(app, host=host, port=port, timeout_graceful_shutdown=30)
    server = uvicorn.Server(config)

    async def _serve() -> None:
        shutdown.install()
        await server.serve()
        await shutdown.run_cleanups()

    asyncio.run(_serve())


if __name__ == "__main__":
    main()
