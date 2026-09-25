/**
 * U4 视觉收敛 — Token 静态验收
 * run: node --experimental-strip-types tests/js/test_u4_visual.mjs
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const tokens = readFileSync("src/styles/tokens.css", "utf8");
const controls = readFileSync("src/styles/controls.css", "utf8");
const base = readFileSync("src/styles/base.css", "utf8");

// 1. 圆角三档 8/12/16
assert.match(tokens, /--radius-sm:\s*8px/);
assert.match(tokens, /--radius-md:\s*12px/);
assert.match(tokens, /--radius-lg:\s*16px/);
assert.match(tokens, /--radius-xl:\s*16px/);

// 2. 字体四档 24/16/14/12
assert.match(tokens, /--fs-sm:\s*12px/);
assert.match(tokens, /--fs-md:\s*14px/);
assert.match(tokens, /--fs-lg:\s*16px/);
assert.match(tokens, /--fs-xl:\s*24px/);
assert.match(tokens, /--text-2xl:\s*24px/);
assert.match(tokens, /--text-md:\s*14px/);

// 3. 品牌色 hover/active 深色阶
assert.match(tokens, /--accent-hover:/);
assert.match(tokens, /--accent-active:/);
assert.match(tokens, /--accent-deep:/);
assert.match(tokens, /--button-primary-bg-hover:/);
assert.match(tokens, /--button-primary-bg-active:/);
assert.match(controls, /ui-button--primary:active/);
assert.match(controls, /accent-active/);

// 4. 背景分层
assert.match(tokens, /--bg-page:/);
assert.match(tokens, /--surface-card:/);
assert.match(base, /surface-page/);

// 5. 卡片统一阴影
assert.match(tokens, /--card-shadow:/);
assert.match(tokens, /--card-shadow-hover:/);

console.log("test_u4_visual: ALL PASS");
