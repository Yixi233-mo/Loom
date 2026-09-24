/**
 * FE.1 Feature 聚合 — 按业务域组织，底层仍复用 views/state/services。
 * 仅 re-export `.ts` 实现，保证 `node --experimental-strip-types` 可测。
 * FE.3 将在此扩展对话工作台 / 任务中心 / 设置 / 技能树页面组件。
 */

export * as chat from "../views/chat-panel.ts";
export * as tasks from "../views/task-panel.ts";
export * as files from "../views/file-panel.ts";
export * as llm from "../views/llm-settings-panel.ts";
export * as mcp from "../views/mcp-panel.ts";
export * as dsl from "../shell/dsl-editor.impl.ts";

export type FeatureId =
  | "chat"
  | "tasks"
  | "files"
  | "llm"
  | "mcp"
  | "dsl"
  | "skills";

export interface FeatureMeta {
  id: FeatureId;
  title: string;
  /** 技能树节点：点亮条件描述 */
  unlockHint: string;
}

export const FEATURES: FeatureMeta[] = [
  { id: "chat", title: "对话", unlockHint: "Hub 在线即可用" },
  { id: "tasks", title: "任务", unlockHint: "有可调度 Workflow 时点亮" },
  { id: "files", title: "文件", unlockHint: "连接 Hub 存储后点亮" },
  { id: "llm", title: "自定义 LLM", unlockHint: "配置并测试通过后点亮" },
  { id: "mcp", title: "MCP 服务", unlockHint: "检测连接成功后点亮" },
  { id: "dsl", title: "DSL 扩展", unlockHint: "校验并保存后解锁" },
  { id: "skills", title: "技能树", unlockHint: "设备与 Agent 全景" },
];
