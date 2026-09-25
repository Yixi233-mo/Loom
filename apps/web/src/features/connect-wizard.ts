/**
 * E3 说话即任务 — 从自然语言生成任务预览（不暴露 YAML）
 * E2 — 三步接入文案（扫码 / 授权 / 贴 Key）
 */
import * as React from "react";
import { UI } from "../components/index.ts";
import { qrToSvg } from "./qr-code.ts";
import { CameraScanner } from "./camera-scan.ts";

const e = React.createElement;

/** 旧 WebView 兼容：clipboard / crypto 不存在时不抛 */
export function safeClipboard(text: string): Promise<boolean> {
  try {
    const n: any = (globalThis as any).navigator;
    if (n?.clipboard?.writeText) return n.clipboard.writeText(text).then(() => true, () => false);
  } catch {
    /* ignore */
  }
  try {
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    document.body.appendChild(ta);
    ta.select();
    const ok = document.execCommand && document.execCommand("copy");
    document.body.removeChild(ta);
    return Promise.resolve(!!ok);
  } catch {
    return Promise.resolve(false);
  }
}


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
/** 配对码：6 位大写字母数字（去掉易混字符） */
export function makePairingCode(len = 6): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  let out = "";
  const buf = new Uint8Array(len);
  if (typeof globalThis.crypto?.getRandomValues === "function") {
    globalThis.crypto.getRandomValues(buf);
  } else {
    for (let i = 0; i < len; i++) buf[i] = Math.floor(Math.random() * 256);
  }
  for (let i = 0; i < len; i++) out += alphabet[buf[i] % alphabet.length];
  return out;
}

export type PairingInfo = {
  code: string;
  /** 手机扫描或打开的地址 */
  url: string;
  /** 设备接入用 WS / hub 地址 */
  hub: string;
  host: string;
  port: number;
};

export function buildPairingInfo(
  code?: string,
  locationLike?: { hostname?: string; port?: string; protocol?: string }
): PairingInfo {
  const loc = locationLike ?? (globalThis as any).location ?? {};
  const host = loc.hostname && loc.hostname !== "" ? String(loc.hostname) : "127.0.0.1";
  const port = Number(loc.port || 8765) || 8765;
  const c = code || makePairingCode();
  const origin =
    loc.protocol && loc.protocol.startsWith("http")
      ? `${loc.protocol}//${host}${loc.port ? ":" + loc.port : ""}`
      : `http://${host}:5173`;
  return {
    code: c,
    url: `${origin}/#/devices?pair=${c}&host=${encodeURIComponent(host)}&port=${port}`,
    hub: `ws://${host}:${port}/ws`,
    host,
    port,
  };
}

