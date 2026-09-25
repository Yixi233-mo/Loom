/**
 * FE.1 状态层域入口 — 保留 session/tasks/agents，新增 ui。
 */

export {
  Store,
  SessionStore,
  createSessionState,
  TaskStore,
  createTask,
  AgentStore,
  createAgent,
  createAppStores,
  type AppStores,
} from "../state/index.ts";

export { UiStore, createUiState, type UiState, type ChatSize } from "./ui-store.ts";

import { createAppStores, type AppStores } from "../state/index.ts";
import { UiStore } from "./ui-store.ts";

export interface RootStores extends AppStores {
  ui: UiStore;
}

export function createRootStores(sessionId = "sess-1"): RootStores {
  const base = createAppStores(sessionId);
  return {
    ...base,
    ui: UiStore.create(),
  };
}
