/**
 * MCP 面板 — 检测连接 · 工具调用 · 内置目录 / Work Buddy 下载推荐
 */

import * as React from "react";

const e = React.createElement;

export interface McpProbeResult {
  ok: boolean;
  url: string;
  message: string;
  tools: string[];
  serverInfo?: { name?: string } | null;
}

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

export function McpPanel(props: {
  url: string;
  onUrl?: (u: string) => void;
  onProbe?: () => void;
  result?: McpProbeResult | null;
  busy?: boolean;
  history?: string[];
  catalog?: McpCatalogItem[];
  toolCallResult?: string | null;
  toolCallBusy?: boolean;
  onToolsCall?: (tool: string) => void;
  onUseEndpoint?: (url: string) => void;
}) {
  const r = props.result;
  const catalog = props.catalog ?? [];
  const downloads = catalog.filter((c) => !!c.download_url);

  return e(
    "section",
    { className: "app-section", "data-view": "mcp" },
    e("h2", null, "MCP 外接服务"),
    e(
      "p",
      { className: "hint" },
      "MCP 是「让 Loom 连上外部 AI 工具（Claude Code、Work Buddy 等）」的标准接口。填地址 → 检测连接 → 看工具；可一键试调用。"
    ),

    e(
      "div",
      { className: "llm-form" },
      e("input", {
        "data-field": "mcp-url",
        placeholder: "MCP 地址，例如 http://127.0.0.1:54916/mcp",
        value: props.url,
        onChange: (ev: { target: { value: string } }) =>
          props.onUrl?.(ev.target.value),
      }),
      e(
        "button",
        {
          type: "button",
          "data-action": "mcp-probe",
          disabled: !!props.busy,
          onClick: () => props.onProbe?.(),
        },
        props.busy ? "检测中…" : "检测连接"
      ),
      e(
        "button",
        {
          type: "button",
          "data-action": "mcp-tools-call",
          disabled: !!props.toolCallBusy || !r?.ok,
          onClick: () => props.onToolsCall?.(r?.tools?.[0] ?? "code_task"),
        },
        props.toolCallBusy ? "调用中…" : "试调用工具"
      )
    ),

    e(
      "div",
      {
        className: "mcp-demo-hint",
        "data-action": "mcp-demo-hint",
      },
      "没有外部服务？先运行演示服务：",
      e("code", null, "python scripts/mock_mcp_server.py"),
      " 然后地址填 ",
      e("code", null, "http://127.0.0.1:54916/mcp")
    ),

    downloads.length > 0
      ? e(
          "div",
          { className: "mcp-catalog", "data-view": "mcp-downloads" },
          e("h3", null, "推荐下载"),
          downloads.map((c) =>
            e(
              "div",
              {
                key: c.id,
                className: "mcp-catalog-card",
                "data-catalog-id": c.id,
              },
              e("strong", null, c.name),
              e("p", { className: "hint" }, c.install_hint || c.description || ""),
              e(
                "a",
                {
                  className: "ui-button ui-button--primary",
                  href: c.download_url || "#",
                  target: "_blank",
                  rel: "noreferrer",
                  "data-action": "download-work-buddy",
                  "data-download-url": c.download_url || "",
                },
                (c.id === "work_buddy" ? (c.download_label || "下载 Work Buddy") : (c.download_label || "下载"))
              ),
              c.endpoint
                ? e(
                    "button",
                    {
                      type: "button",
                      className: "ui-button ui-button--ghost",
                      "data-action": "use-buddy-endpoint",
                      onClick: () => props.onUseEndpoint?.(c.endpoint!),
                    },
                    "填入地址"
                  )
                : null
            )
          )
        )
      : null,

    catalog.length > 0
      ? e(
          "div",
          { className: "mcp-catalog", "data-view": "mcp-catalog" },
          e("h3", null, "内置 / 可接服务"),
          catalog.map((c) =>
            e(
              "div",
              {
                key: c.id,
                className: "mcp-catalog-card",
                "data-catalog-id": c.id,
                "data-catalog-kind": c.kind || "",
              },
              e("strong", null, c.name),
              e("p", { className: "hint" }, c.description || ""),
              e("div", { className: "mcp-msg" }, "默认工具：", e("code", null, c.default_tool || "-")),
              c.endpoint
                ? e(
                    "button",
                    {
                      type: "button",
                      className: "ui-button ui-button--ghost",
                      "data-action": "use-endpoint",
                      onClick: () => props.onUseEndpoint?.(c.endpoint!),
                    },
                    "使用该地址"
                  )
                : null
            )
          )
        )
      : null,

    r
      ? e(
          "div",
          {
            className: `mcp-result ${r.ok ? "ok" : "fail"}`,
            "data-mcp-ok": r.ok ? "true" : "false",
            role: "status",
          },
          e(
            "div",
            { className: "mcp-status" },
            e("strong", null, r.ok ? "✓ 连接成功" : "✗ 连接失败"),
            e("span", { className: "mcp-url" }, r.url)
          ),
          e("div", { className: "mcp-msg" }, r.message),
          r.serverInfo?.name
            ? e("div", { className: "mcp-msg" }, "服务名：", r.serverInfo.name)
            : null,
          r.tools.length > 0
            ? e(
                "div",
                { className: "mcp-tools" },
                e("div", { className: "mcp-msg" }, `可用工具（${r.tools.length} 个）：`),
                e(
                  "div",
                  { className: "plugin-tools" },
                  r.tools.map((t) =>
                    e(
                      "code",
                      {
                        key: t,
                        "data-tool": t,
                        onClick: () => props.onToolsCall?.(t),
                        style: { cursor: "pointer" },
                      },
                      t
                    )
                  )
                )
              )
            : r.ok
              ? e("div", { className: "mcp-msg" }, "暂无工具")
              : null,
          props.toolCallResult
            ? e(
                "div",
                {
                  className: "mcp-msg",
                  "data-view": "mcp-tools-call-result",
                  "data-tools-call": "result",
                },
                "调用结果：",
                props.toolCallResult
              )
            : null
        )
      : e(
          "p",
          { className: "empty-hint" },
          "尚未检测。填好地址后点「检测连接」。"
        ),

    e(
      "p",
      { className: "hint", "data-action": "mcp-docs-link" },
      "链路说明：对话 → 意图识别 → 选端 → 工具调用 / 连 Claude Code · Work Buddy。详见 ",
      e("code", null, "目录/MCP_工具调用说明.md")
    )
  );
}
