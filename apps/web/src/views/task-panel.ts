/**
 * 任务面板 — 任务状态列表 + 结果卡片。
 */

import * as React from "react";
import type { TaskResult, TaskState, TaskStatus } from "../contracts/index.ts";

const e = React.createElement;

export function ResultCard(props: { result: TaskResult; traceId?: string; taskName?: string }) {
  const { result, traceId, taskName } = props;
  return e(
    "div",
    { className: "result-card", "data-view": "result-card" },
    e("h4", { className: "result-title" }, "结果卡片"),
    e("div", { className: "result-summary" }, result.summary || "（无摘要）"),
    e(
      "dl",
      { className: "result-metrics" },
      e("dt", null, "tokens_used"),
      e("dd", { "data-metric": "tokens_used" }, String(result.tokensUsed ?? "—")),
      e("dt", null, "latency_ms"),
      e("dd", { "data-metric": "latency_ms" }, String(result.latencyMs ?? "—")),
      e("dt", null, "degradation_level"),
      e("dd", { "data-metric": "degradation_level" }, String(result.degradationLevel ?? 0))
    ),
    e("div", { className: "result-trace" }, "trace_id: ", traceId ?? "—", taskName ? ` · ${taskName}` : "")
  );
}

export function TaskPanel(props: {
  tasks: TaskState[];
  filter?: TaskStatus | "all";
  onFilter?: (f: TaskStatus | "all") => void;
}) {
  const filter = props.filter ?? "all";
  const rows =
    filter === "all" ? props.tasks : props.tasks.filter((t) => t.status === filter);

  return e(
    "section",
    { className: "panel task-panel", "data-view": "tasks" },
    e(
      "header",
      { className: "panel-header" },
      e("h2", null, "任务面板"),
      e(
        "div",
        { className: "task-filters" },
        ["all", "pending", "running", "done", "failed"].map((f) =>
          e(
            "button",
            {
              key: f,
              type: "button",
              "data-filter": f,
              "data-active": filter === f,
              onClick: () => props.onFilter?.(f as TaskStatus | "all"),
            },
            f
          )
        )
      )
    ),
    e(
      "ul",
      { className: "task-list", "data-task-count": rows.length },
      rows.length === 0
        ? e("p", { className: "empty-hint" }, "暂无任务")
        : rows.map((t) =>
            e(
              "li",
              {
                key: t.taskId,
                className: "task-item",
                "data-task-id": t.taskId,
                "data-status": t.status,
              },
              e(
                "div",
                { className: "task-head" },
                e("strong", null, t.workflowName),
                e("span", { className: `badge status-${t.status}` }, t.status)
              ),
              e(
                "div",
                { className: "task-meta" },
                `device=${t.device} · assigned=${t.assignedTo ?? "—"} · ${t.traceId}`
              ),
              t.result ? e(ResultCard, { result: t.result, traceId: t.traceId, taskName: t.workflowName }) : null,
              t.error
                ? e("div", { className: "task-error", role: "alert" }, t.error)
                : null
            )
          )
    )
  );
}
