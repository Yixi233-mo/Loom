/**
 * 对话区 — 消息流 + 流式 + 输入框。
 * 尺寸：default（固定高滑窗）/ expanded（放大）。
 * createElement 实现，便于 Node 测试；App 通过 store 驱动。
 */

import * as React from "react";
import type { SessionMessage, SessionState } from "../contracts/index.ts";

const e = React.createElement;

export type ChatSize = "default" | "expanded";

export function MessageBubble(props: { message: SessionMessage }) {
  const m = props.message;
  return e(
    "div",
    {
      className: `msg-bubble role-${m.role}`,
      "data-role": m.role,
      "data-message-id": m.id,
    },
    e(
      "div",
      { className: "msg-meta" },
      m.role,
      " · ",
      new Date(m.createdAt).toLocaleTimeString()
    ),
    e("div", { className: "msg-content" }, m.content)
  );
}

export function ChatPanel(props: {
  session: SessionState;
  size?: ChatSize;
  onToggleSize?: () => void;
  onSend?: (text: string) => void;
  onDraft?: (text: string) => void;
  busy?: boolean;
  modelLabel?: string;
}) {
  const { session, onSend, onDraft } = props;
  const size = props.size ?? "default";
  return e(
    "section",
    {
      className: `panel chat-panel size-${size}`,
      "data-view": "chat",
      "data-size": size,
    },
    e(
      "header",
      { className: "panel-header" },
      e(
        "div",
        { className: "chat-title" },
        e("h2", null, "对话区"),
        props.modelLabel
          ? e("span", { className: "chat-model", "data-model": "true" }, props.modelLabel)
          : null
      ),
      e(
        "div",
        { className: "chat-actions" },
        e(
          "span",
          { className: "panel-status", "data-status": session.status },
          session.status
        ),
        e(
          "button",
          {
            type: "button",
            "data-action": "toggle-size",
            "data-size": size,
            onClick: () => props.onToggleSize?.(),
          },
          size === "expanded" ? "还原" : "放大"
        )
      )
    ),
    e(
      "div",
      {
        className: "msg-list",
        "data-message-count": session.messages.length,
        "data-scroll-window": "true",
      },
      session.messages.length === 0
        ? e("p", { className: "empty-hint" }, "暂无消息，输入下方内容开始")
        : session.messages.map((m) =>
            e(MessageBubble, { key: m.id, message: m })
          )
    ),
    e(
      "form",
      {
        className: "chat-input",
        onSubmit: (ev: { preventDefault: () => void }) => {
          ev.preventDefault();
          const text = (session.draft || "").trim();
          if (!text || props.busy) return;
          onSend?.(text);
        },
      },
      e("input", {
        type: "text",
        "data-field": "draft",
        placeholder: props.busy
          ? "模型回复中…"
          : "输入消息…（Enter 发送）",
        value: session.draft,
        disabled: !!props.busy,
        onChange: (ev: { target: { value: string } }) =>
          onDraft?.(ev.target.value),
      }),
      e(
        "button",
        { type: "submit", "data-action": "send", disabled: !!props.busy },
        "发送"
      )
    )
  );
}
