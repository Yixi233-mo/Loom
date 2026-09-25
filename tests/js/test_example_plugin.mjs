/**
 * T13 单元测试：示例插件 UI 可显示（SchemaRenderer 渲染 plugin.ui）。
 *
 * 运行：node --experimental-strip-types tests/js/test_example_plugin.mjs
 */

import assert from "node:assert/strict";
import path from "node:path";
import { pathToFileURL, fileURLToPath } from "node:url";
import { readFileSync } from "node:fs";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(__dirname, "../..");
const tsUrl = (p) => pathToFileURL(p).href;

const modulesRoot = process.env.MIMO_NODE_MODULES;
const React = await import(tsUrl(path.join(modulesRoot, "react", "index.js")));
const ReactDOMServer = await import(
  tsUrl(path.join(modulesRoot, "react-dom", "server.js"))
);
const { SchemaRenderer } = await import(
  tsUrl(path.join(root, "apps/web/src/shell/schema-renderer.impl.ts"))
);
const { resolveUiSchema } = await import(
  tsUrl(path.join(root, "apps/web/src/shell/ui-registry.ts"))
);

const e = React.createElement ?? React.default.createElement;
const render = (el) =>
  (ReactDOMServer.renderToStaticMarkup ?? ReactDOMServer.default.renderToStaticMarkup)(el);

// plugin.json 与 Python 编译结果同源（T13 示例）
const plugin = JSON.parse(
  readFileSync(path.join(root, "plugins/example/plugin.json"), "utf8")
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

ok("plugin.json ui 结构合法", () => {
  assert.equal(plugin.name, "notes");
  assert.equal(plugin.ui.type, "list");
  assert.equal(plugin.ui.props.title, "笔记列表");
  assert.equal(plugin.ui.props.source, "notes.list");
  const r = resolveUiSchema(plugin.ui);
  assert.equal(r.ok, true);
});

ok("插件 UI 能显示 — SchemaRenderer 渲染 list", () => {
  const html = render(
    e(SchemaRenderer, {
      schema: plugin.ui,
      data: {
        items: [
          { id: "n1", title: "早会", content: "同步进度" },
          { id: "n2", title: "想法", content: "Loom 要做跨端" },
        ],
      },
    })
  );
  assert.match(html, /data-ui-type="list"/);
  assert.match(html, /笔记列表/);
  assert.match(html, /notes\.list/);
  assert.match(html, /早会/);
  assert.match(html, /Loom 要做跨端/);
});

ok("插件 UI 空数据仍可显示", () => {
  const html = render(e(SchemaRenderer, { schema: plugin.ui, data: { items: [] } }));
  assert.match(html, /data-ui-type="list"/);
  assert.match(html, /暂无数据/);
});

console.log(`\n${passed} passed`);
if (process.exitCode) console.log("FAILED");
else console.log("ALL PASS");
