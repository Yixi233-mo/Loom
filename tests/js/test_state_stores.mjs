/**
 * F0/F1 状态层测试 — 三态 store。
 *
 * 运行：node --experimental-strip-types tests/js/test_state_stores.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const contracts = await import(tsUrl(path.join(root, "src/contracts/index.ts")));
const state = await import(tsUrl(path.join(root, "src/state/index.ts")));

const { EVENTS, API } = contracts;
const {
  Store,
  SessionStore,
  TaskStore,
  AgentStore,
  createTask,
  createAgent,
  createAppStores,
} = state;

let passed = 0;
function ok(name, fn) {
  try {
    fn();
    passed += 1;
    console.log(`ok - ${name}`);
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

// --- F0 契约 ---

ok("契约含三态事件与 REST", () => {
  assert.ok(EVENTS.SESSION_UPSERT);
  assert.ok(EVENTS.TASK_UPDATED);
  assert.ok(EVENTS.AGENT_STATUS);
  assert.ok(EVENTS.FILE_UPLOADED);
  assert.ok(API.SESSIONS);
  assert.ok(API.TASK_TRIGGER);
  assert.ok(API.FILE_UPLOAD);
  assert.ok(API.STREAM);
});

// --- Store 基类 ---

ok("Store get/set/subscribe", () => {
  const s = new Store({ n: 0 });
  let hit = 0;
  const un = s.subscribe(() => hit++);
  s.set((p) => ({ n: p.n + 1 }));
  assert.equal(s.get().n, 1);
  assert.equal(hit, 1);
  un();
  s.patch({ n: 5 });
  assert.equal(s.get().n, 5);
  assert.equal(hit, 1);
});

// --- 会话状态 ---

ok("SessionStore 消息与流式", () => {
  const ss = SessionStore.create("sess-1", "跨端会话");
  assert.equal(ss.get().sessionId, "sess-1");
  assert.equal(ss.get().status, "idle");

  const m = ss.appendMessage({ role: "user", content: "帮我查资料" });
  assert.equal(ss.get().messages.length, 1);
  assert.equal(m.content, "帮我查资料");

  ss.setStatus("streaming");
  ss.appendDelta("正在");
  ss.appendDelta("检索");
  const msgs = ss.get().messages;
  assert.equal(msgs[msgs.length - 1].role, "assistant");
  assert.equal(msgs[msgs.length - 1].content, "正在检索");
  ss.endSession();
  assert.equal(ss.get().status, "ended");
});

ok("SessionStore draft / title", () => {
  const ss = SessionStore.create("s2");
  ss.setDraft("草稿…");
  ss.setTitle("周报");
  assert.equal(ss.get().draft, "草稿…");
  assert.equal(ss.get().title, "周报");
});

// --- 任务状态 ---

ok("TaskStore 状态机字段", () => {
  const ts = TaskStore.create();
  const t = createTask({
    taskId: "t1",
    workflowName: "daily_report",
    traceId: "tr-1",
    device: "pc",
    assignedTo: "pc-1",
  });
  ts.upsert(t);
  assert.equal(ts.getItem("t1").status, "pending");
  ts.setStatus("t1", "running");
  assert.equal(ts.getItem("t1").status, "running");
  ts.setResult("t1", { summary: "ok", tokensUsed: 12, latencyMs: 34 }, "done");
  const done = ts.getItem("t1");
  assert.equal(done.status, "done");
  assert.equal(done.result.summary, "ok");
  assert.equal(done.result.tokensUsed, 12);
  assert.equal(done.traceId, "tr-1");
});

ok("TaskStore 失败与过滤", () => {
  const ts = TaskStore.create();
  ts.upsert(createTask({ taskId: "a", workflowName: "w", traceId: "tr-a" }));
  ts.upsert(createTask({ taskId: "b", workflowName: "w", traceId: "tr-b" }));
  ts.setError("a", "超时");
  assert.equal(ts.getItem("a").status, "failed");
  assert.equal(ts.listByStatus("failed").length, 1);
  assert.equal(ts.list().length, 2);
});

// --- Agent 状态 ---

ok("AgentStore 调用记账与降级", () => {
  const as = AgentStore.create();
  as.upsert(createAgent({ agentName: "claude_code", capabilities: ["code.gen"] }));
  as.setStatus("claude_code", "online");
  assert.equal(as.getItem("claude_code").status, "online");

  as.recordCall("claude_code", {
    lastLatencyMs: 120,
    lastTokensUsed: 80,
    degradationLevel: 1,
  });
  const a = as.getItem("claude_code");
  assert.equal(a.status, "degraded");
  assert.equal(a.degradationLevel, 1);
  assert.equal(a.lastLatencyMs, 120);
  assert.equal(a.lastTokensUsed, 80);

  as.recordCall("claude_code", { degradationLevel: 0 });
  assert.equal(as.getItem("claude_code").status, "online");
});

ok("createAppStores 三态齐备", () => {
  const app = createAppStores("sess-x");
  assert.equal(app.session.get().sessionId, "sess-x");
  assert.equal(app.tasks.list().length, 0);
  assert.equal(app.agents.list().length, 0);
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
