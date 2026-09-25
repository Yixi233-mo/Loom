/**
 * 保存后保留 apiKeyPlain — 回归测试（源码级）。
 *
 * 运行：node --experimental-strip-types tests/js/test_save_key_plain.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");

let passed = 0;
function ok(name, fn) {
  try {
    fn();
    passed += 1;
    console.log(`ok - ${name}`);
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

const app = readFileSync(path.join(root, "apps/web/src/App.tsx"), "utf8");
const panel = readFileSync(
  path.join(root, "apps/web/src/views/llm-settings-panel.ts"),
  "utf8"
);
const chat = readFileSync(
  path.join(root, "apps/web/src/services/model-chat.ts"),
  "utf8"
);

ok("保存写入 apiKeyPlain", () => {
  assert.ok(app.includes("apiKeyPlain"));
  assert.ok(app.includes("llmDraft.apiKey"));
});

ok("合并时保留旧明文 Key", () => {
  assert.ok(app.includes("prev[idx]") && app.includes("apiKeyPlain"));
});

ok("占位示例为 DeepSeek", () => {
  assert.ok(panel.includes("https://api.deepseek.com/v1"));
  assert.ok(panel.includes("DeepSeek"));
  assert.ok(!panel.includes("hcnsec"));
  assert.ok(chat.includes("https://api.deepseek.com/v1"));
  assert.ok(!chat.includes("hcnsec"));
});

ok("缺 Key 时提示重新保存", () => {
  assert.ok(app.includes("本页缺少 API Key 明文"));
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
