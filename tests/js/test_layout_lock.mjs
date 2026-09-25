/**
 * U1 窗口适配 + 布局锁定 — 静态验收
 * run: node --experimental-strip-types tests/js/test_layout_lock.mjs
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const base = readFileSync("src/styles/base.css", "utf8");
const layout = readFileSync("src/styles/layout.css", "utf8");
const rootCss = readFileSync("src/styles.css", "utf8");
const indexHtml = readFileSync("index.html", "utf8");
const tauri = JSON.parse(readFileSync("src-tauri/tauri.conf.json", "utf8"));
const pages = readFileSync("src/styles/pages.css", "utf8");

// 1. 视口锁定：html/body/#root 不整体滚动
assert.match(base, /html\s*\{[^}]*overflow:\s*hidden/s);
assert.match(base, /body\s*\{[^}]*overflow:\s*hidden/s);
assert.match(indexHtml, /#root\s*\{[^}]*overflow:\s*hidden/s);
assert.match(indexHtml, /100dvh/);

// 2. 根 styles.css 不再覆盖壳布局为居中卡片
assert.doesNotMatch(rootCss, /\.app-shell\s*\{[^}]*max-width:\s*1100px/s);

// 3. 壳 Grid 分区 + 视口高度锁定
assert.match(layout, /\.app-shell\s*\{[^}]*display:\s*grid/s);
assert.match(layout, /100dvh/);
assert.match(layout, /overflow:\s*hidden/);

// 4. 侧栏导航 / 主区 独立滚动
assert.match(layout, /\.app-side\s+\.side-nav\s*\{[^}]*overflow-y:\s*auto/s);
assert.match(layout, /\.app-main\s*\{[^}]*overflow-y:\s*auto/s);

// 5. 对话流独立滚动、输入区 flex 贴底
assert.match(layout, /chat-stream/);
assert.match(layout, /chat-composer/);
assert.match(pages, /\.chat-workbench\s*\{[^}]*height:\s*100%/s);
assert.doesNotMatch(pages, /chat-workbench\s*\{[^}]*height:\s*calc\(100vh/);

// 6. 悬停细滚动条 6px
assert.match(base, /::-webkit-scrollbar\s*\{[^}]*width:\s*6px/s);

// 7. Tauri 最小窗口 960×640
const win = tauri.app.windows[0];
assert.equal(win.minWidth, 960);
assert.equal(win.minHeight, 640);

// 8. 窄屏为底部 Tab 留白，且不撑全局滚动
assert.match(layout, /layout-narrow\s+\.app-main/);

console.log("test_layout_lock: ALL PASS");
