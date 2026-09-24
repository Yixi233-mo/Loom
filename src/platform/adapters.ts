/**
 * FE.5 三端适配 — 桌面 / 移动 / Web
 * 能力探测 + 优雅降级（无 Tauri / 无手势 API 时仍可跑）。
 */

import type { DeviceType } from "./device.ts";
import type { TauriBridge } from "./tauri-bridge.ts";

export type HostKind = "tauri-desktop" | "web" | "mobile-web";

export interface SafeAreaInsets {
  top: number;
  right: number;
  bottom: number;
  left: number;
}

export interface BreakpointInfo {
  /** sm < 768 · md 768–1279 · lg >= 1280 */
  name: "sm" | "md" | "lg";
  columns: 1 | 2 | 3;
  isMobile: boolean;
  isTablet: boolean;
  isDesktop: boolean;
}

export function detectHost(opts?: {
  hasTauri?: boolean;
  deviceType?: DeviceType;
}): HostKind {
  const hasTauri = opts?.hasTauri ?? false;
  const deviceType = opts?.deviceType;
  if (hasTauri) return "tauri-desktop";
  if (deviceType === "mobile") return "mobile-web";
  return "web";
}

export function breakpointOf(width: number, deviceType: DeviceType): BreakpointInfo {
  const name = width < 768 ? "sm" : width < 1280 ? "md" : "lg";
  const columns = name === "lg" ? 3 : name === "md" ? 2 : 1;
  return {
    name,
    columns,
    isMobile: deviceType === "mobile",
    isTablet: deviceType === "tablet",
    isDesktop: deviceType === "pc",
  };
}

/** 解析 viewport-fit=cover 的安全区（无 CSS env 时回落 0） */
export function readSafeArea(el?: {
  computedStyle?: (n: string) => string;
}): SafeAreaInsets {
  const zero = { top: 0, right: 0, bottom: 0, left: 0 };
  if (typeof getComputedStyle === "function" && el === undefined && typeof document !== "undefined") {
    const raw = getComputedStyle(document.documentElement);
    const pick = (k: string) => {
      const v = raw.getPropertyValue(k).trim();
      const n = parseFloat(v);
      return Number.isFinite(n) ? n : 0;
    };
    return {
      top: pick("--safe-top") || pick("--sat"),
      right: pick("--safe-right") || pick("--sar"),
      bottom: pick("--safe-bottom") || pick("--sab"),
      left: pick("--safe-left") || pick("--sal"),
    };
  }
  if (el?.computedStyle) {
    const num = (k: string) => {
      const v = el.computedStyle!(k);
      const n = parseFloat(v);
      return Number.isFinite(n) ? n : 0;
    };
    return {
      top: num("--safe-top"),
      right: num("--safe-right"),
      bottom: num("--safe-bottom"),
      left: num("--safe-left"),
    };
  }
  return zero;
}

export type GestureName = "swipe-left" | "swipe-right" | "swipe-up" | "swipe-down";

export interface GestureHandlers {
  onSwipeLeft?: () => void;
  onSwipeRight?: () => void;
  onSwipeUp?: () => void;
  onSwipeDown?: () => void;
}

/** 简易滑动手势识别（阈值可配，便于测试注入） */
export class GestureTracker {
  private startX = 0;
  private startY = 0;
  private tracking = false;
  private readonly threshold: number;
  private handlers: GestureHandlers = {};

  constructor(threshold = 48) {
    this.threshold = threshold;
  }

  on(handlers: GestureHandlers): void {
    this.handlers = handlers;
  }

  start(x: number, y: number): void {
    this.startX = x;
    this.startY = y;
    this.tracking = true;
  }

  end(x: number, y: number): GestureName | null {
    if (!this.tracking) return null;
    this.tracking = false;
    const dx = x - this.startX;
    const dy = y - this.startY;
    if (Math.abs(dx) < this.threshold && Math.abs(dy) < this.threshold) return null;
    let name: GestureName;
    if (Math.abs(dx) >= Math.abs(dy)) {
      name = dx < 0 ? "swipe-left" : "swipe-right";
    } else {
      name = dy < 0 ? "swipe-up" : "swipe-down";
    }
    if (name === "swipe-left") this.handlers.onSwipeLeft?.();
    if (name === "swipe-right") this.handlers.onSwipeRight?.();
    if (name === "swipe-up") this.handlers.onSwipeUp?.();
    if (name === "swipe-down") this.handlers.onSwipeDown?.();
    return name;
  }
}

