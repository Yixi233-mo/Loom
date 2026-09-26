/**
 * 应用内诊断 — 不依赖 USB：状态、最近错误、一键复制
 */
import * as React from "react";
import { UI } from "../components/index.ts";

const e = React.createElement;

export type DiagSnapshot = {
  time: string;
  ua: string;
  online: boolean;
  hub: string;
  hubOk: boolean | null;
  lastError: string;
  route: string;
};

const ERR_KEY = "loom.lastError";

export function pushDiagError(msg: string) {
  try {
    localStorage.setItem(ERR_KEY, String(msg).slice(0, 500));
  } catch {
    /* ignore */
  }
}

export function readDiagError(): string {
  try {
    return localStorage.getItem(ERR_KEY) || "";
  } catch {
    return "";
  }
}

export async function probeHub(baseUrl = ""): Promise<boolean | null> {
  try {
    const f = (globalThis as any).fetch;
    if (!f) return null;
    const r = await f((baseUrl || "") + "/health", {
      method: "GET",
      mode: "cors",
      cache: "no-store",
    });
    return !!(r && r.ok);
  } catch {
    return false;
  }
}

export function DiagnosticsPanel(props: {
  route?: string;
  onCopy?: (text: string) => void;
}) {
  const [snap, setSnap] = React.useState<DiagSnapshot | null>(null);
  const [copied, setCopied] = React.useState(false);

  const refresh = async () => {
    const hubOk = await probeHub("");
    const s: DiagSnapshot = {
      time: new Date().toISOString(),
      ua: (globalThis as any).navigator?.userAgent || "unknown",
      online: (globalThis as any).navigator?.onLine !== false,
      hub: "http://127.0.0.1:8765/health",
      hubOk,
      lastError: readDiagError(),
      route: props.route || location.hash || "#/",
    };
    setSnap(s);
  };

  React.useEffect(() => {
    void refresh();
  }, [props.route]);

  const copy = async () => {
    const text = snap
      ? [
          "Loom 诊断",
          "time=" + snap.time,
          "route=" + snap.route,
          "online=" + snap.online,
          "hub=" + snap.hub + " ok=" + snap.hubOk,
          "lastError=" + (snap.lastError || "(none)"),
          "ua=" + snap.ua,
        ].join("\n")
      : "";
    void (props.onCopy
      ? props.onCopy(text)
      : (globalThis as any).navigator?.clipboard?.writeText(text));
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return e(
    "section",
    {
      className: "diag-panel glass",
      "data-view": "diagnostics",
      "data-testid": "diagnostics",
    },
    e("h3", null, "自检 / 诊断"),
    e(
      "p",
      { className: "hint" },
      "出问题先看这里：红点=Hub 未连上；带上这段文字发我，不用 USB 也行。"
    ),
    e(
      "div",
      { className: "diag-rows" },
      e(
        "div",
        { className: "diag-row" },
        e("span", null, "网络"),
        e(
          "strong",
          { "data-ok": snap?.online ? "1" : "0" },
          snap ? (snap.online ? "在线" : "离线") : "…"
        )
      ),
      e(
        "div",
        { className: "diag-row" },
        e("span", null, "Hub 健康"),
        e(
          "strong",
          { "data-ok": snap?.hubOk ? "1" : "0" },
          snap == null
            ? "…"
            : snap.hubOk === null
              ? "未知"
              : snap.hubOk
                ? "正常"
                : "连不上"
        )
      ),
      e(
        "div",
        { className: "diag-row" },
        e("span", null, "当前页"),
        e("strong", null, snap?.route || "…")
      ),
      e(
        "div",
        { className: "diag-row" },
        e("span", null, "最近错误"),
        e(
          "strong",
          { "data-ok": snap?.lastError ? "0" : "1" },
          snap?.lastError || "无"
        )
      )
    ),
    e(
      "div",
      { className: "diag-actions" },
      e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "diag-refresh",
          onClick: () => void refresh(),
        },
        "重新检测"
      ),
      e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonPrimary,
          "data-action": "diag-copy",
          onClick: () => void copy(),
        },
        copied ? "已复制" : "复制诊断信息"
      )
    )
  );
}

/** 全局：把未捕获错误写入诊断（供面板读取） */
export function installDiagnosticsCapture() {
  if (typeof window === "undefined") return;
  window.addEventListener("error", (ev) => {
    pushDiagError(String(ev?.message || "error"));
  });
  window.addEventListener("unhandledrejection", (ev: any) => {
    pushDiagError(String(ev?.reason || "rejection"));
  });
}
