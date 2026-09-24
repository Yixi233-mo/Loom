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

/** 布局模式：三栏 / 双栏 / 单栏 */
export type LayoutMode = "wide" | "medium" | "narrow";

export function layoutFor(deviceType: DeviceType): LayoutMode {
  if (deviceType === "pc") return "wide";
  if (deviceType === "tablet") return "medium";
  return "narrow";
}
