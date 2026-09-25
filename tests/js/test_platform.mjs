/**
 * F4 三端适配测试 — 设备探测 / Tauri IPC / 能力桥。
 *
 * 运行：node --experimental-strip-types tests/js/test_platform.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const platform = await import(tsUrl(path.join(root, "src/platform/index.ts")));
const {
  detectDeviceType,
  detectDevice,
  layoutFor,
  TauriBridge,
  capabilitiesFor,
  registerPayload,
  can,
  CAPABILITIES,
  createPlatformLayer,
} = platform;

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

// --- 设备探测 / 响应式 ---

ok("宽度映射 pc/tablet/mobile", () => {
  assert.equal(detectDeviceType(1440), "pc");
  assert.equal(detectDeviceType(1280), "pc");
  assert.equal(detectDeviceType(1024), "tablet");
  assert.equal(detectDeviceType(768), "tablet");
  assert.equal(detectDeviceType(375), "mobile");
});

ok("layoutFor 四档", () => {
  assert.equal(layoutFor("pc", 1440), "wide");
  assert.equal(layoutFor("tablet", 1100), "medium");
  assert.equal(layoutFor("tablet", 900), "compact");
  assert.equal(layoutFor("mobile", 375), "narrow");
});

ok("detectDevice 字段完整", () => {
  const d = detectDevice(1440, 900);
  assert.equal(d.deviceType, "pc");
  assert.equal(d.width, 1440);
  assert.equal(d.height, 900);
  assert.equal(d.canShellExec, true);
  assert.equal(detectDevice(375, 667).canShellExec, false);
});

// --- Tauri IPC ---

await okAsync("无 Tauri 时优雅降级 mock", async () => {
  const bridge = new TauriBridge(null);
  assert.equal(bridge.available, false);
  const plugins = await bridge.listPlugins();
  assert.deepEqual(plugins, []);
  const wr = await bridge.writeTextFile("/tmp/a.yaml", "x: 1");
  assert.equal(wr.ok, true);
  assert.equal(bridge.mockCalls.length, 2);
});

await okAsync("有 Tauri 时走 invoke", async () => {
  const calls = [];
  const bridge = new TauriBridge({
    invoke: async (cmd, args) => {
      calls.push({ cmd, args });
      return { name: "notes", version: "1.0.0" };
    },
  });
  assert.equal(bridge.available, true);
  const r = await bridge.listPlugins("/plugins");
  assert.equal(r.name, "notes");
  assert.equal(calls[0].cmd, "list_plugins");
  assert.equal(calls[0].args.root, "/plugins");
  assert.equal(bridge.mockCalls.length, 0);
});

// --- 能力桥 ---

ok("三端 capabilities 声明", () => {
  const pc = capabilitiesFor("pc");
  assert.ok(pc.includes(CAPABILITIES.SHELL_EXEC));
  assert.ok(pc.includes(CAPABILITIES.FILE_READ));

  const tablet = capabilitiesFor("tablet");
  assert.ok(!tablet.includes(CAPABILITIES.SHELL_EXEC));
  assert.ok(tablet.includes(CAPABILITIES.FILE_READ));

  const mobile = capabilitiesFor("mobile");
  assert.ok(mobile.includes(CAPABILITIES.CAMERA));
  assert.ok(!mobile.includes(CAPABILITIES.FILE_READ));
});

ok("registerPayload 对齐 DeviceMesh", () => {
  const info = detectDevice(1440, 900);
  const p = registerPayload(info, "web-pc-1");
  assert.equal(p.type, "register");
  assert.equal(p.device_id, "web-pc-1");
  assert.equal(p.device_type, "pc");
  assert.ok(Array.isArray(p.capabilities));
  assert.ok(typeof p.ts === "number");
});

ok("can() 能力判断", () => {
  assert.ok(can({ deviceType: "pc" }, CAPABILITIES.SHELL_EXEC));
  assert.ok(!can({ deviceType: "mobile" }, CAPABILITIES.SHELL_EXEC));
  assert.ok(can({ deviceType: "mobile" }, CAPABILITIES.CAMERA));
});

ok("createPlatformLayer 三件齐备", () => {
  const layer = createPlatformLayer(375, 667, null);
  assert.equal(layer.device.deviceType, "mobile");
  assert.equal(layer.layout, "narrow");
  assert.ok(layer.capabilities.includes(CAPABILITIES.CAMERA));
  assert.equal(layer.tauri.available, false);
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
