/**
 * 模型对话修复测试 — HTML 响应友好报错 / URL 规范化。
 *
 * 运行：node --experimental-strip-types tests/js/test_model_chat_fix.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const { ModelChatClient, normalizeChatBaseUrl, toChatMessages } = await import(
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

ok("normalizeChatBaseUrl 补 /v1", () => {
  assert.equal(
    normalizeChatBaseUrl("https://api.deepseek.com"),
    "https://api.deepseek.com/v1"
  );
  assert.equal(
    normalizeChatBaseUrl("https://api.deepseek.com/"),
    "https://api.deepseek.com/v1"
  );
  assert.equal(
    normalizeChatBaseUrl("https://api.openai.com/v1"),
    "https://api.openai.com/v1"
  );
  assert.equal(normalizeChatBaseUrl(""), "");
});

await okAsync("HTML 响应 → 可读错误（非 SyntaxError）", async () => {
  const client = new ModelChatClient(async () => ({
    ok: true,
    status: 200,
    json: async () => {
      throw new SyntaxError("Unexpected token '<'");
    },
    text: async () => "<!doctype html><html><body>404</body></html>",
  }));
  try {
    await client.complete(
      {
        providerId: "p",
        baseUrl: "https://api.x.com",
        apiKey: "sk",
        model: "m",
      },
      [{ id: "1", role: "user", content: "hi", createdAt: 1 }]
    );
    ok("HTML 响应应抛错", () => assert.fail("should throw"));
  } catch (err) {
    ok("HTML 响应可读错误", () => {
      assert.match(String(err.message), /服务器返回了网页/);
      assert.match(String(err.message), /\/v1/);
      assert.ok(!String(err).includes("is not valid JSON"));
    });
  }
});

await okAsync("成功 JSON 照常返回", async () => {
  const client = new ModelChatClient(async () => ({
    ok: true,
    status: 200,
    json: async () => ({}),
    text: async () =>
      JSON.stringify({ choices: [{ message: { content: "你好" } }] }),
  }));
  const reply = await client.complete(
    { providerId: "p", baseUrl: "https://api.x.com/v1", apiKey: "sk", model: "m" },
    []
  );
  assert.equal(reply, "你好");
});

await okAsync("HTTP 错误带状态码与片段", async () => {
  const client = new ModelChatClient(async () => ({
    ok: false,
    status: 401,
    json: async () => ({}),
    text: async () => '{"error":"invalid key"}',
  }));
  try {
    await client.complete(
      { providerId: "p", baseUrl: "https://api.x.com/v1", apiKey: "sk", model: "m" },
      []
    );
    ok("HTTP 错误应抛错", () => assert.fail("should throw"));
  } catch (err) {
    ok("HTTP 错误可读", () => {
      assert.match(String(err.message), /HTTP 401/);
      assert.match(String(err.message), /invalid key/);
    });
  }
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
