/**
 * FE.2 设计 Token — 类型化导出（供 JS/测试引用，与 tokens.css 同步）。
 * 组件优先用 CSS 变量；仅在需要 JS 分支（如技能树状态）时读本表。
 */

export type ThemeName = "light" | "dark";

export type ColorSemanticKey =
  | "bg"
  | "bgElevated"
  | "panel"
  | "ink"
  | "muted"
  | "accent"
  | "accentStrong"
  | "accentSoft"
  | "success"
  | "warn"
  | "danger"
  | "sage"
  | "champagne"
  | "nodeOn"
  | "nodeOff";

export type SpaceScaleKey =
  | "0"
  | "1"
  | "2"
  | "3"
  | "4"
  | "5"
  | "6"
  | "7"
  | "8"
  | "9"
  | "10";

export type RadiusKey = "xs" | "sm" | "md" | "lg" | "xl" | "pill";

export type TextScaleKey =
  | "2xs"
  | "xs"
  | "sm"
  | "md"
  | "lg"
  | "xl"
  | "2xl"
  | "3xl"
  | "display";

export type ShadowKey = "sm" | "md" | "lg";

/** CSS 变量名（字符串字面量，便于校验） */
export const CSS_VARS = {
  bg: "--bg",
  panel: "--panel",
  ink: "--ink",
  muted: "--muted",
  accent: "--accent",
  accentHover: "--accent-hover",
  accentActive: "--accent-active",
  accentStrong: "--accent-strong",
  accentSoft: "--accent-soft",
  success: "--success",
  warn: "--warn",
  danger: "--danger",
  sage: "--sage",
  champagne: "--champagne",
  nodeOn: "--node-on",
  nodeOff: "--node-off",
  space: (n: SpaceScaleKey) => `--space-${n}`,
  radius: (k: RadiusKey) => (k === "pill" ? "--radius-pill" : `--radius-${k}`),
  text: (k: TextScaleKey) => `--text-${k}`,
  shadow: (k: ShadowKey) => `--shadow-${k}`,
  duration: (k: "fast" | "normal" | "slow") => `--duration-${k}`,
  fontBody: "--font-body",
  fontDisplay: "--font-display",
  fontMono: "--font-mono",
} as const;

export const THEMES: readonly ThemeName[] = ["light", "dark"];

export function isThemeName(v: unknown): v is ThemeName {
  return v === "light" || v === "dark";
}

/** 技能树节点状态 → 语义色 token */
export type SkillNodeState = "on" | "off" | "half";

export const SKILL_NODE_VAR: Record<SkillNodeState, string> = {
  on: "--node-on",
  half: "--node-half",
  off: "--node-off",
};

export function themeAttr(theme: ThemeName): { "data-theme": ThemeName } {
  return { "data-theme": theme };
}

/** 设计文档锚点（token 文件相对路径） */
export const TOKEN_DOC_PATH = "src/styles/tokens.css";
