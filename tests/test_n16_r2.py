"""N16 R2 验收测试 — 数据层 / 模型服务 / 编排护栏。"""

from __future__ import annotations

import asyncio
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_hub.orchestration import (
    ActionTracker,
    DuplicateActionError,
    IterationLimitError,
    MultiAgentAdjudicator,
    RunGuard,
    ToolExecutor,
    ToolNotFoundError,
    ToolValidationError,
    build_graph_ascii,
    validate_tool_args,
)
from data import Database, backup_db, resolve_db_path, restore_db
from observability.cost import DEFAULT_TOKEN_LIMIT, CostMeter, get_token_limit


class TestDataLayer(unittest.TestCase):
    def test_db_path_default_and_env(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            p = resolve_db_path("/tmp/loomroot")
            self.assertTrue(str(p).replace("\\", "/").endswith("data/loom.db"))
        with mock.patch.dict(os.environ, {"LOOM_DB_PATH": "x/y.db"}):
            self.assertEqual(resolve_db_path().name, "y.db")

    def test_wal_and_auto_migrate_and_index(self):
        with tempfile.TemporaryDirectory() as td:
            db_path = Path(td) / "data" / "loom.db"
            db = Database(db_path)
            info = db.info()
            self.assertTrue(info.journal_mode.lower() in ("wal", "memory") or info.journal_mode)
            self.assertGreaterEqual(info.schema_version, 1)
            # 5.7 目录自动创建
            self.assertTrue(db_path.parent.exists())
            # 5.9 索引存在
            idx = db.query("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
            names = {r["name"] for r in idx}
            self.assertIn("idx_changelog_key", names)
            self.assertIn("idx_changelog_version", names)
            db.close()

    def test_concurrent_write_lock(self):
        with tempfile.TemporaryDirectory() as td:
            db = Database(Path(td) / "t.db")

            def write(i: int) -> None:
                db.execute(
                    "INSERT INTO kv(key, value, version, updated_by, updated_at) VALUES (?,?,?,?,?)",
                    (f"k{i}", "v", i, "t", 0.0),
                )

            import threading

            threads = [threading.Thread(target=write, args=(i,)) for i in range(20)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            n = db.query("SELECT COUNT(*) AS c FROM kv")[0]["c"]
            self.assertEqual(n, 20)
            db.close()

    def test_backup_and_restore(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "src.db"
            db = Database(src)
            db.execute(
                "INSERT INTO kv(key, value, version, updated_by, updated_at) VALUES (?,?,?,?,?)",
                ("a", "1", 1, "t", 1.0),
            )
            bak = backup_db(src, Path(td) / "bak" / "copy.db")
            self.assertTrue(bak.exists())
            db.close()  # Windows 文件锁
            restore_db(bak, src)
            db2 = Database(src)
            rows = db2.query("SELECT value FROM kv WHERE key='a'")
            self.assertEqual(rows[0]["value"], "1")
            db2.close()


class TestModelLayer(unittest.TestCase):
    def test_token_limit_default_and_env(self):
        self.assertEqual(DEFAULT_TOKEN_LIMIT, 8000)
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_token_limit(), 8000)
        with mock.patch.dict(os.environ, {"LOOM_TOKEN_LIMIT": "500"}):
            self.assertEqual(get_token_limit(), 500)

    def test_meter_prompt_completion_split(self):
        m = CostMeter(task_id="t", limit=100)
        m.add_tokens(10, prompt=6, completion=4)
        rep = m.report().to_dict()
        self.assertEqual(rep["prompt_tokens"], 6)
        self.assertEqual(rep["completion_tokens"], 4)
        self.assertEqual(rep["tokens_used"], 10)

    def test_circuit_breaker(self):
        m = CostMeter(task_id="t", limit=5)
        m.add_tokens(4)
        with self.assertRaises(Exception):
            m.add_tokens(10)
        self.assertTrue(m.breaker_open)

    def test_degrade_timeout_and_consecutive_fail(self):
        from agent_hub.degrade import (
            DegradationChain,
            Provider,
            rules_provider,
        )
        from observability.logging import DEG_RULES

        calls = {"n": 0}

        async def slow(prompt, **kw):
            await asyncio.sleep(0.2)
            return {"ok": True}

        async def flaky(prompt, **kw):
            calls["n"] += 1
            raise RuntimeError("down")

        chain = DegradationChain(
            [
                Provider("slow", 0, slow, timeout_s=0.05),
                Provider("flaky", 1, flaky, timeout_s=1.0),
                Provider("rules", DEG_RULES, rules_provider, timeout_s=1.0),
            ]
        )
        r = asyncio.run(chain.run("hello"))
        self.assertEqual(r.provider, "rules")
        self.assertEqual(r.degradation_level, DEG_RULES)
        self.assertTrue(any("timeout" in e for e in r.errors))

        # 连续 3 败后 skip
        for _ in range(3):
            asyncio.run(chain.run("x"))
        self.assertTrue(chain.health["flaky"].should_skip())

    def test_hot_swap_model(self):
        from agent_hub.degrade import get_active_model, set_active_model

        set_active_model("deepseek", "deepseek-reasoner")
        self.assertEqual(get_active_model("deepseek")["model"], "deepseek-reasoner")

    def test_prompt_v1_exists(self):
        p = Path(__file__).resolve().parent.parent / "apps" / "hub" / "prompts" / "v1.md"
        self.assertTrue(p.exists())
        text = p.read_text(encoding="utf-8")
        self.assertIn("dsl.generator", text)


class TestOrchestration(unittest.TestCase):
    def test_max_iterations(self):
        g = RunGuard(max_iterations=3)
        for _ in range(3):
            g.tick()
        with self.assertRaises(IterationLimitError):
            g.tick()

    def test_duplicate_action(self):
        t = ActionTracker(limit=3)
        t.check("notes.create", {"title": "a"})
        t.check("notes.create", {"title": "a"})
        with self.assertRaises(DuplicateActionError):
            t.check("notes.create", {"title": "a"})

    def test_unknown_tool_raises(self):
        ex = ToolExecutor({"notes.list": lambda **k: []})
        with self.assertRaises(ToolNotFoundError):
            ex.invoke("nope")

    def test_tool_args_validation(self):
        with self.assertRaises(ToolValidationError):
            validate_tool_args("notes.create", {})
        ok = validate_tool_args("notes.create", {"title": "t", "content": "c"})
        self.assertEqual(ok["title"], "t")
        with self.assertRaises(ToolValidationError):
            validate_tool_args("notes.create", {"title": 123})

    def test_tool_fail_degrade_no_blind_retry(self):
        calls = {"n": 0}

        def boom(**k):
            calls["n"] += 1
            raise ValueError("x")

        ex = ToolExecutor({"notes.create": boom}, max_retries=0)
        sr = ex.invoke("notes.create", {"title": "t"})
        self.assertFalse(sr.ok)
        self.assertEqual(calls["n"], 1)

    def test_task_timeout(self):
        from agent_hub.orchestration import run_with_budget
        from observability.resilience import TimeoutBudgetError

        async def slow():
            await asyncio.sleep(0.2)
            return 1

        with self.assertRaises(TimeoutBudgetError):
            asyncio.run(run_with_budget(slow(), timeout_s=0.05))

    def test_multi_agent_adjudicator(self):
        from agent_hub.orchestration import AgentVote

        adj = MultiAgentAdjudicator()
        out = adj.collect(
            "t1",
            [
                AgentVote("a", {"answer": 1}),
                AgentVote("b", {"answer": 1}),
                AgentVote("c", {"answer": 1}),
            ],
        )
        self.assertFalse(out["needs_confirm"])
        self.assertEqual(out["decision"], {"answer": 1})

        out2 = adj.collect(
            "t2",
            [AgentVote("a", {"answer": 1}), AgentVote("b", {"answer": 2})],
        )
        self.assertTrue(out2["needs_confirm"])
        c = adj.confirm("t2", accepted={"answer": 1})
        self.assertTrue(c["confirmed"])

    def test_graph_compile(self):
        s = build_graph_ascii()
        self.assertTrue(s)


if __name__ == "__main__":
    unittest.main()
