/**
 * 提示词 / 任务进度 — 验收
 */
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";
import { PromptStore } from "../../src/stores/prompt-store.ts";
import { PromptsPage } from "../../src/features/prompts-page.ts";
import { TaskProgressBar } from "../../src/features/task-center.ts";
import { PromptChips } from "../../src/features/chat-workbench.ts";
import { readFileSync } from "node:fs";

const e = React.createElement;

const store = new PromptStore();
assert.ok(store.list().length >= 1);
const created = store.upsert({ title: "T", body: "B", tag: "x" });
assert.ok(store.get(created.id));
store.remove(created.id);

const html = renderToStaticMarkup(e(PromptsPage, { onUseInChat: () => {} }));
assert.match(html, /data-page="prompts"/);
assert.match(html, /prompt-save/);
assert.match(html, /prompt-use/);

const prog = renderToStaticMarkup(
  e(TaskProgressBar, { pending: 1, running: 2, done: 3, failed: 0 })
);
assert.match(prog, /task-progress/);
assert.match(prog, /完成 3/);

const chips = renderToStaticMarkup(
  e(PromptChips, {
    items: [{ id: "p1", title: "审查", body: "x" }],
    onPick: () => {},
    onManage: () => {},
  })
);
assert.match(chips, /prompt-chips/);
assert.match(chips, /manage-prompts/);

const app = readFileSync("src/App.tsx", "utf8");
assert.match(app, /task-progress-pill/);
assert.match(app, /工作区/);
assert.match(app, /设置 · 跨端/);
assert.match(app, /MCP · 推荐/);

console.log("test_prompts: ALL PASS");
