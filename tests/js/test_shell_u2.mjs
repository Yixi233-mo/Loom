/**
 * U2 侧栏 + 主区 + 顶栏 — 结构验收
 * run: node --experimental-strip-types tests/js/test_shell_u2.mjs
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const app = readFileSync("apps/web/src/App.tsx", "utf8");
const settings = readFileSync("apps/web/src/features/settings-page.ts", "utf8");
const chat = readFileSync("apps/web/src/features/chat-workbench.ts", "utf8");
const layout = readFileSync("apps/web/src/styles/layout.css", "utf8");
const pages = readFileSync("apps/web/src/styles/pages.css", "utf8");

// 1. 新建对话入口
assert.match(app, /data-action": "new-chat"/);
assert.match(layout, /\.side-new-chat/);

// 2. 侧栏用户区 + 连接状态
assert.match(app, /data-view": "side-user"/);
assert.match(app, /data-view": "conn-status"/);
assert.match(layout, /\.side-user/);

// 3. 设置·跨端合并为单项
const sidebarBlock = app.slice(
  app.indexOf('data-view": "sidebar"'),
  app.indexOf('data-view": "side-user"')
);
assert.match(sidebarBlock, /设置 · 跨端/);
assert.doesNotMatch(sidebarBlock, /\["devices", "跨端"/);
assert.doesNotMatch(sidebarBlock, /\["settings", "设置"/);

// 4. 设置页含跨端 tab
assert.match(settings, /SettingsTab = "llm" \| "mcp" \| "devices"/);
assert.match(settings, /data-tab": "devices"|data-tab="devices"/);
assert.match(settings, /devicesNode/);

// 5. 顶栏任务进度 + 连接徽标
assert.match(app, /task-progress-pill/);
assert.match(app, /toggle-task-panel/);
assert.match(app, /conn-dot/);

// 6. 消息气泡
assert.match(chat, /msg-row--/);
assert.match(chat, /msg-avatar/);
assert.match(chat, /msg-copy/);
assert.match(pages, /\.msg-row--user/);

// 7. 输入区模型 + 附件
assert.match(chat, /chat-attach/);
assert.match(chat, /composer-model/);
assert.match(chat, /chat-model/);

// 8. 空态推荐任务卡片
assert.match(chat, /chat-starters/);
assert.match(chat, /chat-starter/);
assert.match(pages, /\.chat-starter/);

// 9. 导航活跃态三重反馈
assert.match(layout, /\.nav-link\.is-active::before/);
assert.match(layout, /\.nav-link\.is-active \.nav-icon/);

console.log("test_shell_u2: ALL PASS");
