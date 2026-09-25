/**
 * E2 接入向导 + E3 说话即任务
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const wizard = readFileSync(join(root, "apps/web/src/features/connect-wizard.ts"), "utf8");
const agents = readFileSync(join(root, "apps/web/src/features/agents-page.ts"), "utf8");
const chat = readFileSync(join(root, "apps/web/src/features/chat-workbench.ts"), "utf8");
const app = readFileSync(join(root, "apps/web/src/App.tsx"), "utf8");

test("E2 三步接入：扫码 / 授权 / 贴 Key", () => {
  assert.match(wizard, /扫码连接/);
  assert.match(wizard, /一键授权/);
  assert.match(wizard, /粘贴 API Key|粘贴 API Key|API Key/);
  assert.match(agents, /ConnectWizard/);
  assert.match(app, /onOpenRoute/);
});

test("E3 说话即任务解析", () => {
  assert.match(wizard, /parseTaskPreview/);
  assert.match(wizard, /looksLikeTask/);
  assert.match(wizard, /任务预览/);
  assert.match(chat, /pendingPreview/);
  assert.match(chat, /TaskPreviewCard/);
  assert.match(app, /onConfirmPreview/);
  assert.match(app, /onCancelPreview/);
});

test("E3 确认后才创建", () => {
  assert.match(app, /确认后才会创建|已创建任务/);
  assert.match(wizard, /确认创建/);
});

test("功能不删减：路由仍在", () => {
  for (const r of ["mcp", "recommend", "knowledge", "files", "prompts"]) {
    assert.ok(app.includes(`"${r}"`), r);
  }
});
