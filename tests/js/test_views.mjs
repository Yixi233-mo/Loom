/**
 * F3 视图层测试 — 对话区 / 任务面板 / 结果卡片 / 文件区。
 *
 * 运行：node --experimental-strip-types tests/js/test_views.mjs
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

const views = await import(tsUrl(path.join(root, "src/views/index.ts")));
const { ChatPanel, TaskPanel, ResultCard, FilePanel, Workspace, MessageBubble } = views;
const { createSessionState, createTask, TaskStore, SessionStore } = await import(
  tsUrl(path.join(root, "src/state/index.ts"))
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

const sampleSession = {
  ...createSessionState("s1", "跨端会话"),
  status: "streaming",
  draft: "你好",
  messages: [
    { id: "m1", role: "user", content: "帮我查资料", createdAt: 1 },
    { id: "m2", role: "assistant", content: "正在检索…", createdAt: 2 },
  ],
};

const sampleTasks = [
  createTask({
    taskId: "t1",
    workflowName: "daily_report",
    traceId: "tr-1",
    device: "pc",
    assignedTo: "pc-1",
    status: "done",
  }),
  {
    ...createTask({
      taskId: "t2",
      workflowName: "mobile_to_pc_pdf",
      traceId: "tr-2",
      device: "pc",
      status: "running",
    }),
    result: {
      summary: "PDF 已总结",
      tokensUsed: 120,
      latencyMs: 340,
      degradationLevel: 1,
    },
  },
];

const sampleFiles = [
  {
    fileId: "f1",
    name: "spec.pdf",
    size: 2048,
    mime: "application/pdf",
    uri: "hub://files/f1",
    uploadedAt: 1,
  },
];

ok("对话区渲染消息流", () => {
  const html = render(e(ChatPanel, { session: sampleSession }));
  assert.match(html, /data-view="chat"/);
  assert.match(html, /帮我查资料/);
  assert.match(html, /正在检索…/);
  assert.match(html, /data-message-count="2"/);
});

ok("对话区输入与发送按钮", () => {
  const html = render(e(ChatPanel, { session: sampleSession, onSend: () => {} }));
  assert.match(html, /data-action="send"/);
  assert.match(html, /data-field="draft"/);
  assert.match(html, /你好/);
});

ok("任务面板列表与筛选", () => {
  const html = render(e(TaskPanel, { tasks: sampleTasks, filter: "all" }));
  assert.match(html, /data-view="tasks"/);
  assert.match(html, /daily_report/);
  assert.match(html, /data-task-count="2"/);
  assert.match(html, /data-filter="done"/);
});

ok("任务面板按状态过滤", () => {
  const html = render(e(TaskPanel, { tasks: sampleTasks, filter: "running" }));
  assert.match(html, /data-task-count="1"/);
  assert.match(html, /mobile_to_pc_pdf/);
  assert.doesNotMatch(html, /daily_report/);
});

ok("结果卡片含成本字段", () => {
  const html = render(
    e(ResultCard, {
      result: sampleTasks[1].result,
      traceId: "tr-2",
      taskName: "mobile_to_pc_pdf",
    })
  );
  assert.match(html, /data-view="result-card"/);
  assert.match(html, /data-metric="tokens_used"/);
  assert.match(html, /data-metric="latency_ms"/);
  assert.match(html, /data-metric="degradation_level"/);
  assert.match(html, /120/);
  assert.match(html, /tr-2/);
});

ok("文件区上传与列表", () => {
  const html = render(e(FilePanel, { files: sampleFiles, onUpload: () => {} }));
  assert.match(html, /data-view="files"/);
  assert.match(html, /data-action="upload"/);
  assert.match(html, /spec\.pdf/);
  assert.match(html, /hub:\/\/files\/f1/);
  assert.match(html, /data-action="delete-file"/);
});

ok("文件区空态", () => {
  const html = render(e(FilePanel, { files: [] }));
  assert.match(html, /暂无文件/);
});

ok("Workspace 组合四区", () => {
  const html = render(
    e(Workspace, {
      session: sampleSession,
      tasks: sampleTasks,
      files: sampleFiles,
      onSend: () => {},
    })
  );
  assert.match(html, /data-view="workspace"/);
  assert.match(html, /data-view="chat"/);
  assert.match(html, /data-view="tasks"/);
  assert.match(html, /data-view="result-card"/);
  assert.match(html, /data-view="files"/);
});

ok("MessageBubble 按角色标记", () => {
  const html = render(
    e(MessageBubble, { message: { id: "x", role: "user", content: "hi", createdAt: 0 } })
  );
  assert.match(html, /role-user/);
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
