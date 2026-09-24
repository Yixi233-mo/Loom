/**
 * 文件上传 — Hub 集中存储，返回 FileRef。
 */

import { API, EVENTS, type FileRef } from "../contracts/index.ts";
import type { EventBus } from "./event-bus.ts";
import type { RestClient } from "./rest.ts";

export interface UploadProgress {
  loaded: number;
  total: number;
}

export type UploadFetch = (
  input: string,
  init?: {
    method?: string;
    body?: any;
    headers?: Record<string, string>;
  }
) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<any>;
  text(): Promise<string>;
}>;

export class FileService {
  rest: RestClient;
  bus: EventBus;
  fetchImpl?: UploadFetch;

  constructor(rest: RestClient, bus: EventBus, fetchImpl?: UploadFetch) {
    this.rest = rest;
    this.bus = bus;
    this.fetchImpl = fetchImpl;
  }

  async upload(
    file: {
      name: string;
      type: string;
      size: number;
      content?: string;
    },
    sourceDeviceId?: string
  ): Promise<FileRef> {
    const f: UploadFetch =
      this.fetchImpl ??
      ((input, init) => (globalThis as any).fetch(input, init) as any);

    // JSON 简化上传；二进制可扩展 multipart
    const body = {
      name: file.name,
      mime: file.type || "application/octet-stream",
      size: file.size,
      sourceDeviceId,
      content: file.content,
    };

    const res = await f(API.FILE_UPLOAD, {
      method: "POST",
      body: JSON.stringify(body),
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) {
      throw new Error(`上传失败 HTTP ${res.status}`);
    }
    const ref = (await res.json()) as FileRef;
    this.bus.emit({ type: EVENTS.FILE_UPLOADED, file: ref });
    return ref;
  }

  list(): Promise<FileRef[]> {
    return this.rest.listFiles();
  }

  delete(id: string): Promise<unknown> {
    return this.rest.deleteFile(id);
  }
}
