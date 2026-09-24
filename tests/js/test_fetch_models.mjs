/**
 * 拉取模型测试 — 按 URL+Key 真拉取，拒绝固定列表。
 *
 * 运行：node --experimental-strip-types tests/js/test_fetch_models.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const { fetchProviderModels } = await import(
  tsUrl(path.join(root, "src/services/llm-api.ts"))
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

await okAsync("按 URL+Key 拉取 OpenAI 形状 models", async () => {
  const seen = [];
  const models = await fetchProviderModels(
    "https://api.deepseek.com/v1",
    "sk-test",
    async (url, init) => {
      seen.push({ url, headers: init?.headers });
      return {
        ok: true,
        status: 200,
        text: async () =>
          JSON.stringify({
            data: [{ id: "deepseek-chat" }, { id: "deepseek-reasoner" }],
          }),
      };
    }
  );
  assert.deepEqual(models, ["deepseek-chat", "deepseek-reasoner"]);
  assert.equal(seen[0].url, "https://api.deepseek.com/v1/models");
  assert.equal(seen[0].headers.Authorization, "Bearer sk-test");
});

await okAsync("无 /v1 时尝试 /v1/models 回退 /models", async () => {
  const urls = [];
  const models = await fetchProviderModels(
    "https://api.ollama.local:11434",
    "",
    async (url) => {
      urls.push(url);
      if (url.endsWith("/v1/models")) throw new Error("404");
      return {
        ok: true,
        status: 200,
        text: async () => JSON.stringify({ models: [{ name: "qwen-max" }] }),
      };
    }
  );
  assert.deepEqual(models, ["qwen-max"]);
  assert.ok(urls.some((u) => u.endsWith("/models")));
});

await okAsync("HTML 响应报可读错误", async () => {
  try {
    await fetchProviderModels("https://bad.example.com", "sk", async () => ({
      ok: true,
      status: 200,
      text: async () => "<!doctype html><html></html>",
    }));
    ok("应抛错", () => assert.fail("should throw"));
  } catch (err) {
    ok("HTML 可读错误", () => {
      assert.match(String(err.message), /服务器返回了网页/);
    });
  }
});

await okAsync("服务商返回空列表报错", async () => {
  try {
    await fetchProviderModels("https://api.x.com/v1", "sk", async () => ({
      ok: true,
      status: 200,
      text: async () => JSON.stringify({ data: [] }),
    }));
    ok("空列表应抛错", () => assert.fail("should throw"));
  } catch (err) {
    ok("空列表错误", () => {
      assert.match(String(err.message), /未返回任何模型/);
    });
  }
});

ok("App 不再写死模型列表回退", () => {
  const src = readFileSync(path.join(root, "src/App.tsx"), "utf8");
  assert.ok(!src.includes('models: ["gpt-4o"'));
  assert.ok(src.includes("fetchProviderModels"));
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
