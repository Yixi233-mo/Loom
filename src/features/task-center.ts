/**
 * FE.6 — ResultCard memo + 任务列表虚拟窗口
 */

import * as React from "react";
import type { TaskState, TaskStatus } from "../contracts/index.ts";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageShell,
  phaseOf,
} from "./page-states.ts";
import { UI } from "../components/index.ts";
import { memo, VirtualList } from "../perf/index.ts";

const e = React.createElement;

const FILTERS: Array<{ id: TaskStatus | "all"; label: string }> = [
  { id: "all", label: "全部" },
  { id: "pending", label: "待处理" },
  { id: "running", label: "执行中" },
  { id: "done", label: "已完成" },
  { id: "failed", label: "失败" },
];

function ResultCardImpl(props: { task: TaskState }) {
  const t = props.task;
  const r = t.result;
  return e(
    "article",
    {
      className: "result-card",
      "data-task-id": t.taskId,
      "data-status": t.status,
      "data-view": "result-card",
    },
    e(
      "header",
      { className: "result-head" },
      e("strong", null, t.workflowName),
      e("span", { className: "result-status" }, t.status)
    ),
    e(
      "p",
      { className: "result-trace" },
      `trace=${t.traceId} · device=${t.device}${t.assignedTo ? ` · ${t.assignedTo}` : ""}`
    ),
    r?.summary ? e("p", { className: "result-summary" }, r.summary) : null,
    r
      ? e(
          "dl",
          { className: "result-metrics" },
          e("dt", null, "tokens_used"),
          e("dd", { "data-metric": "tokens_used" }, String(r.tokensUsed ?? 0)),
          e("dt", null, "latency_ms"),
          e("dd", { "data-metric": "latency_ms" }, String(r.latencyMs ?? 0)),
          e("dt", null, "degradation_level"),
          e(
            "dd",
            { "data-metric": "degradation_level" },
            String(r.degradationLevel ?? 0)
          )
        )
      : null,
    t.error
      ? e("p", { className: "result-error", "data-error": "true" }, t.error)
      : null
  );
}

export const ResultCard = memo(ResultCardImpl);

export function TaskCenter(props: {
  tasks: TaskState[];
  filter?: TaskStatus | "all";
  loading?: boolean;
  error?: string | null;
  /** 虚拟列表视口高（默认 360） */
  listHeight?: number;
  itemHeight?: number;
  onFilter?: (f: TaskStatus | "all") => void;
  onRetry?: () => void;
  onRefresh?: () => void;
}) {
  const filter = props.filter ?? "all";
  const phase = phaseOf({
    loading: props.loading,
    error: props.error,
    empty:
      !props.loading &&
      !props.error &&
      (filter === "all"
        ? props.tasks.length === 0
        : props.tasks.filter((t) => t.status === filter).length === 0),
  });
  const visible =
    filter === "all" ? props.tasks : props.tasks.filter((t) => t.status === filter);
  const listHeight = props.listHeight ?? 360;
  const itemHeight = props.itemHeight ?? 120;
  const useVirtual = visible.length > 20;

  return e(
    PageShell,
    {
      route: "tasks",
      title: "任务中心",
      subtitle: "跨端编排 · 结果含 tokens / latency / 降级档位",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonPrimary,
          "data-action": "tasks-refresh",
          disabled: !!props.loading,
          onClick: () => props.onRefresh?.(),
        },
        props.loading ? "刷新中…" : "刷新"
      ),
    },
    e(
      "div",
      {
        className: "task-center",
        "data-phase": phase,
        "data-filter": filter,
        "data-virtual": useVirtual ? "true" : "false",
      },
      e(
        "div",
        { className: "task-filters", role: "tablist" },
        FILTERS.map((f) =>
          e(
            "button",
            {
              key: f.id,
              type: "button",
              role: "tab",
              "aria-selected": filter === f.id ? "true" : "false",
              className:
                UI.button +
                " " +
                (filter === f.id ? UI.buttonPrimary : "ui-button--ghost"),
              "data-filter": f.id,
              onClick: () => props.onFilter?.(f.id),
            },
            f.label
          )
        )
      ),
      phase === "loading"
        ? e(LoadingState, { label: "正在同步任务…", rows: 4 })
        : phase === "error"
          ? e(ErrorState, {
              title: "任务列表加载失败",
              message: props.error ?? "未知错误",
              onRetry: props.onRetry,
            })
          : phase === "empty"
            ? e(EmptyState, {
                title: filter === "all" ? "暂无任务" : `没有「${filter}」任务`,
                hint: "触发 Workflow 后会出现在这里。",
                actionLabel: "查看全部",
                onAction: () => props.onFilter?.("all"),
              })
            : useVirtual
              ? e(VirtualList as any, {
                  items: visible,
                  itemHeight,
                  height: listHeight,
                  className: "task-list",
                  "data-view": "task-list",
                  keyOf: (t: TaskState) => t.taskId,
                  renderItem: (t: TaskState) => e(ResultCard, { task: t }),
                })
              : e(
                  "div",
                  { className: "task-list", "data-view": "task-list" },
                  visible.map((t) => e(ResultCard, { key: t.taskId, task: t }))
                )
    )
  );
}
