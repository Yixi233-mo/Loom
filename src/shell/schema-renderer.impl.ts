/**
 * UI Schema 四类组件 + 渲染器（React.createElement，无 JSX，便于 Node 直测）。
 * `schema-renderer.tsx` 再导出本模块，供 Tauri/React 工具链使用。
 */

import * as React from "react";
import {
  resolveUiSchema,
  unknownTypeMessage,
  type UiSchema,
} from "./ui-registry.ts";

const e = React.createElement;

export interface FormField {
  name: string;
  label?: string;
  type?: "text" | "number" | "textarea" | "select";
  options?: string[];
}

export function FormView(props: {
  title?: string;
  fields?: FormField[];
  onSubmit?: (values: Record<string, string>) => void;
}) {
  const fields = props.fields ?? [];
  return e(
    "div",
    { className: "loom-ui form", "data-ui-type": "form" },
    props.title ? e("h3", { className: "loom-ui-title" }, props.title) : null,
    e(
      "form",
      {
        onSubmit: (ev: { preventDefault: () => void }) => {
          ev.preventDefault();
          props.onSubmit?.({});
        },
      },
      fields.map((f) =>
        e(
          "label",
          { key: f.name, className: "loom-ui-field" },
          e("span", null, f.label ?? f.name),
          f.type === "textarea"
            ? e("textarea", { name: f.name })
            : f.type === "select"
              ? e(
                  "select",
                  { name: f.name },
                  (f.options ?? []).map((o) => e("option", { key: o, value: o }, o))
                )
              : e("input", {
                  name: f.name,
                  type: f.type === "number" ? "number" : "text",
                })
        )
      ),
      e("button", { type: "submit" }, "提交")
    )
  );
}

export function ListView(props: {
  title?: string;
  items?: unknown[];
  source?: string;
}) {
  const items = props.items ?? [];
  return e(
    "div",
    { className: "loom-ui list", "data-ui-type": "list" },
    props.title ? e("h3", { className: "loom-ui-title" }, props.title) : null,
    props.source
      ? e("p", { className: "loom-ui-source" }, `数据源：${props.source}`)
      : null,
    e(
      "ul",
      { className: "loom-ui-list" },
      items.length === 0
        ? e("li", { className: "loom-ui-empty" }, "暂无数据")
        : items.map((item, i) =>
            e(
              "li",
              { key: i, className: "loom-ui-list-item" },
              typeof item === "string" ? item : JSON.stringify(item)
            )
          )
    )
  );
}

export function ChatView(props: {
  title?: string;
  messages?: Array<{ role: string; content: string }>;
}) {
  const messages = props.messages ?? [];
  return e(
    "div",
    { className: "loom-ui chat", "data-ui-type": "chat" },
    props.title ? e("h3", { className: "loom-ui-title" }, props.title) : null,
    e(
      "div",
      { className: "loom-ui-chat" },
      messages.length === 0
        ? e("p", { className: "loom-ui-empty" }, "开始对话")
        : messages.map((m, i) =>
            e(
              "div",
              { key: i, className: `loom-ui-msg role-${m.role}` },
              e("strong", null, m.role),
              e("span", null, m.content)
            )
          )
    )
  );
}

export function ChartView(props: {
  title?: string;
  series?: Array<{ label: string; value: number }>;
  kind?: "bar" | "line" | "pie";
}) {
  const series = props.series ?? [];
  const max = Math.max(1, ...series.map((s) => s.value));
  return e(
    "div",
    {
      className: "loom-ui chart",
      "data-ui-type": "chart",
      "data-chart-kind": props.kind ?? "bar",
    },
    props.title ? e("h3", { className: "loom-ui-title" }, props.title) : null,
    e(
      "div",
      { className: "loom-ui-chart" },
      series.length === 0
        ? e("p", { className: "loom-ui-empty" }, "暂无数据")
        : series.map((s, i) =>
            e(
              "div",
              { key: i, className: "loom-ui-bar-row" },
              e("span", { className: "loom-ui-bar-label" }, s.label),
              e("div", {
                className: "loom-ui-bar",
                style: { width: `${Math.round((s.value / max) * 100)}%` },
              }),
              e("span", { className: "loom-ui-bar-value" }, String(s.value))
            )
          )
    )
  );
}

export const UI_COMPONENTS = {
  form: FormView,
  list: ListView,
  chat: ChatView,
  chart: ChartView,
} as const;

export function UnknownTypeNotice(props: {
  type: string;
  reason: string;
  message?: string;
}) {
  const msg = props.message ?? unknownTypeMessage(props.type);
  return e(
    "div",
    { className: "loom-ui unknown", "data-ui-type": "unknown", role: "alert" },
    e("p", { className: "loom-ui-unknown-title" }, "无法渲染插件界面"),
    e("p", { className: "loom-ui-unknown-msg" }, msg),
    e("p", { className: "loom-ui-unknown-reason" }, props.reason)
  );
}

export interface SchemaRendererProps {
  schema: UiSchema | null | undefined;
  data?: Record<string, unknown>;
  onFormSubmit?: (values: Record<string, string>) => void;
}

export function SchemaRenderer(props: SchemaRendererProps) {
  const resolved = resolveUiSchema(props.schema);
  if (!resolved.ok) {
    const type =
      props.schema && typeof props.schema.type === "string"
        ? props.schema.type
        : "(空)";
    return e(UnknownTypeNotice, {
      type,
      reason: resolved.reason,
      message: resolved.fallbackLabel,
    });
  }

  const { descriptor, props: schemaProps } = resolved;
  const merged = {
    ...(schemaProps as Record<string, unknown>),
    ...(props.data ?? {}),
  } as Record<string, unknown>;

  if (descriptor.type === "form") {
    return e(FormView, {
      title: merged.title as string | undefined,
      fields: merged.fields as FormField[] | undefined,
      onSubmit: props.onFormSubmit,
    });
  }
  if (descriptor.type === "list") {
    return e(ListView, {
      title: merged.title as string | undefined,
      items: merged.items as unknown[] | undefined,
      source: merged.source as string | undefined,
    });
  }
  if (descriptor.type === "chat") {
    return e(ChatView, {
      title: merged.title as string | undefined,
      messages: merged.messages as
        | Array<{ role: string; content: string }>
        | undefined,
    });
  }
  return e(ChartView, {
    title: merged.title as string | undefined,
    series: merged.series as Array<{ label: string; value: number }> | undefined,
    kind: merged.kind as "bar" | "line" | "pie" | undefined,
  });
}

export default SchemaRenderer;
