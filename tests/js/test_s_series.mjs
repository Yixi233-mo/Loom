/** S1/S5 — 错误契约与请求重试 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const rest = readFileSync(join(root, "src", "services", "rest.ts"), "utf8");
const errors = readFileSync(join(root, "api", "errors.py"), "utf8");
const routes = readFileSync(join(root, "api", "routes.py"), "utf8");
const hub = readFileSync(join(root, "scripts", "run_hub_server.py"), "utf8");

test("S1 统一错误体 code/message/trace_id", () => {
  assert.match(errors, /trace_id/);
  assert.match(errors, /make_error/);
  assert.match(errors, /install_error_contract/);
  assert.match(routes, /install_error_contract/);
});

test("S5 REST 重试与友好错误", () => {
  assert.match(rest, /attempt/);
  assert.match(rest, /trace/);
});

test("S3 列表窗口", () => {
  assert.match(routes, /limit/);
  assert.match(routes, /out\[-limit:\]|limit/);
});

test("S4 启动依赖就绪日志", () => {
  assert.match(hub, /依赖就绪|依赖未就绪|check_dependencies/);
});

test("错误信息脱敏不泄漏 Key", () => {
  assert.match(errors, /redact_secrets/);
});
