/**
 * U2 侧边栏 + 主区 + 顶栏 — 结构验收
 * run: node --experimental-strip-types tests/js/test_u2_shell.mjs
 */
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";
import { readFileSync } from "node:fs";

import { ChatWorkbench } from "../../src/features/chat-workbench.ts";
import { createSessionState } from "../../src/state/session-store.ts";

const e = React.createElement;

// 1. 消息气泡左右 + 头像 + 时间 + 操作
{
  const session = createSessionState("s1");
  session.messages = [
    {
      id: "m1",
      role: "user",
      content: "帮我总结 PDF",
      createdAt: Date.now(),
    },
    {
      id: "m2",
      role: "assistant",
      content: "已路由到 PC",
      createdAt: Date.now(),
    },
  ];
  const html = renderToStaticMarkup(
    e(ChatWorkbench, { session, modelLabel: "demo-model" })
  );
  assert.match(html, /msg-row--user/);
  assert.match(html, /msg-row--assistant/);
  assert.match(html, /msg-avatar/);
  assert.match(html, /msg-time/);
  assert.match(html, /data-action="msg-copy"/);
  assert.match(html, /data-action="msg-retry"/);
  assert.match(html, /data-action="chat-attach"/);
  assert.match(html, /composer-model/);
}

// 2. 空状态引导 + 快捷任务
{
  const empty = createSessionState("s-empty");
  const html = renderToStaticMarkup(
    e(ChatWorkbench, { session: empty, modelLabel: "x" })
  );
  assert.match(html, /chat-empty/);
  assert.match(html, /开始一段新对话/);
  assert.match(html, /chat-starter/);
  assert.match(html, /data-action="chat-starter"/);
}

// 3. 源码：新建对话 / 任务面板 / 连接状态 / 分组导航
{
  const app = readFileSync("src/App.tsx", "utf8");
  assert.match(app, /"data-action": "new-chat"/);
  assert.match(app, /resetForNew/);
  assert.match(app, /task-progress-panel/);
  assert.match(app, /toggle-task-panel/);
  assert.match(app, /conn-status/);
  assert.match(app, /side-user/);
  assert.match(app, /nav-icon/);
  assert.match(app, /侧栏导航/);
  // U2：设置·跨端合并为单项；工具/帮助分组
  assert.match(app, /工作区/);
  assert.match(app, /设置 · 跨端/);
  assert.match(app, /工具/);
  const side = app.slice(app.indexOf('data-view": "sidebar"'), app.indexOf('data-view": "side-user"'));
  assert.doesNotMatch(side, /\["devices", "跨端"/);
  assert.doesNotMatch(side, /\["settings", "设置"/);
}

// 4. CSS 三重活跃态与气泡布局
{
  const layout = readFileSync("src/styles/layout.css", "utf8");
  assert.match(layout, /nav-link\.is-active/);
  assert.match(layout, /is-active::before/);
  assert.match(layout, /side-new-chat/);
  assert.match(layout, /side-user/);
  const pages = readFileSync("src/styles/pages.css", "utf8");
  assert.match(pages, /msg-row--user/);
  assert.match(pages, /msg-actions/);
  assert.match(pages, /composer-icon/);
}

console.log("test_u2_shell: ALL PASS");
