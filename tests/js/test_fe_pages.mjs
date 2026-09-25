/**
 * FE.3 核心页面验收 — 加载/空/错误 + 三页结构
 * run: node --experimental-strip-types tests/js/test_fe_pages.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

import {
  phaseOf,
  LoadingState,
  EmptyState,
  ErrorState,
  PageShell,
} from "../../apps/web/src/features/page-states.ts";
import { ChatWorkbench } from "../../apps/web/src/features/chat-workbench.ts";
import { TaskCenter } from "../../apps/web/src/features/task-center.ts";
import { SettingsPage } from "../../apps/web/src/features/settings-page.ts";

const e = React.createElement;
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");

function html(node) {
  return renderToStaticMarkup(node);
}

// --- phaseOf ---
{
  assert.equal(phaseOf({ loading: true }), "loading");
  assert.equal(phaseOf({ error: "x" }), "error");
  assert.equal(phaseOf({ empty: true }), "empty");
  assert.equal(phaseOf({}), "ready");
  assert.equal(phaseOf({ loading: true, error: "e" }), "loading");
}

// --- 状态原语 ---
{
  const loading = html(e(LoadingState, { label: "加载中…", rows: 2 }));
  assert.match(loading, /data-state="loading"/);
  assert.match(loading, /aria-busy="true"/);
  assert.match(loading, /fe-skeleton/);

  const empty = html(
    e(EmptyState, { title: "暂无任务", hint: "去触发", actionLabel: "刷新", onAction: () => {} })
  );
  assert.match(empty, /data-state="empty"/);
  assert.match(empty, /暂无任务/);
  assert.match(empty, /data-action="empty-action"/);

  const err = html(
    e(ErrorState, { message: "网络断开", onRetry: () => {} })
  );
  assert.match(err, /data-state="error"/);
  assert.match(err, /网络断开/);
  assert.match(err, /data-action="retry"/);

  const page = html(
    e(PageShell, { route: "chat", title: "对话工作台", subtitle: "sub", children: e("p", null, "body") })
  );
  assert.match(page, /data-page="chat"/);
  assert.match(page, /对话工作台/);
}

// --- 对话工作台：四态 ---
{
  const session = {
    sessionId: "s1",
    title: "t",
    status: "idle",
    messages: [],
    updatedAt: 0,
    draft: "",
  };

  const loading = html(e(ChatWorkbench, { session, loading: true }));
  assert.match(loading, /data-page="chat"/);
  assert.match(loading, /data-phase="loading"/);

  const err = html(e(ChatWorkbench, { session, error: "boom" }));
  assert.match(err, /data-phase="error"/);
  assert.match(err, /boom/);

  const empty = html(e(ChatWorkbench, { session }));
  assert.match(empty, /data-phase="empty"/);
  assert.match(empty, /开始一段新对话|还没有对话/);

  const ready = html(
    e(ChatWorkbench, {
      session: {
        ...session,
        messages: [
          { id: "m1", role: "user", content: "你好", createdAt: 1 },
          { id: "m2", role: "assistant", content: "在的", createdAt: 2, taskId: "t1" },
        ],
        draft: "继续",
      },
      modelLabel: "deepseek-chat",
      onSend: () => {},
    })
  );
  assert.match(ready, /data-phase="ready"/);
  assert.match(ready, /data-role="user"/);
  assert.match(ready, /data-task-id="t1"/);
  assert.match(ready, /deepseek-chat/);
  assert.match(ready, /data-action="chat-send"/);
  assert.doesNotMatch(ready, /data-action="chat-send"[^>]*disabled/);
}

// --- 任务中心 ---
{
  const task = {
    taskId: "t1",
    workflowName: "daily_report",
    device: "pc",
    status: "done",
    traceId: "tr1",
    createdAt: 1,
    updatedAt: 2,
    result: { summary: "ok", tokensUsed: 860, latencyMs: 420, degradationLevel: 0 },
  };

  const empty = html(e(TaskCenter, { tasks: [] }));
  assert.match(empty, /data-page="tasks"/);
  assert.match(empty, /data-phase="empty"/);

  const ready = html(e(TaskCenter, { tasks: [task], filter: "all" }));
  assert.match(ready, /data-phase="ready"/);
  assert.match(ready, /daily_report/);
  assert.match(ready, /data-metric="tokens_used"/);
  assert.match(ready, /860/);

  const filtered = html(e(TaskCenter, { tasks: [task], filter: "running" }));
  assert.match(filtered, /data-phase="empty"/);

  const loading = html(e(TaskCenter, { tasks: [task], loading: true }));
  assert.match(loading, /data-phase="loading"/);

  const failed = html(e(TaskCenter, { tasks: [], error: "hub down" }));
  assert.match(failed, /data-phase="error"/);
}

// --- 设置页 ---
{
  const empty = html(
    e(SettingsPage, {
      tab: "llm",
      providers: [],
      llmDraft: { name: "", baseUrl: "", apiKey: "" },
    })
  );
  assert.match(empty, /data-page="settings"/);
  assert.match(empty, /data-tab="llm"/);
  assert.match(empty, /尚未配置模型/);

  const mcp = html(
    e(SettingsPage, {
      tab: "mcp",
      providers: [{ providerId: "p1", name: "DS", baseUrl: "https://api.deepseek.com/v1" }],
      llmDraft: { name: "", baseUrl: "", apiKey: "" },
      mcpUrl: "http://127.0.0.1:3900/mcp",
    })
  );
  assert.match(mcp, /data-tab="mcp"/);
  assert.match(mcp, /MCP/);
  assert.match(mcp, /mcp-url|data-field="mcp-url"/);

  const loading = html(e(SettingsPage, { tab: "llm", loading: true }));
  assert.match(loading, /data-phase="loading"/);

  const err = html(e(SettingsPage, { tab: "llm", error: "cfg fail" }));
  assert.match(err, /data-phase="error"/);
}

// --- 样式与导出 ---
{
  const pagesCss = readFileSync(join(root, "apps/web/src/styles/pages.css"), "utf8");
  const indexCss = readFileSync(join(root, "apps/web/src/styles/index.css"), "utf8");
  assert.ok(pagesCss.includes(".fe-state--loading"));
  assert.ok(pagesCss.includes(".fe-state--empty"));
  assert.ok(pagesCss.includes(".fe-state--error"));
  assert.ok(indexCss.includes("pages.css"));

  const feat = await import("../../apps/web/src/features/index.ts");
  assert.ok(feat.ChatWorkbench);
  assert.ok(feat.TaskCenter);
  assert.ok(feat.SettingsPage);
  assert.ok(feat.phaseOf);
}

console.log("test_fe_pages: ALL PASS");
