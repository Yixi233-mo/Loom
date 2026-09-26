/**
 * 设置 · 跨端 — LLM + MCP + 设备（U2 合并入口）
 */

import * as React from "react";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageShell,
  phaseOf,
} from "./page-states.ts";
import { UI } from "../components/index.ts";
import { DiagnosticsPanel } from "./diagnostics.ts";
import { LlmSettingsPanel, type LlmProviderView } from "../views/llm-settings-panel.ts";
import { McpPanel, type McpProbeResult } from "../views/mcp-panel.ts";

const e = React.createElement;

export type SettingsTab = "llm" | "mcp" | "devices";

export function SettingsPage(props: {
  tab: SettingsTab;
  onTab?: (t: SettingsTab) => void;
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  /* LLM — 原样透传现有面板 */
  activeProviderId?: string | null;
  onActiveProvider?: (id: string) => void;
  llmError?: string;
  llmTestResult?: string;
  providers?: LlmProviderView[];
  llmDraft?: {
    name: string;
    baseUrl: string;
    apiKey: string;
    providerId?: string;
  };
  onLlmDraft?: (d: {
    name: string;
    baseUrl: string;
    apiKey: string;
    providerId?: string;
  }) => void;
  onSaveLlm?: () => void;
  onFetchModels?: (providerId: string) => void;
  onSelectModel?: (providerId: string, model: string) => void;
  onDeleteProvider?: (providerId: string) => void;
  onTestChat?: (providerId: string) => void;
  /* MCP */
  mcpCatalog?: import("../views/mcp-panel.ts").McpCatalogItem[];
  mcpToolResult?: string | null;
  mcpToolBusy?: boolean;
  onMcpToolsCall?: (tool: string) => void;
  onMcpUseEndpoint?: (url: string) => void;
  mcpUrl?: string;
  onMcpUrl?: (u: string) => void;
  onMcpProbe?: () => void;
  mcpResult?: McpProbeResult | null;
  mcpBusy?: boolean;
  /** U2：跨端设备面板节点（App 注入） */
  devicesNode?: unknown;
}) {
  const tab = props.tab;
  const phase = phaseOf({
    loading: props.loading,
    error: props.error,
    empty: false,
  });
  const emptyProviders = !props.loading && (props.providers?.length ?? 0) === 0;

  return e(
    PageShell,
    {
      route: "settings",
      title: "设置 · 跨端",
      subtitle: "模型 · MCP · 设备，一处管完",
      actions: e(
        "div",
        { className: "settings-tabs", role: "tablist" },
        e(
          "button",
          {
            type: "button",
            role: "tab",
            "aria-selected": tab === "llm" ? "true" : "false",
            className:
              UI.button + " " + (tab === "llm" ? UI.buttonPrimary : "ui-button--ghost"),
            "data-tab": "llm",
            onClick: () => props.onTab?.("llm"),
          },
          "自定义 LLM"
        ),
        e(
          "button",
          {
            type: "button",
            role: "tab",
            "aria-selected": tab === "mcp" ? "true" : "false",
            className:
              UI.button + " " + (tab === "mcp" ? UI.buttonPrimary : "ui-button--ghost"),
            "data-tab": "mcp",
            onClick: () => props.onTab?.("mcp"),
          },
          "MCP 服务"
        ),
        e(
          "button",
          {
            type: "button",
            role: "tab",
            "aria-selected": tab === "devices" ? "true" : "false",
            className:
              UI.button +
              " " +
              (tab === "devices" ? UI.buttonPrimary : "ui-button--ghost"),
            "data-tab": "devices",
            onClick: () => props.onTab?.("devices"),
          },
          "跨端设备"
        )
      ),
    },
    e(
      "div",
      {
        className: "settings-page",
        "data-phase": phase,
        "data-tab": tab,
      },
      e(DiagnosticsPanel, { route: "settings" }),
      phase === "loading"
        ? e(LoadingState, { label: "载入设置…", rows: 2 })
        : phase === "error"
          ? e(ErrorState, {
              title: "设置加载失败",
              message: props.error ?? "未知错误",
              onRetry: props.onRetry,
            })
          : tab === "llm"
            ? e(
                "div",
                { "data-view": "settings-llm" },
                emptyProviders
                  ? e(EmptyState, {
                      title: "尚未配置模型",
                      hint: "填写 OpenAI 兼容 API（如 DeepSeek）并保存，即可拉取模型列表。",
                    })
                  : null,
                e(LlmSettingsPanel, {
                  activeProviderId: props.activeProviderId,
                  onActiveProvider: props.onActiveProvider,
                  error: props.llmError,
                  testResult: props.llmTestResult,
                  providers: props.providers ?? [],
                  draft: props.llmDraft ?? { name: "", baseUrl: "", apiKey: "" },
                  onDraft: props.onLlmDraft,
                  onSave: props.onSaveLlm,
                  onFetchModels: props.onFetchModels,
                  onSelectModel: props.onSelectModel,
                  onDelete: props.onDeleteProvider,
                  onTestChat: props.onTestChat,
                })
              )
            : tab === "devices"
            ? e(
                "div",
                { "data-view": "settings-devices" },
                (props.devicesNode as never) ??
                  e("p", { className: "hint" }, "设备面板加载中…")
              )
            : e(
                "div",
                { "data-view": "settings-mcp" },
                e(McpPanel, {
                  url: props.mcpUrl ?? "",
                  onUrl: props.onMcpUrl,
                  onProbe: props.onMcpProbe,
                  result: props.mcpResult,
                  busy: props.mcpBusy,
                  catalog: props.mcpCatalog,
                  toolCallResult: props.mcpToolResult,
                  toolCallBusy: props.mcpToolBusy,
                  onToolsCall: props.onMcpToolsCall,
                  onUseEndpoint: props.onMcpUseEndpoint,
                })
              )
    )
  );
}
