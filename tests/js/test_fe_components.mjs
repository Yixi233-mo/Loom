/**
 * FE.4 通用组件验收 — 状态齐全 · 可复用 · 有示例
 * run: node --experimental-strip-types tests/js/test_fe_components.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";

import {
  UI,
  Button,
  Input,
  Modal,
  Toast,
  Layout,
  Card,
  ComponentGallery,
} from "../../src/components/index.ts";

const e = React.createElement;
const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const html = (n) => renderToStaticMarkup(n);

// --- Button 状态 ---
{
  const primary = html(e(Button, { children: "保存", "data-action": "save" }));
  assert.match(primary, /ui-button--primary/);
  assert.match(primary, /data-variant="primary"/);
  assert.match(primary, /data-action="save"/);
  assert.doesNotMatch(primary, /disabled/);

  const ghost = html(e(Button, { variant: "ghost", children: "取消" }));
  assert.match(ghost, /ui-button--ghost/);

  const danger = html(e(Button, { variant: "danger", children: "删除" }));
  assert.match(danger, /ui-button--danger/);

  const disabled = html(e(Button, { disabled: true, children: "禁用" }));
  assert.match(disabled, /disabled=""/);
  assert.match(disabled, /data-loading="false"/);

  const loading = html(e(Button, { loading: true, children: "提交" }));
  assert.match(loading, /aria-busy="true"/);
  assert.match(loading, /data-loading="true"/);
  assert.match(loading, /处理中/);
  assert.match(loading, /disabled=""/);
}

// --- Input 状态 ---
{
  const normal = html(
    e(Input, { value: "hi", "data-field": "name", onChange: () => {} })
  );
  assert.match(normal, /ui-input/);
  assert.match(normal, /data-field="name"/);
  assert.match(normal, /value="hi"/);
  assert.doesNotMatch(normal, /ui-input--invalid/);

  const invalid = html(
    e(Input, { value: "", invalid: true, error: "不能为空", "data-field": "x" })
  );
  assert.match(invalid, /ui-input--invalid/);
  assert.match(invalid, /aria-invalid="true"/);
  assert.match(invalid, /不能为空/);
  assert.match(invalid, /data-error="true"/);

  const disabled = html(e(Input, { value: "a", disabled: true }));
  assert.match(disabled, /disabled=""/);
}

// --- Modal ---
{
  const closed = html(e(Modal, { open: false, title: "T" }));
  assert.match(closed, /data-open="false"/);

  const open = html(
    e(Modal, {
      open: true,
      title: "确认删除？",
      onClose: () => {},
      children: e("p", null, "正文"),
      footer: e(Button, { children: "确定" }),
    })
  );
  assert.match(open, /data-open="true"/);
  assert.match(open, /role="dialog"/);
  assert.match(open, /aria-modal="true"/);
  assert.match(open, /确认删除/);
  assert.match(open, /data-action="modal-close"/);
  assert.match(open, /data-action="modal-backdrop"/);
  assert.match(open, /ui-modal-footer/);
}

// --- Toast ---
{
  const hidden = html(e(Toast, { message: "x", visible: false }));
  assert.match(hidden, /data-visible="false"/);

  const success = html(
    e(Toast, { message: "已解锁 DSL", tone: "success", onDismiss: () => {} })
  );
  assert.match(success, /data-visible="true"/);
  assert.match(success, /data-tone="success"/);
  assert.match(success, /ui-toast--success/);
  assert.match(success, /已解锁 DSL/);
  assert.match(success, /data-action="toast-dismiss"/);

  const error = html(e(Toast, { message: "失败", tone: "error" }));
  assert.match(error, /ui-toast--error/);
}

// --- Layout / Card ---
{
  const layout = html(
    e(Layout, {
      density: "compact",
      nav: e("span", null, "nav"),
      aside: e("span", null, "side"),
      children: e("p", null, "main"),
      footer: e("span", null, "foot"),
    })
  );
  assert.match(layout, /data-view="layout"/);
  assert.match(layout, /data-density="compact"/);
  assert.match(layout, /ui-layout-nav/);
  assert.match(layout, /ui-layout-aside/);
  assert.match(layout, /ui-layout-content/);
  assert.match(layout, /ui-layout-footer/);

  const card = html(
    e(Card, { title: "标题", children: e("p", null, "内容"), footer: e("i", null, "f") })
  );
  assert.match(card, /ui-card/);
  assert.match(card, /ui-card-title/);
  assert.match(card, /ui-card-footer/);
}

// --- Gallery 示例 ---
{
  const gallery = html(e(ComponentGallery));
  assert.match(gallery, /data-view="component-gallery"/);
  assert.match(gallery, /ui-button--primary/);
  assert.match(gallery, /ui-button--danger/);
  assert.match(gallery, /ui-input--invalid/);
  assert.match(gallery, /data-action="open-modal"/);
  assert.match(gallery, /data-action="show-toast"/);
}

// --- 样式覆盖 ---
{
  const css = readFileSync(join(root, "src/styles/components.css"), "utf8");
  for (const sel of [
    ".ui-button--primary",
    ".ui-button--ghost",
    ".ui-button--danger",
    ".ui-button:disabled",
    ".ui-input--invalid",
    ".ui-input:disabled",
    ".ui-modal-backdrop",
    ".ui-toast--success",
    ".ui-toast--error",
    ".ui-layout-main",
    ".ui-card",
  ]) {
    assert.ok(css.includes(sel), `components.css 应包含 ${sel}`);
  }
  assert.ok(UI.buttonGhost === "ui-button--ghost");
  assert.ok(UI.skillNodeHalf === "ui-skill-node--half");
}

console.log("test_fe_components: ALL PASS");
