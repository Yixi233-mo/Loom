/**
 * T12 单元测试：DSL 编辑器 — 打开/保存 / Schema 校验 / 双模式。
 *
 * 运行：node --experimental-strip-types tests/js/test_dsl_editor.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { createRequire } from "node:module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

// 统一使用项目本地 node_modules 的 React，避免双副本导致 Invalid hook call
const require = createRequire(path.join(root, "package.json"));
const React = require("react");
const ReactDOMServer = require("react-dom/server");

const impl = await import(tsUrl(path.join(root, "src/shell/dsl-editor.impl.ts")));
const {
  createMemoryFs,
  createEditorState,
  formToYaml,
  yamlToForm,
  validateWorkflowYaml,
  validateBeforeSave,
  openYamlFile,
  saveYamlFile,
  switchMode,
  updateForm,
  updateYamlText,
} = impl;

const { DslEditor, TextareaCodeEditor, ValidationBanner } = await import(
  tsUrl(path.join(root, "src/shell/dsl-editor.ui.ts"))
);

const e = React.createElement;
const render = (el) => ReactDOMServer.renderToStaticMarkup(el);

const SAMPLE = `name: weekly_report
trigger:
  type: cron
  cron: "0 9 * * 1"
device: pc
steps:
  - id: fetch
    tool: excel.read
  - id: summarize
    agent: claude_code
    prompt: "总结"
`;

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

ok("formToYaml 基本输出", () => {
  const yaml = formToYaml({
    name: "weekly_report",
    device: "pc",
    triggerType: "cron",
    triggerCron: "0 9 * * 1",
    steps: [
      { id: "fetch", kind: "tool", target: "excel.read" },
      { id: "sum", kind: "agent", target: "claude_code", prompt: "总结" },
    ],
  });
  assert.match(yaml, /^name: weekly_report/m);
  assert.match(yaml, /device: pc/);
  assert.match(yaml, /- id: fetch/);
  assert.match(yaml, /tool: excel.read/);
  assert.match(yaml, /agent: claude_code/);
});

ok("yamlToForm 解析示例", () => {
  const form = yamlToForm(SAMPLE);
  assert.equal(form.name, "weekly_report");
  assert.equal(form.device, "pc");
  assert.equal(form.triggerType, "cron");
  assert.equal(form.triggerCron, "0 9 * * 1");
  assert.equal(form.steps.length, 2);
  assert.equal(form.steps[0].kind, "tool");
  assert.equal(form.steps[1].kind, "agent");
});

ok("form → yaml → form 往返", () => {
  const form = {
    name: "n1",
    device: "tablet",
    steps: [{ id: "a", kind: "agent", target: "builtin_rag", prompt: "q" }],
  };
  const rt = yamlToForm(formToYaml(form));
  assert.equal(rt.name, "n1");
  assert.equal(rt.device, "tablet");
  assert.equal(rt.steps[0].id, "a");
  assert.equal(rt.steps[0].target, "builtin_rag");
  assert.equal(rt.steps[0].prompt, "q");
});

ok("合法 YAML 校验通过", () => {
  const r = validateBeforeSave(SAMPLE);
  assert.equal(r.ok, true);
  assert.equal(r.issues.length, 0);
});

ok("缺 name 报错", () => {
  const r = validateWorkflowYaml("device: pc\nsteps:\n  - id: a\n    tool: t\n");
  assert.equal(r.ok, false);
  assert.ok(r.issues.some((i) => /name/.test(i.message)));
});

ok("缺 steps 报错", () => {
  const r = validateWorkflowYaml("name: x\ndevice: pc\n");
  assert.equal(r.ok, false);
  assert.ok(r.issues.some((i) => /steps/.test(i.message)));
});

ok("非法 device 报错", () => {
  const r = validateWorkflowYaml("name: x\ndevice: watch\nsteps:\n  - id: a\n    tool: t\n");
  assert.equal(r.ok, false);
  assert.ok(r.issues.some((i) => /device/.test(i.message)));
});

ok("空内容报错", () => {
  const r = validateWorkflowYaml("");
  assert.equal(r.ok, false);
});

await okAsync("打开 yaml 文件", async () => {
  const fs = createMemoryFs({ "wf.yaml": SAMPLE });
  const st = await openYamlFile(fs, "wf.yaml");
  assert.equal(st.filename, "wf.yaml");
  assert.equal(st.mode, "file");
  assert.equal(st.dirty, false);
  assert.equal(st.form.name, "weekly_report");
});

await okAsync("保存前校验通过才写入", async () => {
  const fs = createMemoryFs();
  const st = createEditorState({
    filename: "ok.yaml",
    yamlText: SAMPLE,
    dirty: true,
  });
  const result = await saveYamlFile(fs, st);
  assert.equal(result.ok, true);
  assert.equal(fs.files.get("ok.yaml"), SAMPLE);
});

await okAsync("保存前校验失败拒绝写入", async () => {
  const fs = createMemoryFs();
  const st = createEditorState({
    filename: "bad.yaml",
    yamlText: "device: pc\nsteps: []\n",
  });
  const result = await saveYamlFile(fs, st);
  assert.equal(result.ok, false);
  assert.ok(result.issues.length > 0);
  assert.ok(!fs.files.has("bad.yaml"), "校验失败不得写盘");
});

await okAsync("打开不存在文件抛错", async () => {
  const fs = createMemoryFs();
  await assert.rejects(() => openYamlFile(fs, "nope.yaml"));
});

ok("file → form 切换解析表单", () => {
  const st = createEditorState({ mode: "file", yamlText: SAMPLE });
  const st2 = switchMode(st, "form");
  assert.equal(st2.mode, "form");
  assert.equal(st2.form.name, "weekly_report");
  assert.equal(st2.form.steps.length, 2);
});

ok("form → file 切换序列化 YAML", () => {
  let st = createEditorState({ mode: "file", yamlText: SAMPLE });
  st = switchMode(st, "form");
  st = updateForm(st, { ...st.form, name: "renamed" });
  st = switchMode(st, "file");
  assert.equal(st.mode, "file");
  assert.match(st.yamlText, /name: renamed/);
});

ok("updateYamlText 同步 form", () => {
  let st = createEditorState();
  st = updateYamlText(st, "name: t\ndevice: mobile\nsteps:\n  - id: a\n    tool: x\n");
  assert.equal(st.form.device, "mobile");
  assert.equal(st.dirty, true);
});

ok("DslEditor 双模式按钮存在", () => {
  const fs = createMemoryFs();
  const html = render(
    e(DslEditor, {
      fs,
      state: createEditorState({ yamlText: SAMPLE }),
      onState: () => {},
    })
  );
  assert.match(html, /data-component="dsl-editor"/);
  assert.match(html, /文件模式/);
  assert.match(html, /表单模式/);
  assert.match(html, /保存/);
  assert.match(html, /校验/);
});

ok("文件模式渲染 textarea", () => {
  const html = render(e(TextareaCodeEditor, { value: SAMPLE, onChange: () => {} }));
  assert.match(html, /data-editor-backend="textarea"/);
});

ok("ValidationBanner 显示问题", () => {
  const html = render(
    e(ValidationBanner, {
      issues: [{ path: "/name", message: "缺少必填字段: name" }],
    })
  );
  assert.match(html, /Schema 校验未通过/);
  assert.match(html, /缺少必填字段: name/);
});

ok("ValidationBanner 空问题不渲染", () => {
  const html = render(e(ValidationBanner, { issues: [] }));
  assert.equal(html, "");
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
