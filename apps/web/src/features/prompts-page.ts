/**
 * 提示词页 — 自定义提示词 CRUD · 持久化 · 用于对话
 */

import * as React from "react";
import { PageShell, EmptyState } from "./page-states.ts";
import { UI } from "../components/index.ts";
import { promptStore, type PromptItem } from "../stores/prompt-store.ts";

const e = React.createElement;

export function PromptsPage(props: {
  onUseInChat?: (p: PromptItem) => void;
}) {
  const [list, setList] = React.useState<PromptItem[]>(() => promptStore.list());
  const [title, setTitle] = React.useState("");
  const [body, setBody] = React.useState("");
  const [tag, setTag] = React.useState("");
  const [editId, setEditId] = React.useState<string | null>(null);

  React.useEffect(() => {
    return promptStore.subscribe(() => setList(promptStore.list()));
  }, []);

  const reset = () => {
    setEditId(null);
    setTitle("");
    setBody("");
    setTag("");
  };

  const save = () => {
    const t = title.trim();
    const b = body.trim();
    if (!t || !b) return;
    promptStore.upsert({
      id: editId ?? undefined,
      title: t,
      body: b,
      tag: tag.trim() || undefined,
    });
    reset();
  };

  return e(
    PageShell,
    {
      route: "prompts",
      title: "提示词",
      subtitle: "自定义提示词模板 · 持久化保存 · 一键用于对话",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "prompt-reset-demo",
          onClick: () => promptStore.resetDemo(),
        },
        "恢复示例"
      ),
    },
    e(
      "div",
      { className: "prompts-page", "data-page": "prompts", "data-view": "prompts" },

      /* 编辑表单 */
      e(
        "div",
        { className: "prompt-editor glass", "data-view": "prompt-editor" },
        e("h3", null, editId ? "编辑提示词" : "新建提示词"),
        e("input", {
          className: UI.input,
          "data-field": "prompt-title",
          placeholder: "标题，如：代码审查",
          value: title,
          onChange: (ev: { target: { value: string } }) => setTitle(ev.target.value),
        }),
        e("input", {
          className: UI.input,
          "data-field": "prompt-tag",
          placeholder: "标签（可选），如：编码",
          value: tag,
          onChange: (ev: { target: { value: string } }) => setTag(ev.target.value),
        }),
        e("textarea", {
          className: UI.input,
          "data-field": "prompt-body",
          placeholder: "提示词正文…（可留空让用户补内容）",
          rows: 5,
          value: body,
          onChange: (ev: { target: { value: string } }) => setBody(ev.target.value),
        }),
        e(
          "div",
          { className: "prompt-actions" },
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonPrimary,
              "data-action": "prompt-save",
              disabled: !title.trim() || !body.trim(),
              onClick: save,
            },
            editId ? "保存修改" : "保存提示词"
          ),
          editId
            ? e(
                "button",
                {
                  type: "button",
                  className: UI.button + " " + UI.buttonGhost,
                  "data-action": "prompt-cancel",
                  onClick: reset,
                },
                "取消"
              )
            : null
        )
      ),

      /* 列表 */
      list.length === 0
        ? e(EmptyState, {
            title: "还没有提示词",
            hint: "在上方新建一条，发消息时可快速套用。",
          })
        : e(
            "ul",
            { className: "prompt-list", "data-prompt-count": String(list.length) },
            list.map((p) =>
              e(
                "li",
                {
                  key: p.id,
                  className: "prompt-card glass",
                  "data-prompt-id": p.id,
                },
                e(
                  "header",
                  null,
                  e("strong", null, p.title),
                  p.tag ? e("code", { className: "badge" }, p.tag) : null
                ),
                e("p", { className: "prompt-body" }, p.body),
                e(
                  "div",
                  { className: "prompt-actions" },
                  e(
                    "button",
                    {
                      type: "button",
                      className: UI.button + " " + UI.buttonPrimary,
                      "data-action": "prompt-use",
                      onClick: () => props.onUseInChat?.(p),
                    },
                    "用于对话"
                  ),
                  e(
                    "button",
                    {
                      type: "button",
                      className: UI.button + " " + UI.buttonGhost,
                      "data-action": "prompt-edit",
                      onClick: () => {
                        setEditId(p.id);
                        setTitle(p.title);
                        setBody(p.body);
                        setTag(p.tag ?? "");
                      },
                    },
                    "编辑"
                  ),
                  e(
                    "button",
                    {
                      type: "button",
                      className: UI.button + " " + UI.buttonDanger,
                      "data-action": "prompt-delete",
                      onClick: () => promptStore.remove(p.id),
                    },
                    "删除"
                  )
                )
              )
            )
          )
    )
  );
}
