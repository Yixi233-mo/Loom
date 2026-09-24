/**
 * LLM 设置面板 — 配置 API（密钥输入）、拉取模型、选择模型、测试对话。
 */

import * as React from "react";

const e = React.createElement;

export interface LlmProviderView {
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

export function LlmSettingsPanel(props: {
  providers: LlmProviderView[];
  draft: { name: string; baseUrl: string; apiKey: string; providerId?: string };
  onDraft?: (d: {
    name: string;
    baseUrl: string;
    apiKey: string;
    providerId?: string;
  }) => void;
  onSave?: () => void;
  onFetchModels?: (providerId: string) => void;
  onSelectModel?: (providerId: string, model: string) => void;
  onDelete?: (providerId: string) => void;
  onTestChat?: (providerId: string) => void;
  busy?: boolean;
  error?: string;
  testResult?: string;
}) {
  const { providers, draft, busy } = props;
  return e(
    "section",
    { className: "app-section", "data-view": "llm-settings" },
    e("h2", null, "自定义 LLM"),
    e(
      "p",
      { className: "hint" },
      "配置 OpenAI 兼容 API（密钥加密存储）；拉取服务商真实模型列表并选择，可用「测试对话」验证。"
    ),

    e(
      "div",
      { className: "llm-form" },
      e("input", {
        "data-field": "llm-name",
        placeholder: "名称（如 DeepSeek）",
        value: draft.name,
        onChange: (ev: { target: { value: string } }) =>
          props.onDraft?.({ ...draft, name: ev.target.value }),
      }),
      e("input", {
        "data-field": "llm-base-url",
        placeholder: "Base URL（https://api.deepseek.com/v1）",
        value: draft.baseUrl,
        onChange: (ev: { target: { value: string } }) =>
          props.onDraft?.({ ...draft, baseUrl: ev.target.value }),
      }),
      e("input", {
        "data-field": "llm-api-key",
        type: "password",
        placeholder: "API Key（加密保存）",
        value: draft.apiKey,
        onChange: (ev: { target: { value: string } }) =>
          props.onDraft?.({ ...draft, apiKey: ev.target.value }),
      }),
      e(
        "button",
        {
          type: "button",
          "data-action": "save-llm",
          disabled: busy,
          onClick: () => props.onSave?.(),
        },
        "保存配置"
      )
    ),

    props.error
      ? e(
          "div",
          {
            className: "loom-dsl-validation",
            role: "alert",
            "data-llm-error": "true",
          },
          e("p", { className: "loom-dsl-validation-title" }, props.error)
        )
      : null,
    props.testResult
      ? e(
          "div",
          {
            className: "mcp-result ok",
            role: "status",
            "data-test-chat": "true",
          },
          e("div", { className: "mcp-msg" }, "测试对话：", props.testResult)
        )
      : null,

    e(
      "ul",
      { className: "llm-list", "data-provider-count": providers.length },
      providers.length === 0
        ? e("p", { className: "empty-hint" }, "尚未配置 LLM 服务商")
        : providers.map((p) =>
            e(
              "li",
              {
                key: p.providerId,
                className: "llm-item",
                "data-provider-id": p.providerId,
              },
              e(
                "div",
                { className: "task-head" },
                e("strong", null, p.name),
                e(
                  "span",
                  { className: "badge" },
                  p.defaultModel ? `模型: ${p.defaultModel}` : "未选模型"
                )
              ),
              e(
                "div",
                { className: "task-meta" },
                `${p.baseUrl} · key=${p.apiKeyMasked || "—"}`
              ),
              e(
                "div",
                { className: "loom-dsl-toolbar" },
                e(
                  "button",
                  {
                    type: "button",
                    "data-action": "fetch-models",
                    disabled: busy,
                    onClick: () => props.onFetchModels?.(p.providerId),
                  },
                  "拉取模型"
                ),
                e(
                  "select",
                  {
                    "data-field": "model-select",
                    value: p.defaultModel || "",
                    onChange: (ev: { target: { value: string } }) =>
                      props.onSelectModel?.(p.providerId, ev.target.value),
                  },
                  e("option", { value: "" }, "选择模型"),
                  ...p.models.map((m) => e("option", { key: m, value: m }, m))
                ),
                e(
                  "button",
                  {
                    type: "button",
                    "data-action": "test-chat",
                    disabled: busy || !p.defaultModel,
                    onClick: () => props.onTestChat?.(p.providerId),
                  },
                  "测试对话"
                ),
                e(
                  "button",
                  {
                    type: "button",
                    "data-action": "delete-llm",
                    onClick: () => props.onDelete?.(p.providerId),
                  },
                  "删除"
                )
              ),
              p.models.length > 0
                ? e(
                    "div",
                    { className: "plugin-tools" },
                    p.models.slice(0, 12).map((m) => e("code", { key: m }, m))
                  )
                : null
            )
          )
    )
  );
}
