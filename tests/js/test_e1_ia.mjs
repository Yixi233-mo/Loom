/**
 * E1 侧栏 — 保持原毛玻璃风格，仅轻量增强
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const app = readFileSync(join(root, "src", "App.tsx"), "utf8");
const layout = readFileSync(join(root, "src", "styles", "layout.css"), "utf8");

test("保留原侧栏属性", () => {
  assert.ok(app.includes("side-brand"), "side-brand");
  assert.ok(app.includes("side-new-chat"), "side-new-chat");
  assert.ok(app.includes("side-user"), "side-user");
  assert.ok(app.includes("工作区"), "workgroup label");
  assert.ok(app.includes("💬") && app.includes("◎"), "original emoji icons");
  assert.ok(!app.includes("console-side"), "no console chrome");
});

test("产品叙事轻改", () => {
  assert.ok(app.includes("AI 总控台"), "subtitle");
});

test("路由未删减", () => {
  for (const r of [
    "chat",
    "tasks",
    "files",
    "knowledge",
    "agents",
    "prompts",
    "mcp",
    "recommend",
    "settings",
    "devices",
    "help",
  ]) {
    assert.ok(
      app.includes(`"${r}"`) || app.includes(`'${r}'`),
      `route ${r} missing`
    );
  }
});

test("轻量增强：角标 + 接入组", () => {
  assert.ok(layout.includes("nav-badge"), "badge css");
  assert.ok(app.includes("接入") || app.includes("agents"), "agents entry");
});
