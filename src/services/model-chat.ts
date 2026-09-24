/**
 * 模型对话服务 — 调用自定义 LLM（OpenAI 兼容 chat）。
 * 对「返回网页而不是 JSON」「模型不可用/无权限」给出可读错误。
 */

import type { SessionMessage } from "../contracts/index.ts";

export interface ChatModelRef {
  providerId: string;
  baseUrl: string;
  apiKey: string;
  model: string;
}

export type ChatFetch = (
  input: string,
  init?: {
    method?: string;
    body?: any;
    headers?: Record<string, string>;
  }
) => Promise<{
  ok: boolean;
  status: number;
  headers?: { get(name: string): string | null };
  json(): Promise<any>;
  text(): Promise<string>;
}>;

/** 规范化 OpenAI 兼容 base：补 /v1、去尾斜杠 */
export function normalizeChatBaseUrl(baseUrl: string): string {
  let u = (baseUrl || "").trim().replace(/\/+$/, "");
  if (!u) return "";
  if (!/\/v\d+$/i.test(u)) {
    u = u + "/v1";
  }
  return u;
}

export function toChatMessages(
  history: SessionMessage[],
  system?: string
): Array<{ role: string; content: string }> {
  const msgs: Array<{ role: string; content: string }> = [];
  if (system) msgs.push({ role: "system", content: system });
  for (const m of history) {
    if (m.role === "user" || m.role === "assistant") {
      msgs.push({ role: m.role, content: m.content });
    }
  }
  return msgs;
}

function looksLikeHtml(text: string): boolean {
  const t = (text || "").trimStart().toLowerCase();
  return t.startsWith("<!doctype") || t.startsWith("<html") || t.startsWith("<head");
}

function providerErrorMessage(text: string, status: number): string {
  try {
    const data = JSON.parse(text);
    const raw =
      data?.error?.message || data?.message || data?.error || "";
    const msg = String(raw);
    if (/not supported/i.test(msg)) {
      return `模型对话失败：所选模型当前不支持对话（${msg}）。请在下拉里换一个可对话的模型，例如 auto`;
    }
    if (/no access|invalid token|无效的令牌/i.test(msg)) {
      return `模型对话失败：${msg}。请核对 API Key 是否正确、是否有效`;
    }
    if (msg) return `模型对话失败 HTTP ${status}：${msg}`;
  } catch {
    /* fallthrough */
  }
  return `模型对话失败 HTTP ${status}：${(text || "").slice(0, 160)}`;
}

export class ModelChatClient {
  fetchImpl?: ChatFetch;

  constructor(fetchImpl?: ChatFetch) {
    this.fetchImpl = fetchImpl;
  }

  async complete(
    ref: ChatModelRef,
    history: SessionMessage[],
    system?: string
  ): Promise<string> {
    const f: ChatFetch =
      this.fetchImpl ??
      ((input, init) => (globalThis as any).fetch(input, init) as any);

    const base = normalizeChatBaseUrl(ref.baseUrl);
    if (!base) {
      throw new Error(
        "请先在「自定义 LLM」里填写 API 地址（例如 https://api.deepseek.com/v1）"
      );
    }
    if (!ref.model) {
      throw new Error("请先在「自定义 LLM」里选择对话模型");
    }
    const url = base + "/chat/completions";
    const res = await f(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(ref.apiKey ? { Authorization: `Bearer ${ref.apiKey}` } : {}),
      },
      body: JSON.stringify({
        model: ref.model,
        messages: toChatMessages(history, system),
      }),
    });

    const text =
      typeof (res as any).text === "function"
        ? await res.text()
        : JSON.stringify(await (res as any).json());

    if (looksLikeHtml(text)) {
      throw new Error(
        `模型对话失败：服务器返回了网页而不是 JSON。请检查 API 地址（应类似 https://…/v1，当前 ${base}）`
      );
    }

    if (!res.ok) {
      throw new Error(providerErrorMessage(text, res.status));
    }

    let data: any;
    try {
      data = JSON.parse(text);
    } catch {
      throw new Error(
        "模型对话失败：响应不是 JSON，请检查 API 地址与网络代理设置"
      );
    }

    const content = data?.choices?.[0]?.message?.content;
    if (typeof content !== "string") {
      throw new Error("模型响应格式不正确（缺少 choices[0].message.content）");
    }
    return content;
  }
}
