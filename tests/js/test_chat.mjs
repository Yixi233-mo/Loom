/**
 * CHAT JS 测试 — 对话区尺寸 / 模型对话客户端。
 *
 * 运行：node --experimental-strip-types tests/js/test_chat.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const require = createRequire(path.join(root, "package.json"));
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const e = React.createElement;
const render = (el) => ReactDOMServer.renderToStaticMarkup(el);

const { ChatPanel } = await import(tsUrl(path.join(root, "src/views/chat-panel.ts")));
const { ModelChatClient, toChatMessages } = await import(
  tsUrl(path.join(root, "src/services/model-chat.ts"))
);
const { createSessionState } = await import(
  tsUrl(path.join(root, "src/state/session-store.ts"))
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

const session = {
  ...createSessionState("s1", "对话"),
  status: "idle",
  draft: "你好",
  messages: [
    { id: "m1", role: "user", content: "hi", createdAt: 1 },
    { id: "m2", role: "assistant", content: "hello", createdAt: 2 },
  ],
};

ok("对话区默认固定滑窗", () => {
  const html = render(e(ChatPanel, { session }));
  assert.match(html, /data-size="default"/);
  assert.match(html, /size-default/);
  assert.match(html, /data-scroll-window="true"/);
  assert.match(html, /data-action="toggle-size"/);
});

ok("对话区可放大", () => {
  const html = render(
    e(ChatPanel, { session, size: "expanded", onToggleSize: () => {} })
  );
  assert.match(html, /data-size="expanded"/);
  assert.match(html, /size-expanded/);
  assert.match(html, /还原/);
});

ok("对话区显示当前模型", () => {
  const html = render(e(ChatPanel, { session, modelLabel: "deepseek-chat" }));
  assert.match(html, /data-model="true"/);
  assert.match(html, /deepseek-chat/);
});

ok("toChatMessages 映射 user/assistant", () => {
  const msgs = toChatMessages(session.messages, "system-prompt");
  assert.equal(msgs[0].role, "system");
  assert.equal(msgs[1].role, "user");
  assert.equal(msgs[2].content, "hello");
});

await okAsync("ModelChatClient 调用 chat completions", async () => {
  const calls = [];
  const client = new ModelChatClient(async (url, init) => {
    calls.push({ url, body: JSON.parse(init.body) });
    return {
      ok: true,
      status: 200,
      json: async () => ({
        choices: [{ message: { role: "assistant", content: "模型回复" } }],
      }),
      text: async () =>
        JSON.stringify({
          choices: [{ message: { role: "assistant", content: "模型回复" } }],
        }),
    };
  });
  const reply = await client.complete(
    {
      providerId: "p1",
      baseUrl: "https://api.x/v1",
      apiKey: "sk-1",
      model: "gpt-4o",
    },
    session.messages
  );
  assert.equal(reply, "模型回复");
  assert.match(calls[0].url, /\/chat\/completions$/);
  assert.equal(calls[0].body.model, "gpt-4o");
  assert.equal(calls[0].body.messages.length, 2);
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
