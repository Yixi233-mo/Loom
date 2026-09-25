/**
 * U3 交互细节 + 三端适配 — 静态验收
 * run: node --experimental-strip-types tests/js/test_u3_responsive.mjs
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { breakpointName, layoutFor } from "../../apps/web/src/platform/device.ts";
import { breakpointOf } from "../../apps/web/src/platform/adapters.ts";

// 1. 四档断点
assert.equal(breakpointName(1440), "xl");
assert.equal(breakpointName(1100), "lg");
assert.equal(breakpointName(900), "md");
assert.equal(breakpointName(375), "sm");
assert.equal(breakpointOf(1440, "pc").name, "xl");
assert.equal(breakpointOf(375, "mobile").columns, 1);

// 2. 四档布局
assert.equal(layoutFor("pc", 1440), "wide");
assert.equal(layoutFor("tablet", 1100), "medium");
assert.equal(layoutFor("pc", 900), "compact");
assert.equal(layoutFor("mobile", 375), "narrow");

// 3. chips 背景/边框/悬停
const pages = readFileSync("apps/web/src/styles/pages.css", "utf8");
assert.match(pages, /\.chip:hover/);
assert.match(pages, /\.chip \{[^}]*border:/s);

// 4. 任务 Tag 可点
const chat = readFileSync("apps/web/src/features/chat-workbench.ts", "utf8");
assert.match(chat, /msg-task-tag/);
assert.match(chat, /goto-task/);
assert.match(chat, /onOpenTask/);

// 5. 移动抽屉 + 底部 Tab
const layout = readFileSync("apps/web/src/styles/layout.css", "utf8");
assert.match(layout, /side-scrim/);
assert.match(layout, /side-toggle/);
assert.match(layout, /layout-narrow\[data-side-open/);
assert.match(layout, /\.layout-narrow \.tabbar/);
assert.match(layout, /layout-compact/);

const app = readFileSync("apps/web/src/App.tsx", "utf8");
assert.match(app, /toggle-side/);
assert.match(app, /sideOpen/);

// 6. Web 100dvh
assert.match(layout, /100dvh/);
const indexHtml = readFileSync("apps/web/index.html", "utf8");
assert.match(indexHtml, /100dvh/);

console.log("test_u3_responsive: ALL PASS");
