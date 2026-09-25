/**
 * 测试：模型列表端点包含 /v1beta/models。
 *
 * 运行：node --experimental-strip-types tests/js/test_v1beta_models.mjs
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

ok("候选含 /v1beta/models", () => {
  const urls = modelsEndpoints("https://api.example.com/v1");
  assert.ok(urls.some((u) => u.endsWith("/v1/models")), urls.join(","));
  assert.ok(urls.some((u) => u.endsWith("/v1beta/models")), urls.join(","));
  assert.ok(urls.some((u) => u.endsWith("/v1/models")));
  const urls2 = modelsEndpoints("https://api.example.com");
  assert.ok(urls2.some((u) => u.endsWith("/v1beta/models")));
});

await okAsync("优先命中 /v1beta/models", async () => {
  const hit = [];
  const models = await fetchProviderModels(
    "https://api.newapi.com/v1",
    "sk-1",
    async (url) => {
      hit.push(url);
      if (url.endsWith("/v1beta/models")) {
        return {
          ok: true,
          status: 200,
          text: async () =>
            JSON.stringify({ data: [{ id: "gpt-4o-mini" }, { id: "m1" }] }),
        };
      }
      return {
        ok: false,
        status: 401,
        text: async () => '{"error":{"message":"无效的令牌"}}',
      };
    }
  );
  assert.deepEqual(models, ["gpt-4o-mini", "m1"]);
  assert.ok(
    hit[0].endsWith("/v1/models") || hit[0].endsWith("/v1beta/models"),
    hit[0]
  );
});

await okAsync("失败时错误含已试端点", async () => {
  try {
    await fetchProviderModels("https://api.bad.com/v1", "sk", async () => ({
      ok: false,
      status: 401,
      text: async () => '{"error":{"message":"无效的令牌"}}',
    }));
    ok("应抛错", () => assert.fail("should throw"));
  } catch (err) {
    ok("错误可读", () => {
      assert.match(String(err.message), /无效的令牌|HTTP 401/);
      assert.match(String(err.message), /已尝试/);
      assert.match(String(err.message), /v1beta/);
    });
  }
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
