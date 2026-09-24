/**
 * 视图层入口 — 对话区 / 任务面板 / 文件区 组合。
 */

export { ChatPanel, MessageBubble } from "./chat-panel.ts";
export { TaskPanel, ResultCard } from "./task-panel.ts";
export { FilePanel } from "./file-panel.ts";
export { LlmSettingsPanel, type LlmProviderView } from "./llm-settings-panel.ts";
export { McpPanel, type McpProbeResult } from "./mcp-panel.ts";

import * as React from "react";
import { ChatPanel } from "./chat-panel.ts";
import { TaskPanel } from "./task-panel.ts";
import { FilePanel } from "./file-panel.ts";
import type { FileRef, SessionState, TaskState, TaskStatus } from "../contracts/index.ts";

const e = React.createElement;

export function Workspace(props: {
  session: SessionState;
  chatSize?: "default" | "expanded";
  onToggleSize?: () => void;
  chatBusy?: boolean;
  modelLabel?: string;
  tasks: TaskState[];
  files: FileRef[];
  filter?: TaskStatus | "all";
  onSend?: (text: string) => void;
  onDraft?: (text: string) => void;
  onFilter?: (f: TaskStatus | "all") => void;
  onUpload?: (file: { name: string; type: string; size: number }) => void;
  onDeleteFile?: (fileId: string) => void;
}) {
  return e(
    "div",
    { className: "workspace", "data-view": "workspace" },
    e(ChatPanel, {
      session: props.session,
      size: props.chatSize,
      onToggleSize: props.onToggleSize,
      onSend: props.onSend,
      onDraft: props.onDraft,
      busy: props.chatBusy,
      modelLabel: props.modelLabel,
    }),
    e(TaskPanel, {
      tasks: props.tasks,
      filter: props.filter,
      onFilter: props.onFilter,
    }),
    e(FilePanel, {
      files: props.files,
      onUpload: props.onUpload,
      onDelete: props.onDeleteFile,
    })
  );
}
