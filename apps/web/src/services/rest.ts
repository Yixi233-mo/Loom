/**
 * REST 客户端 — 对接 contracts.API。
 */

import {
  API,
  type FileRef,
  type SessionState,
  type TaskState,
  type AgentState,
} from "../contracts/index.ts";

export type FetchLike = (
  input: string,
  init?: RequestInit
) => Promise<{
  ok: boolean;
  status: number;
  json(): Promise<any>;
  text(): Promise<string>;
}>;

export interface RequestOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

export class RestClient {
  baseUrl: string;
  fetchImpl?: FetchLike;

  constructor(baseUrl: string = "", fetchImpl?: FetchLike) {
    this.baseUrl = baseUrl;
    this.fetchImpl = fetchImpl;
  }

  /** 公开请求（供 LlmApi 等扩展路径使用） */
  requestPublic<T>(path: string, options: RequestOptions = {}): Promise<T> {
    return this.request<T>(path, options);
  }

  private async request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const f: FetchLike =
      this.fetchImpl ?? ((input, init) => (globalThis as any).fetch(input, init) as any);

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers ?? {}),
    };
    const init: RequestInit = {
      method: options.method ?? "GET",
      headers,
    };
    if (options.body !== undefined) {
      init.body = JSON.stringify(options.body);
    }

    // S5：网络/5xx 自动重试一次（幂等 GET；写操作仅网络错误重试）
    const method = (init.method ?? "GET").toUpperCase();
    let lastErr: unknown;
    for (let attempt = 0; attempt < 2; attempt += 1) {
      try {
        const res = await f(this.baseUrl + path, init);
        if (res.ok) {
          return (await res.json()) as T;
        }
        const text = await res.text();
        let message = `HTTP ${res.status}`;
        try {
          const j = JSON.parse(text);
          if (j && (j.message || j.detail)) {
            message = String(j.message ?? j.detail);
            if (j.trace_id) message += ` (trace ${j.trace_id})`;
          }
        } catch {
          if (text) message += ": " + text.slice(0, 200);
        }
        // 4xx 不重试；5xx GET/HEAD 重试一次
        if (res.status >= 500 && attempt === 0 && (method === "GET" || method === "HEAD")) {
          await new Promise((r) => setTimeout(r, 300));
          continue;
        }
        throw new Error(message);
      } catch (err) {
        lastErr = err;
        if (attempt === 0 && (method === "GET" || method === "HEAD")) {
          await new Promise((r) => setTimeout(r, 250));
          continue;
        }
        throw err instanceof Error ? err : new Error(String(err));
      }
    }
    throw lastErr instanceof Error ? lastErr : new Error(String(lastErr));
  }

  listSessions(): Promise<SessionState[]> {
    return this.request(API.SESSIONS);
  }

  getSession(id: string): Promise<SessionState> {
    return this.request(API.SESSION(id));
  }

  createSession(payload: Partial<SessionState>): Promise<SessionState> {
    return this.request(API.SESSIONS, { method: "POST", body: payload });
  }

  appendMessage(
    sessionId: string,
    message: { role: string; content: string }
  ): Promise<unknown> {
    return this.request(API.SESSION_MESSAGES(sessionId), {
      method: "POST",
      body: message,
    });
  }

  listTasks(): Promise<TaskState[]> {
    return this.request(API.TASKS);
  }

  getTask(id: string): Promise<TaskState> {
    return this.request(API.TASK(id));
  }

  triggerTask(payload: {
    workflowName: string;
    device?: string;
    traceId?: string;
  }): Promise<{ taskId: string; status: string }> {
    return this.request(API.TASK_TRIGGER, { method: "POST", body: payload });
  }

  listAgents(): Promise<AgentState[]> {
    return this.request(API.AGENTS);
  }

  getAgent(name: string): Promise<AgentState> {
    return this.request(API.AGENT(name));
  }

  listFiles(): Promise<FileRef[]> {
    return this.request(API.FILES);
  }

  deleteFile(id: string): Promise<unknown> {
    return this.request(API.FILE(id), { method: "DELETE" });
  }
}
