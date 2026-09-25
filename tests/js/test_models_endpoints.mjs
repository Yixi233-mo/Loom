/**
 * 端点清理与报错优先级测试。
 *
 * 运行：node --experimental-strip-types tests/js/test_models_endpoints.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const { modelsEndpoints, fetchProviderModels } = await import(
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

ok("不再产生 /v1/v1beta", () => {
  const urls = modelsEndpoints("https://api.hcnsec.cn/v1");
  assert.ok(!urls.some((u) => u.includes("/v1/v1beta")), urls.join(","));
  assert.ok(urls.includes("https://api.hcnsec.cn/v1/models"));
  assert.ok(urls.includes("https://api.hcnsec.cn/v1beta/models"));
});

ok("无 /v1 的 base 也干净", () => {
  const urls = modelsEndpoints("https://api.hcnsec.cn");
  assert.ok(!urls.some((u) => u.includes("/v1/v1beta")));
  assert.ok(urls.includes("https://api.hcnsec.cn/v1/models"));
});

await okAsync("优先报首个真实错误（401），不是最后一个 404", async () => {
  const calls = [];
  try {
    await fetchProviderModels(
      "https://api.hcnsec.cn/v1",
      "",
      async (url) => {
        calls.push(url);
        if (url.includes("/v1/v1beta")) {
          return {
            ok: false,
            status: 404,
            text: async () =>
              '{"error":{"message":"Invalid URL (GET /v1/v1beta/models)"}}',
          };
        }
        return {
          ok: false,
          status: 401,
          text: async () => '{"error":{"message":"Invalid token"}}',
        };
      }
    );
    ok("应抛错", () => assert.fail("should throw"));
  } catch (err) {
    ok("报 401 而非 404", () => {
      assert.match(String(err.message), /HTTP 401|Invalid token/);
      assert.match(String(err.message), /重新保存 API Key/);
      assert.ok(!String(err.message).includes("Invalid URL (GET /v1/v1beta"));
    });
  }
});

await okAsync("第一个端点成功即返回", async () => {
  const calls = [];
  const models = await fetchProviderModels(
    "https://api.hcnsec.cn/v1",
    "sk",
    async (url) => {
      calls.push(url);
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ data: [{ id: "auto" }] }),
      };
    }
  );
  assert.deepEqual(models, ["auto"]);
  assert.equal(calls.length, 1);
  assert.ok(calls[0].endsWith("/v1/models"));
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
