/**
 * FE.6 性能验收 — 虚拟窗口 / memo / 防抖 / 构建拆包
 * run: node --experimental-strip-types tests/js/test_fe_perf.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

import {
  computeWindow,
  VirtualList,
  memo,
  shallowEqual,
  debounce,
} from "../../apps/web/src/perf/index.ts";
import { ResultCard, TaskCenter } from "../../apps/web/src/features/task-center.ts";
import { MessageRow } from "../../apps/web/src/features/chat-workbench.ts";

const e = React.createElement;
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const html = (n) => renderToStaticMarkup(n);

// --- computeWindow ---
{
  const w = computeWindow(100, 50, 0, 200, 2);
  assert.equal(w.totalHeight, 5000);
  assert.equal(w.start, 0);
  assert.equal(w.end, 6);
  assert.equal(w.offsetY, 0);

  const mid = computeWindow(100, 50, 250, 200, 2);
  assert.equal(mid.start, 3);
  assert.equal(mid.offsetY, 150);
  assert.ok(mid.end > mid.start);

  const empty = computeWindow(0, 50, 0, 200);
  assert.equal(empty.totalHeight, 0);
  assert.equal(empty.end, 0);
}

// --- VirtualList 窗口渲染 ---
{
  const items = Array.from({ length: 100 }, (_, i) => ({ id: "t" + i, n: i }));
  const node = e(VirtualList, {
    items,
    itemHeight: 20,
    height: 100,
    overscan: 2,
    keyOf: (it) => it.id,
    renderItem: (it) => e("div", { "data-id": it.id }, String(it.n)),
    "data-view": "task-list",
  });
  const out = html(node);
  assert.match(out, /data-window-start="0"/);
  assert.match(out, /data-total="100"/);
  const ids = out.match(/data-id=/g) || [];
  assert.ok(ids.length <= 12, "windowed rows should be few, got " + ids.length);
  assert.ok(ids.length >= 5);
  assert.match(out, /ui-vlist-spacer/);
}

// --- memo / shallowEqual ---
{
  assert.equal(shallowEqual({ a: 1 }, { a: 1 }), true);
  assert.equal(shallowEqual({ a: 1 }, { a: 2 }), false);
  assert.equal(shallowEqual({ a: 1 }, { a: 1, b: 2 }), false);
  function Hello(props) {
    return e("i", null, String(props.x));
  }
  const M = memo(Hello);
  assert.equal(html(e(M, { x: 3 })), "<i>3</i>");
}

// --- debounce ---
{
  let n = 0;
  const d = debounce(() => {
    n += 1;
  }, 5);
  d();
  d();
  d();
  assert.equal(n, 0);
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(n, 1);
}

// --- ResultCard memo + MessageRow + TaskCenter 虚拟阈值 ---
{
  const task = {
    taskId: "t1",
    workflowName: "wf",
    device: "pc",
    status: "done",
    traceId: "tr",
    createdAt: 1,
    updatedAt: 2,
    result: { summary: "s", tokensUsed: 1, latencyMs: 2, degradationLevel: 0 },
  };
  assert.match(html(e(ResultCard, { task })), /data-metric="tokens_used"/);

  const row = html(
    e(MessageRow, {
      message: { id: "m1", role: "user", content: "hi", createdAt: 1 },
    })
  );
  assert.match(row, /data-message-id="m1"/);

  const many = Array.from({ length: 25 }, (_, i) => ({
    ...task,
    taskId: "t" + i,
  }));
  const virt = html(e(TaskCenter, { tasks: many, filter: "all" }));
  assert.match(virt, /data-virtual="true"/);
  assert.match(virt, /data-view="task-list"/);

  const few = html(e(TaskCenter, { tasks: [task], filter: "all" }));
  assert.match(few, /data-virtual="false"/);
}

// --- 构建配置 ---
{
  const vite = readFileSync(join(root, "apps/web/vite.config.ts"), "utf8");
  assert.ok(vite.includes("manualChunks"));
  assert.ok(vite.includes("cssCodeSplit"));
  assert.ok(vite.includes("react-vendor"));
}

console.log("test_fe_perf: ALL PASS");
