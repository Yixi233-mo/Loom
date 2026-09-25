/**
 * 模型配置选用 / 毛玻璃按钮 — 验收
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";
import { LlmSettingsPanel } from "../../apps/web/src/views/llm-settings-panel.ts";

const e = React.createElement;
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const html = (n) => renderToStaticMarkup(n);

const providers = [
  {
    providerId: "p1",
    name: "DeepSeek",
    baseUrl: "https://api.deepseek.com/v1",
    defaultModel: "deepseek-chat",
    models: ["deepseek-chat", "deepseek-reasoner"],
    apiKeyMasked: "sk***",
  },
  {
    providerId: "p2",
    name: "Other",
    baseUrl: "https://api.other.com/v1",
    defaultModel: "",
    models: [],
  },
];

const out = html(
  e(LlmSettingsPanel, {
    providers,
    draft: { name: "", baseUrl: "", apiKey: "" },
    activeProviderId: "p1",
    onActiveProvider: () => {},
  })
);

assert.match(out, /data-view="llm-active"/);
assert.match(out, /active-provider-select/);
assert.match(out, /选用此配置|使用中/);
assert.match(out, /data-active-provider="p1"/);
assert.match(out, /data-action="use-provider"/);
assert.match(out, /data-field="model-select"/);
assert.match(out, /deepseek-reasoner/);

const css = readFileSync(join(root, "apps/web/src/styles/controls.css"), "utf8");
assert.ok(css.includes(".nav-link"));
assert.ok(css.includes("backdrop-filter"));
assert.ok(css.includes(".ui-button"));
assert.ok(css.includes(".llm-item.is-active"));

const idx = readFileSync(join(root, "apps/web/src/styles/index.css"), "utf8");
assert.ok(idx.includes("controls.css"));

console.log("test_llm_select: ALL PASS");
