/**
 * 平台层入口 — 三端适配（F4 + FE.5）。
 */

export {
  detectDevice,
  detectDeviceType,
  layoutFor,
  breakpointName,
  type BpName,
  type DeviceInfo,
  type DeviceType,
  type LayoutMode,
} from "./device.ts";

export {
  TauriBridge,
  getTauri,
  type TauriInvokeArgs,
  type TauriLike,
} from "./tauri-bridge.ts";

export {
  CAPABILITIES,
  capabilitiesFor,
  registerPayload,
  can,
  type CapabilityName,
} from "./capabilities.ts";

export {
  detectHost,
  breakpointOf,
  readSafeArea,
  GestureTracker,
  bindSoftKeyboard,
  handleBack,
  DesktopAdapter,
  shareUrl,
  copyText,
  type HostKind,
  type BreakpointInfo,
  type SafeAreaInsets,
  type GestureName,
  type GestureHandlers,
  type DesktopApi,
} from "./adapters.ts";

import { detectDevice, layoutFor, type DeviceInfo, type LayoutMode } from "./device.ts";
import { TauriBridge } from "./tauri-bridge.ts";
import { capabilitiesFor, type CapabilityName } from "./capabilities.ts";
import {
  detectHost,
  breakpointOf,
  DesktopAdapter,
  type HostKind,
  type BreakpointInfo,
} from "./adapters.ts";

export interface PlatformLayer {
  device: DeviceInfo;
  layout: LayoutMode;
  capabilities: CapabilityName[];
  tauri: TauriBridge;
  host: HostKind;
  breakpoint: BreakpointInfo;
  desktop: DesktopAdapter;
}

export function createPlatformLayer(
  width?: number,
  height?: number,
  tauriImpl?: any
): PlatformLayer {
  const device = detectDevice(width, height);
  const tauri = new TauriBridge(tauriImpl);
  return {
    device,
    layout: layoutFor(device.deviceType, device.width),
    capabilities: capabilitiesFor(device.deviceType),
    tauri,
    host: detectHost({ hasTauri: tauri.available, deviceType: device.deviceType }),
    breakpoint: breakpointOf(device.width, device.deviceType),
    desktop: new DesktopAdapter(tauri),
  };
}
