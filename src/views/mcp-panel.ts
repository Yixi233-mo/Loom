/**
 * MCP 面板 — 普通人也能操作：填地址 → 点「检测连接」→ 看状态和工具。
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

export function McpPanel(props: {
  url: string;
  onUrl?: (u: string) => void;
  onProbe?: () => void;
  result?: McpProbeResult | null;
  busy?: boolean;
  history?: string[];
}) {
  const r = props.result;
  return e(
    "section",
    { className: "app-section", "data-view": "mcp" },
    e("h2", null, "MCP 外接服务"),
    e(
      "p",
      { className: "hint" },
      "MCP 是「让 Loom 连上外部 AI 工具（如 Claude Code）」的标准接口。填入地址，点检测，就知道能不能用、有哪些工具。"
    ),

    e(
      "div",
      { className: "llm-form" },
      e("input", {
        "data-field": "mcp-url",
        placeholder: "MCP 地址，例如 http://127.0.0.1:3900/mcp",
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
      e("code", null, "http://127.0.0.1:3900/mcp")
    ),

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
            e(
              "strong",
              null,
              r.ok ? "✓ 连接成功" : "✗ 连接失败"
            ),
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
                  r.tools.map((t) => e("code", { key: t }, t))
                )
              )
            : r.ok
              ? e("div", { className: "mcp-msg" }, "暂无工具")
              : null
        )
      : e(
          "p",
          { className: "empty-hint" },
          "尚未检测。填好地址后点「检测连接」。"
        )
  );
}
