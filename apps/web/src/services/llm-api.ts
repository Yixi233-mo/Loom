/**
 * LLM 配置 REST 联调 — 对接 /api/llm/*；可按 URL+Key 直接拉取模型。
 */

import type { RestClient } from "./rest.ts";

export interface LlmProviderDto {
  providerId: string;
  name: string;
  baseUrl: string;
  apiKeyMasked?: string;
  hasApiKey?: boolean;
  defaultModel?: string;
  enabled?: boolean;
  models: string[];
  apiKeyPlain?: string;
}

export class LlmApi {
  rest: RestClient;

  constructor(rest: RestClient) {
    this.rest = rest;
  }

  list(): Promise<LlmProviderDto[]> {
    return this.rest.requestPublic("/api/llm/providers");
  }

  save(body: {
    name: string;
    baseUrl: string;
    apiKey?: string;
    defaultModel?: string;
    providerId?: string;
    enabled?: boolean;
  }): Promise<LlmProviderDto> {
    return this.rest.requestPublic("/api/llm/providers", {
      method: "POST",
      body,
    });
  }

  remove(providerId: string): Promise<{ ok: boolean }> {
    return this.rest.requestPublic(`/api/llm/providers/${providerId}`, {
      method: "DELETE",
    });
  }

  fetchModels(
    providerId: string
  ): Promise<{ providerId: string; models: string[] }> {
    return this.rest.requestPublic(
      `/api/llm/providers/${providerId}/fetch-models`,
      { method: "POST" }
    );
  }

  select(providerId: string, model: string): Promise<LlmProviderDto> {
    return this.rest.requestPublic(`/api/llm/providers/${providerId}/select`, {
      method: "POST",
      body: { model },
    });
  }
}

/** 只返回合法、可读的模型列表端点（不拼 /v1/v1beta 之类） */
export function modelsEndpoints(baseUrl: string): string[] {
  const base = (baseUrl || "").trim().replace(/\/+$/, "");
  if (!base) return [];
  // 去掉末尾 /v1、/v1beta 等版本段，得到网关根
  const root = base.replace(/\/v\d+[a-z]*$/i, "");
  const out: string[] = [];
  const push = (u: string) => {
    if (u && !out.includes(u)) out.push(u);
  };
  // 优先标准与该平台支持的路径
  push(root + "/v1/models");
  push(root + "/v1beta/models");
  // 兼容 base 已带 /v1 的写法
  push(base + "/models");
  // 最后才试无版本 /models（部分网关会回 HTML）
  push(root + "/models");
  return out;
}

function parseModelNames(data: any): string[] {
  const items = data?.data || data?.models || data?.items || [];
  const names: string[] = [];
  for (const it of items) {
    if (typeof it === "string") names.push(it);
    else if (it && (it.id || it.name)) names.push(String(it.id || it.name));
  }
  return names;
}

function isHtml(text: string): boolean {
  const t = (text || "").trimStart().toLowerCase();
  return t.startsWith("<!doctype") || t.startsWith("<html") || t.startsWith("<head");
}

/** 按 Base URL + API Key 拉取服务商支持的模型 */
export async function fetchProviderModels(
  baseUrl: string,
  apiKey: string,
  fetchImpl?: typeof fetch
): Promise<string[]> {
  const f = fetchImpl ?? ((globalThis as any).fetch as typeof fetch);
  const urls = modelsEndpoints(baseUrl);
  if (!urls.length) throw new Error("请先填写 API 地址");

  const attempts: string[] = [];
  let firstRealError = "";

  for (const url of urls) {
    try {
      const res = await f(url, {
        method: "GET",
        headers: {
          Accept: "application/json",
          ...(apiKey ? { Authorization: "Bearer " + apiKey } : {}),
        },
      });
      const text = await res.text();
      if (isHtml(text)) {
        attempts.push(url + " → 返回网页");
        if (!firstRealError) {
          firstRealError =
            "服务器返回了网页而不是 JSON，请检查 API 地址（应类似 https://…/v1）";
        }
        continue;
      }
      if (!res.ok) {
        let detail = text.slice(0, 160);
        try {
          const j = JSON.parse(text);
          detail = j?.error?.message || j?.message || detail;
        } catch {
          /* keep raw */
        }
        attempts.push(url + " → HTTP " + res.status);
        if (!firstRealError) {
          firstRealError = "HTTP " + res.status + "：" + detail;
          if (res.status === 401 || /invalid token|无效的令牌/i.test(detail)) {
            firstRealError +=
              "。请重新保存 API Key（保存后在列表里点「拉取模型」）";
          }
        }
        continue;
      }
      let data: any;
      try {
        data = JSON.parse(text);
      } catch {
        attempts.push(url + " → 响应不是 JSON");
        if (!firstRealError) firstRealError = "响应不是 JSON";
        continue;
      }
      const names = parseModelNames(data);
      if (!names.length) {
        attempts.push(url + " → 空模型列表");
        if (!firstRealError) firstRealError = "服务商未返回任何模型 id";
        continue;
      }
      return names;
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      attempts.push(url + " → " + msg);
      if (!firstRealError) firstRealError = msg;
    }
  }

  throw new Error(
    (firstRealError || "拉取模型失败") +
      "（已尝试：" +
      attempts.join("；") +
      "）"
  );
}

/** MCP 探测（对接 /api/mcp/probe） */
export async function probeMcp(
  rest: RestClient,
  url: string,
  timeout = 8,
  token?: string
): Promise<McpProbeResult> {
  return rest.requestPublic("/api/mcp/probe", {
    method: "POST",
    body: { url, timeout, token },
  });
}

export interface McpProbeResult {
  ok: boolean;
  url: string;
  message: string;
  tools: string[];
  serverInfo?: { name?: string } | null;
}
