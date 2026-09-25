/**
 * E3 说话即任务 — 从自然语言生成任务预览（不暴露 YAML）
 * E2 — 三步接入文案（扫码 / 授权 / 贴 Key）
 */
import * as React from "react";
import { UI } from "../components/index.ts";

const e = React.createElement;

export type TaskPreview = {
  title: string;
  trigger: string;
  steps: string[];
  device: string;
  sourceText: string;
};

const TRIGGER_RE =
  /(每周[一二三四五六日天]?|每天|每月|定时|cron|工作流|汇总|自动|触发|发到|推送)/i;

/** 是否像一条「要固化成任务」的说话 */
export function looksLikeTask(text: string): boolean {
  const t = (text || "").trim();
  if (t.length < 6) return false;
  return TRIGGER_RE.test(t) && /(帮我|帮我|请|汇总|发送|生成|整理|执行|跑)/.test(t);
}

/** 从自然语言解析任务预览（启发式，用户确认后才创建） */
export function parseTaskPreview(text: string): TaskPreview | null {
  if (!looksLikeTask(text)) return null;
  const t = text.trim();
  let trigger = "手动运行（对我说「跑一遍」）";
  if (/每周一/.test(t)) trigger = "每周一 9:00";
  else if (/每周/.test(t)) trigger = "每周 9:00";
  else if (/每天|每日/.test(t)) trigger = "每天 9:00";
  else if (/每月/.test(t)) trigger = "每月 1 日 9:00";
  else if (/早上|上午/.test(t)) trigger = "每天 9:00";
  else if (/定时|cron/i.test(t)) trigger = "按描述的时间触发";

  const steps: string[] = [];
  if (/周报|日报|月报|汇总|总结/.test(t)) steps.push("收集相关内容");
  if (/飞书|微信|钉钉|邮件|发送|发到|推送/.test(t)) steps.push("通知到目标渠道");
  if (/LLM|大模型|AI|生成|润色|写/.test(t)) steps.push("用当前模型生成结果");
  if (steps.length === 0) steps.push("执行你描述的动作");

  let device = "自动选择（PC 优先）";
  if (/手机/.test(t)) device = "手机";
  else if (/PC|电脑/.test(t)) device = "PC";

  return {
    title: t.length > 28 ? t.slice(0, 28) + "…" : t,
    trigger,
    steps,
    device,
    sourceText: t,
  };
}

export function TaskPreviewCard(props: {
  preview: TaskPreview;
  onConfirm?: (p: TaskPreview) => void;
  onCancel?: () => void;
}) {
  const p = props.preview;
  return e(
    "div",
    {
      className: "task-preview glass",
      "data-view": "task-preview",
      "data-testid": "task-preview",
    },
    e("div", { className: "task-preview-title" }, "任务预览 · 确认后才会创建"),
    e(
      "div",
      { className: "task-preview-body" },
      e("div", { className: "tp-row" }, e("b", null, "任务"), e("span", null, p.title)),
      e("div", { className: "tp-row" }, e("b", null, "触发"), e("span", null, p.trigger)),
      e("div", { className: "tp-row" }, e("b", null, "执行"), e("span", null, p.device)),
      e(
        "div",
        { className: "tp-row" },
        e("b", null, "步骤"),
        e(
          "ol",
          { className: "tp-steps" },
          p.steps.map((s, i) => e("li", { key: i }, s))
        )
      )
    ),
    e(
      "div",
      { className: "task-preview-actions" },
      e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonPrimary,
          "data-action": "confirm-task-preview",
          onClick: () => props.onConfirm?.(p),
        },
        "确认创建"
      ),
      e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "cancel-task-preview",
          onClick: () => props.onCancel?.(),
        },
        "再改改"
      )
    )
  );
}

/** E2 · 三步接入 */
export const CONNECT_STEPS = [
  {
    id: "scan",
    icon: "▣",
    title: "扫码连接",
    desc: "手机 / 桌面设备扫一扫，立刻出现在「跨端」。",
    action: "devices",
    cta: "去跨端",
  },
  {
    id: "auth",
    icon: "🔐",
    title: "一键授权",
    desc: "Claude Code、Work Buddy 等本地 Agent 一键接入。",
    action: "mcp",
    cta: "去接入",
  },
  {
    id: "key",
    icon: "🔑",
    title: "粘贴 API Key",
    desc: "DeepSeek / Ollama / 自定义模型，贴上就能用。",
    action: "settings",
    cta: "去配置",
  },
] as const;

export function ConnectWizard(props: {
  onOpen?: (action: "devices" | "mcp" | "settings") => void;
}) {
  return e(
    "div",
    {
      className: "connect-wizard glass",
      "data-view": "connect-wizard",
      "data-testid": "connect-wizard",
    },
    e(
      "div",
      { className: "connect-wizard-head" },
      e("h3", null, "30 秒接入你的 AI"),
      e("p", { className: "hint" }, "不用学 MCP / 配置文件。三选一，接完就能在对话里用。")
    ),
    e(
      "div",
      { className: "connect-wizard-grid" },
      CONNECT_STEPS.map((s) =>
        e(
          "div",
          { key: s.id, className: "connect-step", "data-step": s.id },
          e("div", { className: "connect-step-icon", "aria-hidden": "true" }, s.icon),
          e("strong", null, s.title),
          e("p", null, s.desc),
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonGhost,
              "data-action": `connect-${s.id}`,
              onClick: () => props.onOpen?.(s.action),
            },
            s.cta
          )
        )
      )
    )
  );
}
