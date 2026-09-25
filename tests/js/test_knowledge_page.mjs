/**
 * 知识库页 — 选库/新建库 + 外部源卡片结构验收
 * run: node --experimental-strip-types tests/js/test_knowledge_page.mjs
 */
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";
import { KnowledgePage } from "../../src/features/knowledge-page.ts";

const e = React.createElement;

function mockRest(overrides = {}) {
  return {
    requestPublic: async (path) => {
      if (path.includes("/kbs")) {
        return {
          items: [
            { id: "builtin", name: "内置知识库", count: 1 },
            { id: "产品文档", name: "产品文档", count: 0 },
          ],
        };
      }
      if (path.includes("/docs")) {
        return {
          items: [
            {
              id: "d1",
              title: "部署流程",
              content: "docker",
              tags: ["运维"],
              source: "manual",
              kb: "builtin",
            },
          ],
        };
      }
      if (path.includes("/sources")) {
        return {
          items: [
            {
              id: "vec1",
              kind: "vector",
              name: "向量演示",
              health: { ok: true },
            },
          ],
        };
      }
      return overrides.fallback ?? {};
    },
  };
}

const html = renderToStaticMarkup(
  e(KnowledgePage, { rest: mockRest() })
);

// 选库 / 新建库
assert.match(html, /data-view="kb-switch"/);
assert.match(html, /data-field="kb-select"/);
assert.match(html, /data-field="kb-new"/);
assert.match(html, /data-field="kb-new-name"/);
assert.match(html, /data-action="kb-create"/);
assert.match(html, /当前知识库/);
assert.match(html, /新建库/);
assert.match(html, /data-view="kb-current"/);
assert.match(html, /data-view="kb-add-target"/);
// 受控 select 即便 kbs 未载入也有合法选项
assert.match(html, /<option value="builtin"/);

// 外部源卡片（静态首屏：表单；列表项在数据到达后渲染）
assert.match(html, /data-view="kb-sources"/);
assert.match(html, /data-action="kb-source-add"/);
assert.match(html, /data-action="kb-source-test-form"/);
assert.match(html, /data-field="src-kind"/);
assert.match(html, /data-field="src-id"/);
// 本地文件导入（像打开文件一样）
assert.match(html, /data-action="kb-import-file"/);
assert.match(html, /data-action="kb-import-path"/);
assert.match(html, /data-field="kb-import-file"/);
assert.match(html, /data-field="kb-import-path"/);
assert.match(html, /自动识别/);

// 列表与添加（首屏 loading，列表容器在数据到达后出现）
assert.match(html, /data-action="kb-add"/);
assert.match(html, /data-action="kb-search"/);
assert.match(html, /data-field="kb-title"/);

// App 路由挂载
import { readFileSync } from "node:fs";
const app = readFileSync("src/App.tsx", "utf8");
assert.match(app, /KnowledgePage/);
assert.match(app, /knowledge/);

console.log("test_knowledge_page: ALL PASS");
