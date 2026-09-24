"""N8 DSL 热加载测试 — 2s 生效 / 工具列表热更。"""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dsl.hot_reload import (  # noqa: E402
    DslHotReloader,
    apply_cron_to_scheduler,
    apply_tools_to_stack,
)
from scripts.run_hub_server import build_demo_stack  # noqa: E402
from task_orchestrator.scheduler import TriggerScheduler  # noqa: E402


def write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


class TestDslHotReload(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / "plugins" / "_hot_test"
        if self.root.exists():
            import shutil

            shutil.rmtree(self.root)
        self.root.mkdir(parents=True)

    def tearDown(self):
        import shutil

        if self.root.exists():
            shutil.rmtree(self.root)

    def test_bootstrap_loads_existing(self):
        write(
            self.root / "a.yaml",
            "name: a_plugin\nversion: 1\ntools:\n  - name: a.list\n",
        )
        re = DslHotReloader(self.root, interval=0.05)
        re.bootstrap()
        self.assertIn("a.list", re.cache.tool_names())
        self.assertIn("a_plugin", re.cache.plugins)

    def test_new_yaml_visible_within_2s(self):
        """验收：新增 .yaml 文件后 2s 内生效。"""
        re = DslHotReloader(self.root, interval=0.1)
        re.bootstrap()
        self.assertEqual(re.cache.tool_names(), [])

        write(
            self.root / "new_plugin.yaml",
            "name: newp\nversion: 1\ntools:\n  - name: newp.run\n",
        )
        start = time.time()
        changed = False
        while time.time() - start < 2.0:
            if re.scan_once():
                changed = True
                break
            time.sleep(0.05)
        self.assertTrue(changed, "2s 内未检测到新增文件")
        self.assertIn("newp.run", re.cache.tool_names())
        self.assertLess(time.time() - start, 2.0)

    def test_modify_updates_tool_list(self):
        """验收：修改 DSL 后工具列表自动更新。"""
        write(
            self.root / "p.yaml",
            "name: p\nversion: 1\ntools:\n  - name: p.old\n",
        )
        re = DslHotReloader(self.root, interval=0.1)
        re.bootstrap()
        self.assertEqual(re.cache.tool_names(), ["p.old"])

        time.sleep(0.01)
        write(
            self.root / "p.yaml",
            "name: p\nversion: 2\ntools:\n  - name: p.new\n  - name: p.extra\n",
        )
        self.assertTrue(re.scan_once())
        tools = re.cache.tool_names()
        self.assertIn("p.new", tools)
        self.assertIn("p.extra", tools)
        self.assertNotIn("p.old", tools)

    def test_remove_clears_tools(self):
        write(self.root / "x.yaml", "name: x\ntools:\n  - name: x.t\n")
        re = DslHotReloader(self.root, interval=0.1)
        re.bootstrap()
        self.assertIn("x.t", re.cache.tool_names())
        (self.root / "x.yaml").unlink()
        self.assertTrue(re.scan_once())
        self.assertNotIn("x.t", re.cache.tool_names())

    def test_workflow_tools_extracted(self):
        write(
            self.root / "wf.yaml",
            "name: wf1\ndevice: pc\nsteps:\n  - id: a\n    tool: notes.list\n",
        )
        re = DslHotReloader(self.root)
        re.bootstrap()
        self.assertIn("wf1", re.cache.workflows)
        self.assertIn("notes.list", re.cache.tool_names())

    def test_on_reload_callback(self):
        hits = []
        re = DslHotReloader(
            self.root, on_reload=lambda c: hits.append(c.tool_names()), interval=0.05
        )
        re.bootstrap()
        write(self.root / "c.yaml", "name: c\ntools:\n  - name: c.t\n")
        re.scan_once()
        self.assertTrue(hits)
        self.assertIn("c.t", hits[-1])

    def test_apply_tools_and_cron(self):
        stack = build_demo_stack()
        sch = TriggerScheduler(fire=lambda n, p: None)
        write(
            self.root / "wf2.yaml",
            "name: wf2\ndevice: pc\ntrigger:\n  type: cron\n  cron: \"0 8 * * *\"\n"
            "steps:\n  - id: a\n    tool: brandnew.tool\n",
        )
        re = DslHotReloader(
            self.root,
            on_reload=lambda cache: (
                apply_tools_to_stack(cache, stack),
                apply_cron_to_scheduler(cache, sch),
            ),
        )
        re.bootstrap()
        self.assertIn("brandnew.tool", stack.tools)
        self.assertIn("wf2", sch.jobs)
        self.assertEqual(sch.jobs["wf2"].cron_expr, "0 8 * * *")

    def test_hub_not_restart_required(self):
        """同一 stack + reloader 多次 scan，引用不变（Hub 不重启）。"""
        stack = build_demo_stack()
        tools_id = id(stack.tools)
        re = DslHotReloader(
            self.root, on_reload=lambda c: apply_tools_to_stack(c, stack)
        )
        re.bootstrap()
        write(self.root / "z.yaml", "name: z\ntools:\n  - name: z.t\n")
        re.scan_once()
        self.assertEqual(id(stack.tools), tools_id)
        self.assertIn("z.t", stack.tools)


if __name__ == "__main__":
    unittest.main()
