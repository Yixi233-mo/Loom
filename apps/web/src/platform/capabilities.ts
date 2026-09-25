/**
 * 设备能力桥 — 对齐 device_mesh 注册的 capabilities。
 */

import type { DeviceInfo, DeviceType } from "./device.ts";

/** 与 Python DeviceMesh / WS register 约定的能力标签 */
export const CAPABILITIES = {
  FILE_READ: "file.read",
  FILE_WRITE: "file.write",
  SHELL_EXEC: "shell.exec",
  CAMERA: "camera",
  NOTIFICATIONS: "notifications",
} as const;

export type CapabilityName = (typeof CAPABILITIES)[keyof typeof CAPABILITIES];

const BASE: CapabilityName[] = [CAPABILITIES.NOTIFICATIONS];

const BY_DEVICE: Record<DeviceType, CapabilityName[]> = {
  pc: [
    CAPABILITIES.FILE_READ,
    CAPABILITIES.FILE_WRITE,
    CAPABILITIES.SHELL_EXEC,
    CAPABILITIES.NOTIFICATIONS,
  ],
  tablet: [CAPABILITIES.FILE_READ, CAPABILITIES.NOTIFICATIONS],
  mobile: [CAPABILITIES.CAMERA, CAPABILITIES.NOTIFICATIONS],
};

export function capabilitiesFor(deviceType: DeviceType): CapabilityName[] {
  return [...(BY_DEVICE[deviceType] ?? BASE)];
}

export function registerPayload(info: DeviceInfo, deviceId: string) {
  const ts = Date.now() / 1000;
  return {
    type: "register",
    device_id: deviceId,
    device_type: info.deviceType,
    capabilities: capabilitiesFor(info.deviceType),
    ts,
  };
}

export function can(
  info: Pick<DeviceInfo, "deviceType">,
  cap: CapabilityName
): boolean {
  return capabilitiesFor(info.deviceType).includes(cap);
}
