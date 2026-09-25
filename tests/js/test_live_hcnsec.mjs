/**
 * 实测 hcnsec.cn API（需网络 + 密钥）。
 * 密钥由环境变量 LIVE_API_KEY 提供，不写入仓库。
 *
 * 运行：
 *   $env:LIVE_API_KEY='sk-...'; node --experimental-strip-types tests/js/test_live_hcnsec.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const { fetchProviderModels, modelsEndpoints } = await import(
  tsUrl(path.join(root, "apps/web/src/services/llm-api.ts"))
);
const { ModelChatClient, normalizeChatBaseUrl } = await import(
  tsUrl(path.join(root, "apps/web/src/services/model-chat.ts"))
);

const BASE = process.env.LIVE_BASE_URL || "https://api.hcnsec.cn/v1";
const KEY = process.env.LIVE_API_KEY || "";

if (!KEY) {
  console.log("跳过在线测试：未设置 LIVE_API_KEY");
  process.exit(0);
}

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

ok("候选含 /v1beta/models 与 /v1/models", () => {
  const urls = modelsEndpoints(BASE);
  assert.ok(urls.some((u) => u.endsWith("/v1beta/models")));
  assert.ok(urls.some((u) => u.endsWith("/v1/models")));
});

await okAsync("在线拉取模型列表", async () => {
  const models = await fetchProviderModels(BASE, KEY);
  console.log("  models =", models);
  assert.ok(models.includes("auto"), "应含 auto");
  assert.ok(models.includes("glm-5.3"), "应含 glm-5.3");
});

await okAsync("在线对话 auto 可用", async () => {
  const c = new ModelChatClient();
  const reply = await c.complete(
    {
      providerId: "live",
      baseUrl: normalizeChatBaseUrl(BASE),
      apiKey: KEY,
      model: "auto",
    },
    [{ id: "1", role: "user", content: "用一句话介绍你自己", createdAt: Date.now() }]
  );
  console.log("  reply =", reply.slice(0, 80));
  assert.ok(reply.length > 0);
});

await okAsync("不支持模型给出可读错误", async () => {
  const c = new ModelChatClient();
  try {
    await c.complete(
      {
        providerId: "live",
        baseUrl: normalizeChatBaseUrl(BASE),
        apiKey: KEY,
        model: "DeepSeek-V4.1-Flash",
      },
      [{ id: "1", role: "user", content: "hi", createdAt: Date.now() }]
    );
    ok("应抛错", () => assert.fail("should throw"));
  } catch (err) {
    ok("错误文案可读", () => {
      assert.match(String(err.message), /不支持对话|not supported/i);
    });
  }
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
