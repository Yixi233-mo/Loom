/**
 * FE.3 页面状态原语 — 加载 / 空 / 错误 / 骨架
 * React.createElement，无 JSX，便于 Node 直测。
 */

import * as React from "react";

const e = React.createElement;

export type AsyncPhase = "idle" | "loading" | "ready" | "empty" | "error";

export function phaseOf(opts: {
  loading?: boolean;
  error?: string | null;
  empty?: boolean;
}): AsyncPhase {
  if (opts.loading) return "loading";
  if (opts.error) return "error";
  if (opts.empty) return "empty";
  return "ready";
}

export function LoadingState(props: { label?: string; rows?: number }) {
  const rows = props.rows ?? 3;
  return e(
    "div",
    {
      className: "fe-state fe-state--loading",
      "data-state": "loading",
      role: "status",
      "aria-busy": "true",
    },
    e("p", { className: "fe-state-label" }, props.label ?? "加载中…"),
    e(
      "div",
      { className: "fe-skeleton-list" },
      Array.from({ length: rows }, (_, i) =>
        e("div", {
          key: i,
          className: "fe-skeleton",
          "data-skeleton": String(i),
        })
      )
    )
  );
}

export function EmptyState(props: {
  title: string;
  hint?: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return e(
    "div",
    {
      className: "fe-state fe-state--empty",
      "data-state": "empty",
      role: "status",
    },
    e("p", { className: "fe-state-title" }, props.title),
    props.hint ? e("p", { className: "fe-state-hint" }, props.hint) : null,
    props.actionLabel
      ? e(
          "button",
          {
            type: "button",
            className: "ui-button ui-button--primary",
            "data-action": "empty-action",
            onClick: () => { if (props.onAction) props.onAction(); },
          },
          props.actionLabel
        )
      : null
  );
}

export function ErrorState(props: {
  title?: string;
  message: string;
  onRetry?: () => void;
  retryLabel?: string;
}) {
  return e(
    "div",
    {
      className: "fe-state fe-state--error",
      "data-state": "error",
      role: "alert",
    },
    e("p", { className: "fe-state-title" }, props.title ?? "出错了"),
    e("p", { className: "fe-state-hint", "data-error-message": "true" }, props.message),
    props.onRetry
      ? e(
          "button",
          {
            type: "button",
            className: "ui-button ui-button--ghost",
            "data-action": "retry",
            onClick: () => { if (props.onRetry) props.onRetry(); },
          },
          props.retryLabel ?? "重试"
        )
      : null
  );
}

export function PageShell(props: {
  route: string;
  title: string;
  subtitle?: string;
  actions?: unknown;
  children?: unknown;
}) {
  return e(
    "section",
    {
      className: "fe-page glass",
      "data-page": props.route,
    },
    e(
      "header",
      { className: "fe-page-header" },
      e(
        "div",
        null,
        e("h2", { className: "fe-page-title" }, props.title),
        props.subtitle
          ? e("p", { className: "fe-page-subtitle" }, props.subtitle)
          : null
      ),
      props.actions
        ? e("div", { className: "fe-page-actions" }, props.actions as any)
        : null
    ),
    e("div", { className: "fe-page-body" }, props.children as any)
  );
}
