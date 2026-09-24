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
import { UI } from "../components/index.ts";


import { memo } from "../perf/index.ts";

export type PromptChip = { id: string; title: string; body: string; updatedAt?: number };

const e = React.createElement;

function MessageRowImpl(props: { message: SessionMessage }) {
  const m = props.message;
  return e(
    "article",
    {
      className: `msg-bubble role-${m.role}`,
      "data-role": m.role,
      "data-message-id": m.id,
    },
    e(
      "div",
      { className: "msg-meta" },
      m.role === "user" ? "你" : m.role === "assistant" ? "Loom" : m.role
    ),
    e("div", { className: "msg-content" }, m.content),
    m.taskId
      ? e(
          "div",
          { className: "msg-task-link", "data-task-id": m.taskId },
          `关联任务 ${m.taskId}`
        )
      : null
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
  chatSize?: "default" | "expanded";
  onSend?: (text: string) => void;
  onDraft?: (text: string) => void;
  onToggleSize?: () => void;
  onRetry?: () => void;
  prompts?: PromptChip[];
  activePromptId?: string | null;
  activePromptTitle?: string;
  onPickPrompt?: (p: PromptChip) => void;
  onClearPrompt?: () => void;
  onManagePrompts?: () => void;
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
            ? e(EmptyState, {
                title: "还没有对话",
                hint: "在下方输入，开始和 Agent 协作。",
                actionLabel: "试试：帮我总结这份 PDF",
                onAction: () => props.onSend?.("帮我总结这份 PDF"),
              })
            : e(
                "div",
                {
                  className: "chat-stream",
                  "data-view": "chat-stream",
                },
                props.session.messages.map((m) =>
                  e(MessageRow, { key: m.id, message: m })
                )
              ),
      e(PromptChips, {
        items: props.prompts ?? [],
        activeId: props.activePromptId,
        onPick: props.onPickPrompt,
        onClear: props.onClearPrompt,
        onManage: props.onManagePrompts,
      }),
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
        e("input", {
          className: UI.input,
          "data-field": "chat-draft",
          placeholder: "输入消息，Enter 发送…",
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
