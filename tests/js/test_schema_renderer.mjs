/**
 * T11 单元测试：UI Schema 渲染器白名单 + 四类组件 + 友好提示。
 *
 * 运行：node --experimental-strip-types tests/js/test_schema_renderer.mjs
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

const { UI_WHITELIST, UI_TYPES, resolveUiSchema, unknownTypeMessage, isUiComponentType } =
  await import(tsUrl(path.join(root, "apps/web/src/shell/ui-registry.ts")));

const {
  FormView,
  ListView,
  ChatView,
  ChartView,
  UnknownTypeNotice,
  UI_COMPONENTS,
  SchemaRenderer,
} = await import(tsUrl(path.join(root, "apps/web/src/shell/schema-renderer.impl.ts")));

const e = React.createElement;
const render = (el) => ReactDOMServer.renderToStaticMarkup(el);

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

ok("whitelist 只有 form/list/chat/chart", () => {
  assert.deepEqual(UI_TYPES, ["form", "list", "chat", "chart"]);
  assert.equal(Object.keys(UI_WHITELIST).length, 4);
  for (const t of UI_TYPES) assert.ok(isUiComponentType(t));
});

ok("resolve 命中 form", () => {
  const r = resolveUiSchema({ type: "form", props: { title: "X" } });
  assert.equal(r.ok, true);
  assert.equal(r.descriptor.type, "form");
  assert.equal(r.props.title, "X");
});

ok("resolve 命中 list/chat/chart", () => {
  for (const type of ["list", "chat", "chart"]) {
    const r = resolveUiSchema({ type, props: {} });
    assert.equal(r.ok, true, type);
    assert.equal(r.descriptor.type, type);
  }
});

ok("未注册类型返回友好失败", () => {
  const r = resolveUiSchema({ type: "table", props: {} });
  assert.equal(r.ok, false);
  assert.match(r.reason, /未注册/);
  assert.match(r.fallbackLabel, /table/);
});

ok("空 schema 友好失败", () => {
  const r = resolveUiSchema(null);
  assert.equal(r.ok, false);
  assert.match(r.fallbackLabel, /无效/);
});

ok("unknownTypeMessage 含可用类型", () => {
  const msg = unknownTypeMessage("table");
  assert.match(msg, /table/);
  assert.match(msg, /form/);
  assert.match(msg, /chart/);
});

ok("FormView 可渲染", () => {
  const html = render(
    e(FormView, {
      title: "表单",
      fields: [{ name: "a", label: "A" }],
    })
  );
  assert.match(html, /data-ui-type="form"/);
  assert.match(html, /表单/);
});

ok("ListView 可渲染", () => {
  const html = render(
    e(ListView, { title: "笔记列表", source: "notes.list", items: ["x", "y"] })
  );
  assert.match(html, /data-ui-type="list"/);
  assert.match(html, /笔记列表/);
  assert.match(html, /notes\.list/);
  assert.match(html, /<li/);
});

ok("ChatView 可渲染", () => {
  const html = render(
    e(ChatView, {
      title: "对话",
      messages: [{ role: "user", content: "hi" }],
    })
  );
  assert.match(html, /data-ui-type="chat"/);
  assert.match(html, /hi/);
});

ok("ChartView 可渲染", () => {
  const html = render(
    e(ChartView, {
      title: "图表",
      series: [
        { label: "A", value: 3 },
        { label: "B", value: 5 },
      ],
    })
  );
  assert.match(html, /data-ui-type="chart"/);
  assert.match(html, /图表/);
  assert.match(html, /loom-ui-bar/);
});

ok("UI_COMPONENTS 四类齐全", () => {
  assert.deepEqual(Object.keys(UI_COMPONENTS).sort(), ["chart", "chat", "form", "list"]);
});

ok("SchemaRenderer 渲染 list", () => {
  const html = render(
    e(SchemaRenderer, {
      schema: { type: "list", props: { title: "笔记列表", source: "notes.list" } },
      data: { items: ["n1"] },
    })
  );
  assert.match(html, /data-ui-type="list"/);
  assert.match(html, /n1/);
});

ok("SchemaRenderer 未注册类型显示友好提示", () => {
  const html = render(e(SchemaRenderer, { schema: { type: "table" } }));
  assert.match(html, /data-ui-type="unknown"/);
  assert.match(html, /无法渲染插件界面/);
  assert.match(html, /暂不支持的组件类型/);
  assert.match(html, /table/);
});

ok("SchemaRenderer 空 schema 显示友好提示", () => {
  const html = render(e(SchemaRenderer, { schema: null }));
  assert.match(html, /data-ui-type="unknown"/);
  assert.match(html, /无效的插件界面定义/);
});

ok("UnknownTypeNotice 可渲染", () => {
  const html = render(e(UnknownTypeNotice, { type: "gantt", reason: "未注册" }));
  assert.match(html, /gantt/);
  assert.match(html, /暂不支持的组件类型/);
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
