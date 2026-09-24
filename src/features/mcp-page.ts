/**
 * FE.3+ MCP 独立页 — 三步：填地址 → 检测连接 → 试调用工具
 * 附内置目录 / Work Buddy 下载推荐。
 */

import * as React from "react";
import {
  McpPanel,
  type McpCatalogItem,
  type McpProbeResult,
} from "../views/mcp-panel.ts";
import { PageShell, ErrorState, LoadingState, phaseOf } from "./page-states.ts";
import { UI } from "../components/index.ts";

const e = React.createElement;

const STEPS = [
  { n: "1", title: "启动服务", desc: "python scripts/mock_mcp_server.py（或真实 Claude Code / Work Buddy）" },
  { n: "2", title: "检测连接", desc: "填协议地址 http://127.0.0.1:3900/mcp，点「检测连接」看工具列表" },
  { n: "3", title: "试调用工具", desc: "点「试调用工具」或点某个工具名，验证 tools/call 真的通" },
];

export function McpWorkspace(props: {
  url: string;
  onUrl?: (u: string) => void;
  onProbe?: () => void;
  result?: McpProbeResult | null;
  busy?: boolean;
  catalog?: McpCatalogItem[];
  toolCallResult?: string | null;
  toolCallBusy?: boolean;
  onToolsCall?: (tool: string) => void;
  onUseEndpoint?: (url: string) => void;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}) {
  const phase = phaseOf({
    loading: props.loading,
    error: props.error,
    empty: false,
  });

  return e(
    PageShell,
    {
      route: "mcp",
      title: "MCP 外接服务",
      subtitle: "让 Loom 调用 Claude Code / Work Buddy 等外部 AI 工具（JSON-RPC）",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "open-mcp-docs",
          onClick: () => {
            /* 文档路径提示 */
          },
        },
        "链路说明"
      ),
    },
    e(
      "div",
      {
        className: "mcp-workspace",
        "data-page": "mcp",
        "data-phase": phase,
        "data-view": "mcp-workspace",
      },
      phase === "loading"
        ? e(LoadingState, { label: "载入 MCP…", rows: 2 })
        : phase === "error"
          ? e(ErrorState, {
              title: "MCP 模块加载失败",
              message: props.error ?? "未知错误",
              onRetry: props.onRetry,
            })
          : e(
              React.Fragment,
              null,
              e(
                "ol",
                { className: "mcp-steps", "data-view": "mcp-steps" },
                STEPS.map((s) =>
                  e(
                    "li",
                    { key: s.n, className: "mcp-step", "data-step": s.n },
                    e("span", { className: "mcp-step-n" }, s.n),
                    e(
                      "div",
                      null,
                      e("strong", null, s.title),
                      e("p", { className: "hint" }, s.desc)
                    )
                  )
                )
              ),
              e("div", { className: "mcp-flow-hint", "data-view": "mcp-flow" },
                "链路：对话 → 意图识别 → 选端 → 工具调用 / 连 Claude Code · Work Buddy"
              ),
              e(McpPanel, {
                url: props.url,
                onUrl: props.onUrl,
                onProbe: props.onProbe,
                result: props.result,
                busy: props.busy,
                catalog: props.catalog,
                toolCallResult: props.toolCallResult,
                toolCallBusy: props.toolCallBusy,
                onToolsCall: props.onToolsCall,
                onUseEndpoint: props.onUseEndpoint,
              })
            )
    )
  );
}
