/**
 * 平台层入口 — 三端适配（F4）。
 */

export {
  detectDevice,
  detectDeviceType,
  layoutFor,
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

import { detectDevice, layoutFor, type DeviceInfo, type LayoutMode } from "./device.ts";
import { TauriBridge } from "./tauri-bridge.ts";
import { capabilitiesFor, type CapabilityName } from "./capabilities.ts";

export interface PlatformLayer {
  device: DeviceInfo;
  layout: LayoutMode;
  capabilities: CapabilityName[];
  tauri: TauriBridge;
}

export function createPlatformLayer(
  width?: number,
  height?: number,
  tauriImpl?: any
): PlatformLayer {
  const device = detectDevice(width, height);
  return {
    device,
    layout: layoutFor(device.deviceType),
    capabilities: capabilitiesFor(device.deviceType),
    tauri: new TauriBridge(tauriImpl),
  };
}
