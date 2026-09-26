/** 诊断面板：应用内自检 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const diag = readFileSync(
  join(root, "apps/web/src/features/diagnostics.ts"),
  "utf8"
);
const settings = readFileSync(
  join(root, "apps/web/src/features/settings-page.ts"),
  "utf8"
);
const main = readFileSync(join(root, "apps/web/src/main.tsx"), "utf8");

test("诊断面板存在", () => {
  assert.match(diag, /自检 \/ 诊断|自检/);
  assert.match(diag, /probeHub/);
  assert.match(diag, /复制诊断信息/);
});

test("设置页挂载诊断", () => {
  assert.match(settings, /DiagnosticsPanel/);
});

test("全局错误进诊断", () => {
  assert.match(diag, /pushDiagError/);
  assert.match(main, /installDiagnosticsCapture/);
});
