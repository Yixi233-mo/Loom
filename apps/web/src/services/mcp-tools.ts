/**
 * MCP 目录 / Work Buddy 下载推荐 / 工具调用 — 前端服务
 */

import type { RestClient } from "./rest.ts";

export interface McpCatalogItem {
  id: string;
  name: string;
  kind?: string;
  description?: string;
  endpoint?: string;
  default_tool?: string;
  download_url?: string | null;
  download_label?: string | null;
  install_hint?: string;
}

export interface McpCatalogResponse {
  items: McpCatalogItem[];
  downloads: Array<{
    id: string;
    name: string;
    download_url: string;
    download_label: string;
    install_hint: string;
  }>;
}

export interface McpToolsCallResult {
  ok: boolean;
  protocol?: string;
  tool?: string;
  url?: string;
  result?: unknown;
  error?: string;
  fallback?: boolean;
}

export async function fetchMcpCatalog(rest: RestClient): Promise<McpCatalogResponse> {
  return rest.requestPublic("/api/mcp/catalog");
}

export async function callMcpTool(
  rest: RestClient,
  body: {
    url: string;
    tool: string;
    arguments?: Record<string, unknown>;
    protocol?: "mcp" | "rest";
    timeout?: number;
    token?: string;
  }
): Promise<McpToolsCallResult> {
  return rest.requestPublic("/api/mcp/tools-call", {
    method: "POST",
    body: {
      url: body.url,
      tool: body.tool,
      arguments: body.arguments ?? {},
      protocol: body.protocol ?? "mcp",
      timeout: body.timeout ?? 30,
      token: body.token,
    },
  });
}

export function isWorkBuddyItem(item: McpCatalogItem): boolean {
  return item.id === "work_buddy";
}

export function primaryDownloadUrl(catalog: McpCatalogResponse): string | null {
  const d = catalog.downloads.find((x) => x.id === "work_buddy") || catalog.downloads[0];
  return d?.download_url ?? null;
}