/** 软键盘避让：输入聚焦时给 root 加 data-kb */
export function bindSoftKeyboard(
  root: { setAttribute: (k: string, v: string) => void; removeAttribute: (k: string) => void } | null,
  doc?: {
    addEventListener: (t: string, fn: (ev: { target: unknown }) => void) => void;
    removeEventListener: (t: string, fn: (ev: { target: unknown }) => void) => void;
  }
): () => void {
  if (!root || !doc) return () => {};
  const isInput = (t: unknown) => {
    const el = t as { tagName?: string; type?: string };
    if (!el || typeof el.tagName !== "string") return false;
    const tag = el.tagName.toLowerCase();
    return tag === "input" || tag === "textarea" || tag === "select";
  };
  const onIn = (ev: { target: unknown }) => {
    if (isInput(ev.target)) root.setAttribute("data-kb", "open");
  };
  const onOut = (ev: { target: unknown }) => {
    if (isInput(ev.target)) root.removeAttribute("data-kb");
  };
  doc.addEventListener("focusin", onIn);
  doc.addEventListener("focusout", onOut);
  return () => {
    doc.removeEventListener("focusin", onIn);
    doc.removeEventListener("focusout", onOut);
  };
}

/** 移动端返回：有历史可退则 back，否则回到默认路由 */
export function handleBack(opts: {
  canGoBack: boolean;
  onBack?: () => void;
  onFallback?: () => void;
}): boolean {
  if (opts.canGoBack) {
    opts.onBack?.();
    return true;
  }
  opts.onFallback?.();
  return false;
}

// ---------------------------------------------------------------------------
// 桌面：窗口 / 托盘 / 快捷键 / 拖拽 / 通知
// ---------------------------------------------------------------------------

export interface DesktopApi {
  setWindowTitle?: (title: string) => Promise<unknown>;
  minimizeWindow?: () => Promise<unknown>;
  toggleTray?: (visible: boolean) => Promise<unknown>;
  registerShortcut?: (combo: string) => Promise<unknown>;
  acceptFileDrop?: (paths: string[]) => Promise<unknown>;
  notify?: (title: string, body: string) => Promise<unknown>;
}

export class DesktopAdapter {
  private bridge: TauriBridge;
  private api: DesktopApi;

  constructor(bridge: TauriBridge, api: DesktopApi = {}) {
    this.bridge = bridge;
    this.api = api;
  }

  get available(): boolean {
    return this.bridge.available;
  }

  async setTitle(title: string): Promise<unknown> {
    if (this.api.setWindowTitle) return this.api.setWindowTitle(title);
    return this.bridge.invoke("set_window_title", { title });
  }

  async minimize(): Promise<unknown> {
    if (this.api.minimizeWindow) return this.api.minimizeWindow();
    return this.bridge.invoke("minimize_window");
  }

  async setTrayVisible(visible: boolean): Promise<unknown> {
    if (this.api.toggleTray) return this.api.toggleTray(visible);
    return this.bridge.invoke("set_tray_visible", { visible });
  }

  async bindShortcut(combo: string, _handler?: () => void): Promise<unknown> {
    // 真机由 Rust 全局快捷键注册；Web/Tauri mock 仅记录
    if (this.api.registerShortcut) return this.api.registerShortcut(combo);
    return this.bridge.invoke("register_shortcut", { combo });
  }

  async onFileDrop(paths: string[]): Promise<unknown> {
    if (this.api.acceptFileDrop) return this.api.acceptFileDrop(paths);
    return this.bridge.invoke("accept_file_drop", { paths });
  }

  async notify(title: string, body: string): Promise<unknown> {
    if (this.api.notify) return this.api.notify(title, body);
    // Web Notification 降级
    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      new Notification(title, { body });
      return { ok: true, via: "web-notification" };
    }
    return this.bridge.invoke("notify", { title, body });
  }
}

// ---------------------------------------------------------------------------
// Web：路由分享 / 复制链接
// ---------------------------------------------------------------------------

export function shareUrl(opts: {
  path?: string;
  query?: Record<string, string>;
  origin?: string;
  locationHref?: string;
}): string {
  const origin =
    opts.origin ??
    (opts.locationHref ? opts.locationHref.split("#")[0] : "http://localhost:5173");
  const q = opts.query
    ? "?" +
      Object.entries(opts.query)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
        .join("&")
    : "";
  const path = opts.path ?? "";
  return `${origin}#/${path.replace(/^\//, "")}${q}`.replace(/#\//, "#/").replace(/#\/\/+/, "#/");
}

export async function copyText(
  text: string,
  clipboard?: { writeText: (t: string) => Promise<void> }
): Promise<boolean> {
  try {
    if (clipboard?.writeText) {
      await clipboard.writeText(text);
      return true;
    }
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    return false;
  }
  return false;
}
