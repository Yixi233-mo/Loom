/**
 * F0 契约 — 三端前端：DTO / 事件名 / REST 路径。
 *
 * 视图层只依赖本文件与状态层；服务层按此契约对接 Hub。
 */

// ---------------------------------------------------------------------------
// DTO：会话 / 任务 / Agent
// ---------------------------------------------------------------------------

export type SessionStatus = "idle" | "streaming" | "ended" | "error";

export interface SessionMessage {
  id: string;
  role: "user" | "assistant" | "system" | "tool";
  content: string;
  createdAt: number;
  /** 关联任务（结果卡片） */
  taskId?: string;
  /** 附件引用 */
  fileIds?: string[];
}

export interface SessionState {
  sessionId: string;
  title: string;
  status: SessionStatus;
  messages: SessionMessage[];
  updatedAt: number;
  /** 当前输入草稿（跨端续写） */
  draft: string;
}

export type TaskStatus =
  | "pending"
  | "assigned"
  | "running"
  | "done"
  | "failed";

export interface TaskResult {
  summary?: string;
  output?: unknown;
  tokensUsed?: number;
  latencyMs?: number;
  degradationLevel?: number;
}

export interface TaskState {
  taskId: string;
  workflowName: string;
  device: "pc" | "tablet" | "mobile" | "any";
  status: TaskStatus;
  assignedTo?: string;
  traceId: string;
  createdAt: number;
  updatedAt: number;
  result?: TaskResult;
  error?: string;
}

export type AgentStatus = "online" | "busy" | "degraded" | "offline";

export interface AgentState {
  agentName: string;
  status: AgentStatus;
  capabilities: string[];
  lastLatencyMs?: number;
  lastTokensUsed?: number;
  degradationLevel: number; // 0/1/2
  updatedAt: number;
}

export interface FileRef {
  fileId: string;
  name: string;
  size: number;
  mime: string;
  /** Hub 集中存储路径或 URL */
  uri: string;
  uploadedAt: number;
  sourceDeviceId?: string;
}

// ---------------------------------------------------------------------------
// 事件名（WS / SSE 统一）
// ---------------------------------------------------------------------------

export const EVENTS = {
  // 连接
  REGISTER: "register",
  REGISTERED: "registered",
  HEARTBEAT: "heartbeat",
  HEARTBEAT_ACK: "heartbeat_ack",
  ERROR: "error",

  // 触发 / 任务
  TRIGGER: "trigger",
  TRIGGER_ACK: "trigger_ack",
  TASK_DISPATCH: "task_dispatch",
  TASK_UPDATED: "task.updated",
  TASK_RESULT: "task.result",

  // 会话 / 对话
  SESSION_UPSERT: "session.upsert",
  MESSAGE_APPENDED: "message.appended",
  MESSAGE_DELTA: "message.delta",

  // Agent
  AGENT_STATUS: "agent.status",

  // 文件
  FILE_UPLOADED: "file.uploaded",

  // 同步
  SYNC_BROADCAST: "sync_broadcast",
} as const;

export type EventName = (typeof EVENTS)[keyof typeof EVENTS];

// ---------------------------------------------------------------------------
// REST API（F2 使用）
// ---------------------------------------------------------------------------

export const API = {
  /** 会话 */
  SESSIONS: "/api/sessions",
  SESSION: (id: string) => `/api/sessions/${id}`,
  SESSION_MESSAGES: (id: string) => `/api/sessions/${id}/messages`,

  /** 任务 */
  TASKS: "/api/tasks",
  TASK: (id: string) => `/api/tasks/${id}`,
  TASK_TRIGGER: "/api/tasks/trigger",

  /** Agent */
  AGENTS: "/api/agents",
  AGENT: (name: string) => `/api/agents/${name}`,

  /** 文件 */
  FILES: "/api/files",
  FILE: (id: string) => `/api/files/${id}`,
  FILE_UPLOAD: "/api/files/upload",

  /** 事件流（SSE 可选通道） */
  STREAM: "/api/stream",
} as const;