/** 配对面板：真二维码 + 配对码 + 复制链接 + 手动填地址 */
export function PairingPanel(props: {
  pairing?: PairingInfo;
  onRefresh?: () => void;
  onPair?: (info: PairingInfo) => void;
  compact?: boolean;
}) {
  const [info, setInfo] = React.useState<PairingInfo | null>(props.pairing ?? null);
  const [copied, setCopied] = React.useState(false);
  const [manualHost, setManualHost] = React.useState("");
  const [manualPort, setManualPort] = React.useState("8765");
  const [err, setErr] = React.useState("");

  React.useEffect(() => {
    if (!info) setInfo(buildPairingInfo());
  }, [info]);

  const refresh = () => {
    const next = buildPairingInfo();
    setInfo(next);
    setCopied(false);
    props.onRefresh?.();
  };

  const svg = info ? qrToSvg(info.url, { scale: 5, margin: 2 }) : "";

  return e(
    "div",
    {
      className: "pairing-panel",
      "data-view": "pairing-panel",
      "data-testid": "pairing-panel",
    },
    e(
      "div",
      { className: "pairing-qr-wrap", "data-testid": "pairing-qr" },
      info
        ? e("div", {
            className: "pairing-qr",
            dangerouslySetInnerHTML: { __html: svg },
          })
        : e("div", { className: "pairing-qr-empty" }, "生成中…"),
      e("div", { className: "pairing-caption" }, "用手机相机或 Loom 扫一扫连接本机")
    ),
    e(
      "div",
      { className: "pairing-side" },
      e(
        "div",
        { className: "pairing-code" },
        e("span", { className: "pairing-code-label" }, "配对码"),
        e("strong", { className: "pairing-code-value", "data-testid": "pairing-code" }, info?.code || "------"),
        e(
          "button",
          {
            type: "button",
            className: UI.button + " " + UI.buttonGhost,
            "data-action": "pairing-refresh",
            onClick: refresh,
          },
          "换一组"
        )
      ),
      e(
        "div",
        { className: "pairing-url" },
        e("span", { className: "pairing-code-label" }, "连接地址"),
        e("code", null, info?.hub || ""),
        e(
          "button",
          {
            type: "button",
            className: UI.button + " " + UI.buttonGhost,
            "data-action": "pairing-copy",
            onClick: () => {
              const text = info ? `${info.url}\n${info.hub}` : "";
              void safeClipboard(text).then((ok) => setCopied(!!ok));
            },
          },
          copied ? "已复制" : "复制链接"
        )
      ),
      e(
        "div",
        { className: "pairing-manual" },
        e("span", { className: "pairing-code-label" }, "没有扫码？手动填本机地址"),
        e(
          "div",
          { className: "pairing-manual-row" },
          e("input", {
            className: "pairing-input",
            placeholder: "主机 IP 或 127.0.0.1",
            value: manualHost,
            "data-field": "pair-host",
            onChange: (ev: any) => setManualHost(String(ev.target.value || "")),
          }),
          e("input", {
            className: "pairing-input pairing-input-port",
            placeholder: "端口",
            value: manualPort,
            "data-field": "pair-port",
            onChange: (ev: any) => setManualPort(String(ev.target.value || "")),
          }),
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonPrimary,
              "data-action": "pairing-submit",
              onClick: () => {
                const host = manualHost.trim() || info?.host || "127.0.0.1";
                const port = Number(manualPort) || 8765;
                if (!host) {
                  setErr("请填写主机地址");
                  return;
                }
                setErr("");
                const next = buildPairingInfo(makePairingCode(), {
                  hostname: host,
                  port: String(port),
                  protocol: "http:",
                });
                setInfo(next);
                props.onPair?.(next);
              },
            },
            "连接"
          )
        ),
        err ? e("p", { className: "pairing-err" }, err) : null
      ),
      props.compact
        ? null
        : e(
            "p",
            { className: "pairing-help" },
            "手机与本机需在同一局域网。扫码失败时，用配对码或「主机:端口」同样可以连上。"
          )
    )
  );
}

/** E2 · 三步接入（无 emoji） */
export const CONNECT_STEPS = [
  {
    id: "scan",
    icon: "01",
    title: "扫码连接",
    desc: "展示本机二维码与配对码，手机扫一扫即接入。",
    action: "scan" as const,
    cta: "刷新二维码",
  },
  {
    id: "auth",
    icon: "02",
    title: "一键授权",
    desc: "Claude Code、Work Buddy 等本地 Agent 授权接入。",
    action: "mcp" as const,
    cta: "去接入",
  },
  {
    id: "key",
    icon: "03",
    title: "粘贴 API Key",
    desc: "DeepSeek / Ollama / 自定义模型，贴上就能用。",
    action: "settings" as const,
    cta: "去配置",
  },
] as const;

export function ConnectWizard(props: {
  onOpen?: (action: "devices" | "mcp" | "settings" | "scan") => void;
}) {
  const [showPair, setShowPair] = React.useState(true);
  const [showScan, setShowScan] = React.useState(false);

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
      e(
        "p",
        { className: "hint" },
        "不用学 MCP / 配置文件。扫码或填配对码即可连上本机。"
      )
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
              onClick: () => {
                if (s.action === "scan") {
                  // 移动端优先相机扫码；桌面仍可看二维码
                  setShowScan((v) => !v);
                  props.onOpen?.("scan");
                  return;
                }
                props.onOpen?.(s.action);
              },
            },
            s.action === "scan" ? (showScan ? "关闭相机扫码" : "打开相机扫码") : s.cta
          )
        )
      )
    ),
    showScan
      ? e(CameraScanner, {
          onResult: (_r) => {
            setShowScan(false);
            setShowPair(true);
            props.onOpen?.("devices");
          },
          onClose: () => setShowScan(false),
        })
      : showPair
        ? e(PairingPanel, {
            onPair: () => props.onOpen?.("devices"),
          })
        : null
  );
}
