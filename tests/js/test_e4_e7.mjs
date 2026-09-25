/**
 * E4–E7 轻量增强（保持原视觉）
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const app = readFileSync(join(root, "src", "App.tsx"), "utf8");
const tasks = readFileSync(join(root, "src", "features", "task-center.ts"), "utf8");
const devices = readFileSync(join(root, "src", "features", "device-hub.ts"), "utf8");
const layout = readFileSync(join(root, "src", "styles", "layout.css"), "utf8");

test("E4 顶栏能力胶囊", () => {
  assert.match(app, /cap-pill/);
  assert.match(layout, /\.cap-pill/);
});

test("E5 状态人话化", () => {
  assert.match(tasks, /humanizeStatus|humanizeDegradation/);
  assert.match(tasks, /已切备选|规则兜底|全功能/);
});

test("E6 一个 Loom 跨端叙事", () => {
  assert.match(devices, /一个 Loom|跨端无感/);
  assert.match(app, /一个 Loom/);
});

test("E7 一键复用", () => {
  assert.match(tasks, /再来一次/);
  assert.match(tasks, /onRerun/);
});

test("原视觉仍在", () => {
  assert.ok(app.includes("side-new-chat") && app.includes("工作区"), "original sidebar");
  assert.ok(!app.includes("console-side"), "no console chrome");
});
