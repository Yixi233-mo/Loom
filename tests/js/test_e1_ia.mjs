/**
 * E1 侧栏 — 无 emoji 字标 + 轻量增强
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const app = readFileSync(join(root, "apps", "web", "src", "App.tsx"), "utf8");
const layout = readFileSync(join(root, "apps", "web", "src", "styles", "layout.css"), "utf8");
const wizard = readFileSync(join(root, "apps", "web", "src", "features", "connect-wizard.ts"), "utf8");

test("保留原侧栏属性", () => {
  assert.ok(app.includes("side-brand"), "side-brand");
  assert.ok(app.includes("side-new-chat"), "side-new-chat");
  assert.ok(app.includes("side-user"), "side-user");
  assert.ok(app.includes("工作区"), "workgroup label");
});

test("无 emoji，使用字标", () => {
  for (const emo of ["💬", "◎", "▤", "◈", "⬡", "✎", "⌘", "☆", "⚙", "🔐", "🔑"]) {
    assert.ok(!app.includes(emo), `no ${emo}`);
    assert.ok(!wizard.includes(emo), `no wizard ${emo}`);
  }
  assert.ok(app.includes('"CT"') && app.includes('"TK"'), "monograms");
});

test("扫码连接默认出二维码", () => {
  assert.ok(wizard.includes("useState(true)"), "pairing shown by default");
  assert.ok(wizard.includes("PairingPanel") && wizard.includes("qrToSvg"), "QR panel");
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
