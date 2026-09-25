/**
 * 扫码连接：真二维码 + 配对码 + 手动地址；无 emoji
 */
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { qrToSvg, encodeQrMatrix } from "../../apps/web/src/features/qr-code.ts";
import {
  CONNECT_STEPS,
  buildPairingInfo,
  makePairingCode,
} from "../../apps/web/src/features/connect-wizard.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const wizard = readFileSync(join(root, "apps/web/src/features/connect-wizard.ts"), "utf8");

test("QR 生成 SVG", () => {
  const svg = qrToSvg("loom://pair?code=TEST12", { scale: 4 });
  assert.ok(svg.includes("<svg"), "svg root");
  assert.ok(svg.includes("path"), "modules path");
  const m = encodeQrMatrix("http://127.0.0.1:5173/#/devices?pair=ABCD12");
  assert.ok(m.length >= 21, "matrix size");
  assert.ok(m.some((row) => row.some(Boolean)), "has dark modules");
});

test("配对码与连接地址", () => {
  const code = makePairingCode();
  assert.equal(code.length, 6);
  assert.ok(!/[01OIL]/.test(code), "no ambiguous chars");
  const info = buildPairingInfo("ZZZZ99", {
    hostname: "10.0.0.8",
    port: "8765",
    protocol: "http:",
  });
  assert.ok(info.url.includes("ZZZZ99"));
  assert.ok(info.hub.includes("10.0.0.8:8765"));
});

test("Connect 步骤无 emoji", () => {
  const blob = JSON.stringify(CONNECT_STEPS) + wizard;
  assert.ok(!/[\u{1F300}-\u{1FAFF}]/u.test(blob), "no emoji");
  assert.ok(wizard.includes("PairingPanel"), "has pairing panel");
  assert.ok(wizard.includes("pairing-qr"), "has qr mount");
  assert.ok(wizard.includes("手动填本机地址"), "manual fallback");
});

test("三步编号 01/02/03", () => {
  assert.deepEqual(
    CONNECT_STEPS.map((s) => s.icon),
    ["01", "02", "03"]
  );
});
