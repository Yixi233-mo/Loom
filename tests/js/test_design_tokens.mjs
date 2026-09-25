/**
 * FE.2 设计 Token 验收测试
 * run: node --experimental-strip-types tests/js/test_design_tokens.mjs
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import {
  CSS_VARS,
  THEMES,
  SKILL_NODE_VAR,
  isThemeName,
  themeAttr,
  TOKEN_DOC_PATH,
} from "../../apps/web/src/styles/tokens.ts";

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const tokensCss = readFileSync(join(root, "apps/web/src/styles/tokens.css"), "utf8");
const baseCss = readFileSync(join(root, "apps/web/src/styles/base.css"), "utf8");
const componentsCss = readFileSync(join(root, "apps/web/src/styles/components.css"), "utf8");
const indexCss = readFileSync(join(root, "apps/web/src/styles/index.css"), "utf8");
const doc = readFileSync(join(root, "apps/web/src/styles/README.md"), "utf8");

function mustDefine(css, name) {
  assert.ok(css.includes(`${name}:`), `tokens.css 应定义 ${name}`);
}

// --- 关键 semantic token 必须存在 ---
{
  const required = [
    "--bg",
    "--bg-elevated",
    "--bg-glow",
    "--panel",
    "--ink",
    "--muted",
    "--accent",
    "--accent-strong",
    "--accent-soft",
    "--success",
    "--warn",
    "--danger",
    "--sage",
    "--champagne",
    "--node-on",
    "--node-off",
    "--node-half",
    "--glass-bg",
    "--glass-blur",
    "--shadow-sm",
    "--shadow-md",
    "--shadow-lg",
    "--font-body",
    "--font-display",
    "--font-mono",
  ];
  for (const name of required) mustDefine(tokensCss, name);
}

// --- 间距 / 圆角 / 字号 ---
{
  for (let i = 0; i <= 10; i++) mustDefine(tokensCss, `--space-${i}`);
  for (const r of ["xs", "sm", "md", "lg", "xl", "pill"]) {
    mustDefine(tokensCss, `--radius-${r}`);
  }
  for (const t of ["2xs", "xs", "sm", "md", "lg", "xl", "2xl", "3xl", "display"]) {
    mustDefine(tokensCss, `--text-${t}`);
  }
  for (const s of ["sm", "md", "lg"]) mustDefine(tokensCss, `--shadow-${s}`);
}

// --- 主题 ---
{
  assert.ok(tokensCss.includes('[data-theme="light"]'));
  assert.ok(tokensCss.includes('[data-theme="dark"]'));
  assert.deepEqual([...THEMES], ["light", "dark"]);
  assert.equal(isThemeName("light"), true);
  assert.equal(isThemeName("blue"), false);
  assert.deepEqual(themeAttr("dark"), { "data-theme": "dark" });
}

// --- 技能树状态 ---
{
  assert.equal(SKILL_NODE_VAR.on, "--node-on");
  assert.equal(SKILL_NODE_VAR.half, "--node-half");
  assert.equal(SKILL_NODE_VAR.off, "--node-off");
  assert.ok(componentsCss.includes(".ui-skill-node--on"));
  assert.ok(componentsCss.includes(".ui-skill-node--off"));
}

// --- CSS_VARS 映射 ---
{
  assert.equal(CSS_VARS.accent, "--accent");
  assert.equal(CSS_VARS.space("4"), "--space-4");
  assert.equal(CSS_VARS.radius("pill"), "--radius-pill");
  assert.equal(CSS_VARS.radius("md"), "--radius-md");
  assert.equal(CSS_VARS.text("display"), "--text-display");
  assert.equal(CSS_VARS.shadow("lg"), "--shadow-lg");
  assert.equal(CSS_VARS.duration("normal"), "--duration-normal");
}

// --- 样式入口串联 ---
{
  assert.ok(indexCss.includes('import "./tokens.css"'));
  assert.ok(indexCss.includes('import "./base.css"'));
  assert.ok(indexCss.includes('import "./components.css"'));
  assert.ok(baseCss.includes("var(--bg)"));
  assert.ok(componentsCss.includes("var(--glass-bg)"));
}

// --- 文档说明 ---
{
  assert.ok(doc.includes("设计系统 Token"));
  assert.ok(doc.includes("--accent"));
  assert.ok(doc.includes("data-theme"));
  assert.ok(TOKEN_DOC_PATH.endsWith("tokens.css"));
}

console.log("test_design_tokens: ALL PASS");
