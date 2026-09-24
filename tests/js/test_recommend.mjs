/**
 * 推荐 Agent 卡片 — 毛玻璃 / 启动 / 展开详情
 */
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import * as React from "react";
import { RecommendPage, RECOMMENDED_AGENTS } from "../../src/features/recommend-page.ts";

const e = React.createElement;
const apps = RECOMMENDED_AGENTS;
assert.ok(apps.length >= 15);

const html = renderToStaticMarkup(
  e(RecommendPage, {
    launchState: { claude_code: "ok", deepseek: "missing" },
    onLaunch: () => {},
  })
);

assert.match(html, /data-page="recommend"/);
assert.match(html, /Claude Code/);
assert.match(html, /Work Buddy/);
assert.match(html, /DeepSeek/);
assert.match(html, /Codex/);
assert.match(html, /千问|Qwen/);
assert.match(html, /Trea|Trae/);
assert.match(html, /Pi/);
assert.match(html, /ChatGPT/);
assert.match(html, /Kimi/);
assert.match(html, /toggle-agent-detail/);
assert.match(html, /launch-agent/);
assert.match(html, /data-launch="ok"/);
assert.match(html, /data-launch="missing"/);
assert.match(html, /展开详情/);
assert.match(html, /agent-card glass/);
// details hidden until expand (default)
assert.doesNotMatch(html, /data-view="agent-detail"/);

const app = await import("node:fs");
const appSrc = app.readFileSync("src/App.tsx", "utf8");
assert.match(appSrc, /recommend/);
assert.match(appSrc, /RecommendPage/);

console.log("test_recommend: ALL PASS");
