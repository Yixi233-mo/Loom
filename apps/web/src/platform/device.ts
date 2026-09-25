/**
 * 平台层 — 三端设备探测 / Tauri IPC / 能力声明。
 */

export type DeviceType = "pc" | "tablet" | "mobile";

export interface DeviceInfo {
  deviceType: DeviceType;
  /** 逻辑视口宽度（px） */
  width: number;
  height: number;
  /** 是否可跑 shell 能力（PC 优先） */
  canShellExec: boolean;
  platform: string;
}

export function detectDeviceType(width: number, height?: number): DeviceType {
  void height;
  if (width < 768) return "mobile";
  if (width < 1280) return "tablet";
  return "pc";
}

/** U3：四档视口 — xl 宽屏 / lg 中屏 / md 窄栏 / sm 移动 */
export type BpName = "sm" | "md" | "lg" | "xl";

export function breakpointName(width: number): BpName {
  if (width < 768) return "sm";
  if (width < 1024) return "md";
  if (width < 1280) return "lg";
  return "xl";
}

export function detectDevice(
  width?: number,
  height?: number
): DeviceInfo {
  const w = width ?? (typeof window !== "undefined" ? window.innerWidth : 1280);
  const h = height ?? (typeof window !== "undefined" ? window.innerHeight : 800);
  const deviceType = detectDeviceType(w, h);
  const platform =
    typeof navigator !== "undefined" ? navigator.platform || "unknown" : "unknown";
  return {
    deviceType,
    width: w,
    height: h,
    canShellExec: deviceType === "pc",
    platform,
  };
}

/**
 * 布局四档（U3）：
 * wide 宽屏侧栏 | medium 中屏侧栏 | compact 图标栏 | narrow 移动 Tab+抽屉
 */
export type LayoutMode = "wide" | "medium" | "compact" | "narrow";

export function layoutFor(
  deviceType: DeviceType,
  width?: number
): LayoutMode {
  const w = width ?? (typeof window !== "undefined" ? window.innerWidth : 1280);
  const bp = breakpointName(w);
  if (bp === "sm") return "narrow";
  if (bp === "md") return "compact";
  if (bp === "lg") return "medium";
  // xl：桌面宽屏；小高度设备仍走 medium
  return deviceType === "mobile" ? "narrow" : "wide";
}
