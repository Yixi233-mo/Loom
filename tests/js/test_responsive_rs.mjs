/**
 * RS 响应式体系 + 相机扫码
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const css = readFileSync(join(root, "apps/web/src/styles/responsive.css"), "utf8");
const wizard = readFileSync(join(root, "apps/web/src/features/connect-wizard.ts"), "utf8");
const scan = readFileSync(join(root, "apps/web/src/features/camera-scan.ts"), "utf8");
const manifest = readFileSync(
  join(root, "apps", "desktop", "src-tauri", "gen", "android", "app", "src", "main", "AndroidManifest.xml"),
  "utf8"
);
const plan = readFileSync(
  join(root, "目录/05-任务Spec/PLAN_全模块自适应.md"),
  "utf8"
);

test("RS 三条铁律入规划与样式", () => {
  assert.match(plan, /不允许横向滚动/);
  assert.match(plan, /不允许固定像素宽度|固定像素/);
  assert.match(css, /overflow-x: hidden/);
  assert.match(css, /min-height: 44px/);
});

test("RS 断点 768 / 1024", () => {
  assert.match(css, /max-width: 767/);
  assert.match(css, /min-width: 1024px/);
  assert.match(css, /768px/);
});

test("RS 移动骨架：顶栏+主区+底Tab+安全区", () => {
  assert.match(css, /tabbar/);
  assert.match(css, /safe-area-inset|safe-bottom/);
  assert.match(css, /app-header/);
});

test("RS 表单单列与底部抽屉", () => {
  assert.match(css, /flex-direction: column/);
  assert.match(css, /bottom: 0/);
  assert.match(css, /80vh/);
});

test("RS4 相机扫码", () => {
  assert.match(scan, /getUserMedia/);
  assert.match(scan, /BarcodeDetector|camera/);
  assert.match(wizard, /CameraScanner/);
  assert.match(manifest, /CAMERA/);
});

test("RS 任务表格移动卡片化", () => {
  assert.match(css, /overflow-x: auto/);
  assert.match(css, /result-card|table/);
});
