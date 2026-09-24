/**
 * LLM 设置面板 — 配置 API、拉取模型、**选用/切换当前配置**、测试对话。
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
  /** 当前生效的配置（可切换） */
  activeProviderId?: string | null;
  onActiveProvider?: (providerId: string) => void;
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
  const activeId = props.activeProviderId ?? null;

  return e(
    "section",
    { className: "app-section", "data-view": "llm-settings" },
    e("h2", null, "自定义 LLM"),
    e(
      "p",
      { className: "hint" },
      "配置 OpenAI 兼容 API（密钥加密存储）；拉取真实模型列表并**选用某条配置**，对话/测试都走当前选用项。"
    ),

    /* —— 当前配置选择 —— */
    e(
      "div",
      { className: "llm-active-bar glass", "data-view": "llm-active" },
      e("strong", { className: "llm-active-label" }, "当前模型配置"),
      e(
        "select",
        {
          className: "ui-input llm-active-select",
          "data-field": "active-provider-select",
          value: activeId ?? "",
          disabled: providers.length === 0,
          onChange: (ev: { target: { value: string } }) =>
            props.onActiveProvider?.(ev.target.value),
        },
        providers.length === 0
          ? e("option", { value: "" }, "（尚未保存配置）")
          : e("option", { value: "" }, "选择要使用的配置…"),
        ...providers.map((p) =>
          e(
            "option",
            { key: p.providerId, value: p.providerId },
            `${p.name}${p.defaultModel ? " · " + p.defaultModel : " · 未选模型"}`
          )
        )
      ),
      (() => {
        const cur = providers.find((p) => p.providerId === activeId);
        return cur
          ? e(
              "span",
              {
                className: "llm-active-badge",
                "data-active-provider": cur.providerId,
                "data-active-model": cur.defaultModel || "",
              },
              cur.defaultModel ? `使用中：${cur.name} / ${cur.defaultModel}` : `使用中：${cur.name}（未选模型）`
            )
          : e("span", { className: "llm-active-badge is-empty" }, "未选用配置");
      })()
    ),

    e(
      "div",
      { className: "llm-form" },
      e("input", {
        className: "ui-input",
        "data-field": "llm-name",
        placeholder: "名称（如 DeepSeek）",
        value: draft.name,
        onChange: (ev: { target: { value: string } }) =>
          props.onDraft?.({ ...draft, name: ev.target.value }),
      }),
      e("input", {
        className: "ui-input",
        "data-field": "llm-base-url",
        placeholder: "Base URL（https://api.deepseek.com/v1）",
        value: draft.baseUrl,
        onChange: (ev: { target: { value: string } }) =>
          props.onDraft?.({ ...draft, baseUrl: ev.target.value }),
      }),
      e("input", {
        className: "ui-input",
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
          className: "ui-button ui-button--primary",
          "data-action": "save-llm",
          disabled: busy,
          onClick: () => props.onSave?.(),
        },
        busy ? "保存中…" : "保存配置"
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
        : providers.map((p) => {
            const isActive = p.providerId === activeId;
            return e(
              "li",
              {
                key: p.providerId,
                className:
                  "llm-item glass" + (isActive ? " is-active" : ""),
                "data-provider-id": p.providerId,
                "data-active": isActive ? "true" : "false",
              },
              e(
                "div",
                { className: "task-head" },
                e("strong", null, p.name),
                e(
                  "span",
                  { className: "badge" + (isActive ? " ok" : "") },
                  isActive
                    ? "当前使用"
                    : p.defaultModel
                      ? `模型: ${p.defaultModel}`
                      : "未选模型"
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
                    className:
                      "ui-button " +
                      (isActive ? "ui-button--primary" : "ui-button--ghost"),
                    "data-action": "use-provider",
                    "data-provider-id": p.providerId,
                    disabled: isActive,
                    onClick: () => props.onActiveProvider?.(p.providerId),
                  },
                  isActive ? "使用中" : "选用此配置"
                ),
                e(
                  "button",
                  {
                    type: "button",
                    className: "ui-button ui-button--ghost",
                    "data-action": "fetch-models",
                    disabled: busy,
                    onClick: () => props.onFetchModels?.(p.providerId),
                  },
                  "拉取模型"
                ),
                e(
                  "select",
                  {
                    className: "ui-input llm-model-select",
                    "data-field": "model-select",
                    "data-provider-id": p.providerId,
                    value: p.defaultModel || "",
                    disabled: p.models.length === 0,
                    onChange: (ev: { target: { value: string } }) =>
                      props.onSelectModel?.(p.providerId, ev.target.value),
                  },
                  e(
                    "option",
                    { value: "" },
                    p.models.length ? "选择模型" : "先拉取模型"
                  ),
                  ...p.models.map((m) => e("option", { key: m, value: m }, m))
                ),
                e(
                  "button",
                  {
                    type: "button",
                    className: "ui-button ui-button--primary",
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
                    className: "ui-button ui-button--danger",
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
                    p.models.slice(0, 12).map((m) =>
                      e(
                        "code",
                        {
                          key: m,
                          style: {
                            cursor: "pointer",
                            outline:
                              p.defaultModel === m ? "2px solid var(--accent)" : undefined,
                          },
                          "data-model": m,
                          onClick: () =>
                            props.onSelectModel?.(p.providerId, m),
                        },
                        m
                      )
                    )
                  )
                : null
            );
          })
    )
  );
}
