/**
 * FE.3 对话工作台 — 消息流 + 输入 + 模型态 + 完整页面状态
 * FE.6 — 消息行 memo
 */

import * as React from "react";
import type { SessionMessage, SessionState } from "../contracts/index.ts";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageShell,
  phaseOf,
} from "./page-states.ts";
import { TaskPreviewCard, type TaskPreview } from "./connect-wizard.ts";
import { UI } from "../components/index.ts";


import { memo } from "../perf/index.ts";

export type PromptChip = { id: string; title: string; body: string; updatedAt?: number };

const e = React.createElement;

function formatTime(ts?: number): string {
  if (!ts) return "";
  const d = new Date(ts);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function MessageRowImpl(props: {
  message: SessionMessage;
  onCopy?: (text: string) => void;
  onRetry?: (text: string) => void;
  onOpenTask?: (taskId: string) => void;
}) {
  const m = props.message;
  const isUser = m.role === "user";
  const name = isUser ? "你" : m.role === "assistant" ? "Loom" : m.role;
  return e(
    "article",
    {
      className: `msg-row msg-row--${isUser ? "user" : "assistant"}`,
      "data-role": m.role,
      "data-message-id": m.id,
    },
    e(
      "div",
      {
        className: "msg-avatar",
        "data-avatar": isUser ? "user" : "bot",
        "aria-hidden": "true",
      },
      isUser ? "我" : "巢"
    ),
    e(
      "div",
      { className: "msg-bubble role-" + m.role },
      e(
        "div",
        { className: "msg-meta" },
        e("span", { className: "msg-author" }, name),
        e("span", { className: "msg-time" }, formatTime(m.createdAt))
      ),
      e("div", { className: "msg-content" }, m.content),
      m.taskId
        ? e(
            "button",
            {
              type: "button",
              className: "msg-task-tag",
              "data-task-id": m.taskId,
              "data-action": "goto-task",
              title: "打开任务中心",
              onClick: () => props.onOpenTask?.(String(m.taskId)),
            },
            `任务 ${m.taskId}`
          )
        : null,
      e(
        "div",
        { className: "msg-actions", "data-view": "msg-actions" },
        e(
          "button",
          {
            type: "button",
            className: "msg-action",
            "data-action": "msg-copy",
            onClick: () => props.onCopy?.(m.content),
          },
          "复制"
        ),
        e(
          "button",
          {
            type: "button",
            className: "msg-action",
            "data-action": "msg-retry",
            onClick: () => props.onRetry?.(m.content),
          },
          "重试"
        ),
        e(
          "button",
          {
            type: "button",
            className: "msg-action",
            "data-action": "msg-quote",
            onClick: () => props.onCopy?.(m.content),
          },
          "引用"
        )
      )
    )
  );
}

export const MessageRow = memo(MessageRowImpl);

export function PromptChips(props: {
  items: PromptChip[];
  activeId?: string | null;
  onPick?: (p: PromptChip) => void;
  onClear?: () => void;
  onManage?: () => void;
}) {
  return e(
    "div",
    { className: "prompt-chips", "data-view": "prompt-chips" },
    e("span", { className: "prompt-chips-label" }, "提示词"),
    props.items.slice(0, 6).map((p) =>
      e(
        "button",
        {
          key: p.id,
          type: "button",
          className:
            "chip" + (props.activeId === p.id ? " is-on" : ""),
          "data-prompt-id": p.id,
          "data-action": "pick-prompt",
          onClick: () => props.onPick?.(p),
        },
        p.title
      )
    ),
    props.activeId
      ? e(
          "button",
          {
            type: "button",
            className: "chip chip-clear",
            "data-action": "clear-prompt",
            onClick: () => props.onClear?.(),
          },
          "清除"
        )
      : null,
    e(
      "button",
      {
        type: "button",
        className: "chip chip-manage",
        "data-action": "manage-prompts",
        onClick: () => props.onManage?.(),
      },
      "管理"
    )
  );
}

export function ChatWorkbench(props: {
  session: SessionState;
  loading?: boolean;
  error?: string | null;
  busy?: boolean;
  modelLabel?: string;
  models?: string[];
  onModelChange?: (model: string) => void;
  chatSize?: "default" | "expanded";
  onSend?: (text: string) => void;
  onDraft?: (text: string) => void;
  onToggleSize?: () => void;
  onRetry?: () => void;
  onNewChat?: () => void;
  onAttach?: () => void;
  onCopy?: (text: string) => void;
  onRetryMessage?: (text: string) => void;
  onOpenTask?: (taskId: string) => void;
  prompts?: PromptChip[];
  activePromptId?: string | null;
  activePromptTitle?: string;
  onPickPrompt?: (p: PromptChip) => void;
  onClearPrompt?: () => void;
  onManagePrompts?: () => void;
  /** E3 说话即任务：待确认预览 */
  pendingPreview?: TaskPreview | null;
  onConfirmPreview?: (p: TaskPreview) => void;
  onCancelPreview?: () => void;
}) {
  const phase = phaseOf({
    loading: props.loading,
    error: props.error,
    empty: !props.loading && !props.error && props.session.messages.length === 0,
  });
  const draft = props.session.draft;
  const canSend =
    !!props.onSend && draft.trim().length > 0 && !props.busy && phase === "ready";

  return e(
    PageShell,
    {
      route: "chat",
      title: "对话工作台",
      subtitle: props.modelLabel
        ? `当前模型 · ${props.modelLabel}`
        : "未选择模型时使用本地回声",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonPrimary,
          "data-action": "toggle-chat-size",
          onClick: () => props.onToggleSize?.(),
        },
        props.chatSize === "expanded" ? "收起" : "放大"
      ),
    },
    e(
      "div",
      {
        className: `chat-workbench chat-workbench--${props.chatSize ?? "expanded"}`,
        "data-chat-size": props.chatSize ?? "expanded",
        "data-phase": phase,
      },
      phase === "loading"
        ? e(LoadingState, { label: "正在载入会话…", rows: 3 })
        : phase === "error"
          ? e(ErrorState, {
              title: "会话加载失败",
              message: props.error ?? "未知错误",
              onRetry: props.onRetry,
            })
          : phase === "empty"
            ? e(
                "div",
                { className: "chat-empty", "data-view": "chat-empty" },
                e(EmptyState, {
                  title: "开始一段新对话",
                  hint: "问问题、丢文件，或点下方快捷任务。侧栏「新建对话」可随时清空重来。",
                  actionLabel: "试试：帮我总结这份 PDF",
                  onAction: () => props.onSend?.("帮我总结这份 PDF"),
                }),
                e(
                  "div",
                  { className: "chat-starters", "data-view": "chat-starters" },
                  ...[
                    ["帮我规划今天的任务", "规划"],
                    ["查资料：项目怎么部署", "查资料"],
                    ["审查这段代码的潜在问题", "审查代码"],
                  ].map(([text, label]) =>
                    e(
                      "button",
                      {
                        key: text,
                        type: "button",
                        className: "chat-starter",
                        "data-action": "chat-starter",
                        onClick: () => props.onSend?.(text),
                      },
                      label
                    )
                  )
                )
              )
            : e(
                "div",
                {
                  className: "chat-stream",
                  "data-view": "chat-stream",
                },
                props.session.messages.map((m) =>
                  e(MessageRow, {
                    key: m.id,
                    message: m,
                    onCopy: props.onCopy,
                    onRetry: props.onRetryMessage,
                    onOpenTask: props.onOpenTask,
                  })
                )
              ),
      e(PromptChips, {
        items: props.prompts ?? [],
        activeId: props.activePromptId,
        onPick: props.onPickPrompt,
        onClear: props.onClearPrompt,
        onManage: props.onManagePrompts,
      }),
      props.pendingPreview
        ? e(TaskPreviewCard, {
            preview: props.pendingPreview,
            onConfirm: props.onConfirmPreview,
            onCancel: props.onCancelPreview,
          })
        : null,

      e(
        "form",
        {
          className: "chat-composer",
          "data-view": "chat-composer",
          onSubmit: (ev: { preventDefault: () => void }) => {
            ev.preventDefault();
            if (canSend && props.onSend) props.onSend(draft);
          },
        },
        e(
          "button",
          {
            type: "button",
            className: "composer-icon",
            "data-action": "chat-attach",
            title: "添加附件",
            onClick: () => props.onAttach?.(),
          },
          "＋"
        ),
        props.models && props.models.length > 0
          ? e(
              "select",
              {
                className: "composer-model",
                "data-field": "chat-model",
                "aria-label": "模型",
                value: props.modelLabel ?? props.models[0],
                onChange: (ev: { target: { value: string } }) =>
                  props.onModelChange?.(ev.target.value),
              },
              ...props.models.map((m) => e("option", { key: m, value: m }, m))
            )
          : e("span", { className: "composer-model-label" }, props.modelLabel || "本地回声"),
        e("input", {
          className: UI.input,
          "data-field": "chat-draft",
          placeholder: props.busy ? "处理中…可继续输入，稍后发送" : "输入消息，Enter 发送…",
          value: draft,
          disabled: props.busy || phase === "loading",
          onChange: (ev: { target: { value: string } }) =>
            props.onDraft?.(ev.target.value),
        }),
        e(
          "button",
          {
            type: "submit",
            className: UI.button + " " + UI.buttonPrimary,
            "data-action": "chat-send",
            disabled: !canSend,
          },
          props.busy ? "发送中…" : "发送"
        )
      )
    )
  );
}
