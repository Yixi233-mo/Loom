/**
 * FE.1 统一通信门面 — REST / 实时事件 / Tauri IPC 收口。
 * 视图与 features 只依赖本模块，不直连底层 transport。
 */

export type {
  SessionState,
  SessionMessage,
  TaskState,
  TaskResult,
  TaskStatus,
  AgentState,
  AgentStatus,
  FileRef,
} from "../contracts/index.ts";

import type { FileRef } from "../contracts/index.ts";
import {
  createServiceLayer,
  type ServiceLayer,
  RestClient,
  EventBus,
  FileService,
  LlmApi,
  ModelChatClient,
} from "../services/index.ts";
import {
  createPlatformLayer,
  type PlatformLayer,
  registerPayload,
  type TauriLike,
} from "../platform/index.ts";

export interface ApiContext {
  services: ServiceLayer;
  platform: PlatformLayer;
  modelChat: ModelChatClient;
}

export interface ApiBootOptions {
  baseUrl?: string;
  restFetch?: import("../services/rest.ts").FetchLike;
  uploadFetch?: import("../services/file-service.ts").UploadFetch;
  width?: number;
  height?: number;
  tauriImpl?: TauriLike | null;
}

export function createApiContext(opts?: ApiBootOptions): ApiContext {
  const services = createServiceLayer({
    baseUrl: opts?.baseUrl ?? "",
    restFetch: opts?.restFetch,
    uploadFetch: opts?.uploadFetch,
  });
  const platform = createPlatformLayer(
    opts?.width,
    opts?.height,
    opts?.tauriImpl ?? null
  );
  return {
    services,
    platform,
    modelChat: new ModelChatClient(),
  };
}

export function refreshPlatform(
  api: ApiContext,
  width?: number,
  height?: number
): PlatformLayer {
  const next = createPlatformLayer(
    width,
    height,
    api.platform.tauri.impl ?? null
  );
  api.platform = next;
  return next;
}

export function deviceRegisterPayload(
  api: ApiContext
): ReturnType<typeof registerPayload> {
  return registerPayload(
    api.platform.device,
    `web-${api.platform.device.deviceType}-1`
  );
}

export interface LocalFileInput {
  name: string;
  type: string;
  size: number;
  content?: string;
}

export function uploadFile(
  api: ApiContext,
  file: LocalFileInput,
  sourceDeviceId?: string
): Promise<FileRef> {
  return api.services.files.upload(file, sourceDeviceId);
}

export function listFiles(api: ApiContext): Promise<FileRef[]> {
  return api.services.files.list();
}

export function removeFile(api: ApiContext, fileId: string): Promise<unknown> {
  return api.services.files.delete(fileId);
}

export { RestClient, EventBus, FileService, LlmApi, ModelChatClient };
