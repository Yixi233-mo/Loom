/**
 * F2 服务层测试 — REST / 事件总线 / 文件上传。
 *
 * 运行：node --experimental-strip-types tests/js/test_services.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const { API, EVENTS } = await import(tsUrl(path.join(root, "src/contracts/index.ts")));
const services = await import(tsUrl(path.join(root, "src/services/index.ts")));
const { RestClient, EventBus, FileService, createServiceLayer } = services;

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

function mockFetch(handler) {
  const calls = [];
  const f = async (input, init) => {
    calls.push({ input, init });
    return handler(input, init);
  };
  f.calls = calls;
  return f;
}

function jsonRes(data, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => data,
    text: async () => JSON.stringify(data),
  };
}

// --- REST ---

await okAsync("REST listSessions / triggerTask", async () => {
  const f = mockFetch((input) => {
    if (input.endsWith("/api/sessions")) {
      return jsonRes([{ sessionId: "s1", title: "t" }]);
    }
    return jsonRes({ taskId: "t1", status: "pending" });
  });
  const rest = new RestClient("", f);
  const sessions = await rest.listSessions();
  assert.equal(sessions[0].sessionId, "s1");
  assert.ok(f.calls[0].input.endsWith(API.SESSIONS));

  const trig = await rest.triggerTask({ workflowName: "daily_report", traceId: "tr-1" });
  assert.equal(trig.taskId, "t1");
  assert.ok(f.calls[1].input.endsWith(API.TASK_TRIGGER));
  assert.equal(f.calls[1].init.method, "POST");
});

await okAsync("REST 错误抛异常", async () => {
  const f = mockFetch(() => jsonRes({ err: "x" }, 500));
  const rest = new RestClient("", f);
  await assert.rejects(() => rest.listTasks(), /HTTP 500/);
});

// --- 事件总线 ---

ok("EventBus on/emit/onAny", () => {
  const bus = new EventBus();
  const hits = [];
  bus.on("task.updated", (m) => hits.push("task:" + m.id));
  bus.onAny((m) => hits.push("any:" + m.type));
  bus.emit({ type: "task.updated", id: "t1" });
  bus.emit({ type: "agent.status", id: "a" });
  assert.deepEqual(hits, ["any:task.updated", "task:t1", "any:agent.status"]);
});

ok("EventBus 取消订阅", () => {
  const bus = new EventBus();
  let n = 0;
  const un = bus.on("x", () => n++);
  bus.emit({ type: "x" });
  un();
  bus.emit({ type: "x" });
  assert.equal(n, 1);
});

await okAsync("WS 传输挂载 + 发送排队", async () => {
  const bus = new EventBus();
  const sent = [];
  const fakeWs = {
    readyState: 1,
    send(s) {
      sent.push(JSON.parse(s));
    },
    close() {},
  };
  const handlersRef = {};
  const transport = {
    start(h) {
      Object.assign(handlersRef, h);
    },
    send(m) {
      fakeWs.send(JSON.stringify(m));
    },
    stop() {},
  };
  // 未连接先排队
  bus.send({ type: "heartbeat", device_id: "web-1" });
  assert.equal(sent.length, 0);
  await bus.attach(transport);
  assert.equal(sent.length, 1);
  assert.equal(sent[0].type, "heartbeat");
  // 上行
  bus.send({ type: "trigger", workflow: { name: "daily_report" } });
  assert.equal(sent[1].type, "trigger");
  // 下行
  handlersRef.onMessage({ type: "task.updated", taskId: "t1" });
  // onAny 已在 emit 路径
});

// --- 文件上传 ---

await okAsync("文件上传返回 FileRef 并广播", async () => {
  const bus = new EventBus();
  const uploaded = [];
  bus.on(EVENTS.FILE_UPLOADED, (m) => uploaded.push(m.file));

  const f = mockFetch(() =>
    jsonRes({
      fileId: "f1",
      name: "spec.pdf",
      size: 1024,
      mime: "application/pdf",
      uri: "hub://files/f1",
      uploadedAt: 1,
    })
  );
  const rest = new RestClient("", f);
  const files = new FileService(rest, bus, f);

  const ref = await files.upload(
    { name: "spec.pdf", type: "application/pdf", size: 1024 },
    "web-shell-1"
  );
  assert.equal(ref.fileId, "f1");
  assert.equal(ref.uri, "hub://files/f1");
  assert.equal(uploaded.length, 1);
  assert.equal(uploaded[0].fileId, "f1");
  assert.ok(f.calls[0].input.endsWith(API.FILE_UPLOAD));
});

ok("createServiceLayer 三件齐备", () => {
  const layer = createServiceLayer({ baseUrl: "http://x" });
  assert.ok(layer.rest);
  assert.ok(layer.bus);
  assert.ok(layer.files);
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
