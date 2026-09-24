/**
 * 实测 hcnsec API 集成测试（需网络；密钥由环境变量注入，默认跳过）。
 *
 * 运行：
 *   $env:LOOM_TEST_API_KEY='sk-...'; $env:LOOM_TEST_BASE_URL='https://api.hcnsec.cn/v1'
 *   node --experimental-strip-types tests/js/test_live_provider.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const BASE = process.env.LOOM_TEST_BASE_URL || "https://api.hcnsec.cn/v1";
const KEY = process.env.LOOM_TEST_API_KEY || "";
const LIVE = !!KEY;

const { fetchProviderModels, modelsEndpoints } = await import(
  tsUrl(path.join(root, "src/services/llm-api.ts"))
);
const { ModelChatClient, normalizeChatBaseUrl } = await import(
  tsUrl(path.join(root, "src/services/model-chat.ts"))
);

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

async function okAsync(name, fn) {
  try {
    await fn();
    passed += 1;
    console.log(`ok - ${name}`);
  } catch (err) {
    console.error(`FAIL - ${name}`);
    console.error(err);
    process.exitCode = 1;
  }
}

ok("候选端点含 /v1beta/models", () => {
  const urls = modelsEndpoints(BASE);
  assert.ok(urls.some((u) => u.endsWith("/v1beta/models")));
  assert.ok(urls.some((u) => u.endsWith("/v1/models")));
});

if (!LIVE) {
  console.log("skip live tests（未设置 LOOM_TEST_API_KEY）");
} else {
  await okAsync("实测拉取模型列表", async () => {
    const models = await fetchProviderModels(BASE, KEY);
    console.log("  live models:", models);
    assert.ok(models.length > 0);
    assert.ok(models.includes("auto") || models.length > 0);
  });

  await okAsync("实测模型对话 auto", async () => {
    const c = new ModelChatClient();
    const r = await c.complete(
      {
        providerId: "live",
        baseUrl: normalizeChatBaseUrl(BASE),
        apiKey: KEY,
        model: "auto",
      },
      [{ id: "1", role: "user", content: "你好，一句话", createdAt: Date.now() }]
    );
    console.log("  chat reply:", r.slice(0, 80));
    assert.equal(typeof r, "string");
    assert.ok(r.length > 0);
  });
}

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
