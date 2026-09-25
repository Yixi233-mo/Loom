/**
 * 状态层入口 — 三端共享应用状态。
 */

export { Store } from "./store.ts";
export { SessionStore, createSessionState } from "./session-store.ts";
export { TaskStore, createTask } from "./task-store.ts";
export { AgentStore, createAgent } from "./agent-store.ts";

import { SessionStore } from "./session-store.ts";
import { TaskStore } from "./task-store.ts";
import { AgentStore } from "./agent-store.ts";

export interface AppStores {
  session: SessionStore;
  tasks: TaskStore;
  agents: AgentStore;
}

export function createAppStores(sessionId = "sess-1"): AppStores {
  return {
    session: SessionStore.create(sessionId),
    tasks: TaskStore.create(),
    agents: AgentStore.create(),
  };
}
