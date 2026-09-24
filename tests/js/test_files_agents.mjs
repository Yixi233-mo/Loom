/**
 * 文件页 / Agent 页 — 验收
 */
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";
import { FilesPage } from "../../src/features/files-page.ts";
import { AgentsPage } from "../../src/features/agents-page.ts";
import { createServiceLayer } from "../../src/services/index.ts";
import { readFileSync } from "node:fs";

const e = React.createElement;
const services = createServiceLayer({
  restFetch: async () => ({
    ok: true,
    status: 200,
    json: async () => [],
    text: async () => "[]",
  }),
  uploadFetch: async () => ({
    ok: true,
    status: 200,
    json: async () => ({
      fileId: "f1",
      name: "a.md",
      size: 3,
      mime: "text/markdown",
      uri: "hub://f1",
    }),
    text: async () => "",
  }),
});

const filesHtml = renderToStaticMarkup(e(FilesPage, { services }));
assert.match(filesHtml, /data-page="files"/);
assert.match(filesHtml, /file-input/);
assert.match(filesHtml, /还没有文件/);

const agentsHtml = renderToStaticMarkup(
  e(AgentsPage, {
    agents: [
      {
        agentName: "builtin_rag",
        status: "online",
        capabilities: ["rag.query"],
        degradationLevel: 0,
        updatedAt: Date.now(),
      },
    ],
  })
);
assert.match(agentsHtml, /data-page="agents"/);
assert.match(agentsHtml, /builtin_rag/);
assert.match(agentsHtml, /test-agent/);

const app = readFileSync("src/App.tsx", "utf8");
assert.match(app, /FilesPage/);
assert.match(app, /AgentsPage/);

console.log("test_files_agents: ALL PASS");
