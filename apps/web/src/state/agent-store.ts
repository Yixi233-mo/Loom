/**
 * Agent 状态 — Agent 状态面板数据源。
 */

import { Store } from "./store.ts";
import type { AgentState, AgentStatus } from "../contracts/index.ts";

export type { AgentState };

function now(): number {
  return Date.now();
}

export class AgentStore extends Store<Map<string, AgentState>> {
  static create(): AgentStore {
    return new AgentStore(new Map());
  }

  upsert(agent: AgentState): void {
    this.set((m) => {
      const next = new Map(m);
      next.set(agent.agentName, {
        ...next.get(agent.agentName),
        ...agent,
        updatedAt: now(),
      });
      return next;
    });
  }

  setStatus(agentName: string, status: AgentStatus): void {
    this.set((m) => {
      const next = new Map(m);
      const a = next.get(agentName);
      if (!a) return m;
      next.set(agentName, { ...a, status, updatedAt: now() });
      return next;
    });
  }

  recordCall(
    agentName: string,
    info: {
      lastLatencyMs?: number;
      lastTokensUsed?: number;
      degradationLevel?: number;
    }
  ): void {
    this.set((m) => {
      const next = new Map(m);
      const a = next.get(agentName);
      if (!a) return m;
      next.set(agentName, {
        ...a,
        lastLatencyMs: info.lastLatencyMs ?? a.lastLatencyMs,
        lastTokensUsed: info.lastTokensUsed ?? a.lastTokensUsed,
        degradationLevel: info.degradationLevel ?? a.degradationLevel,
        status:
          (info.degradationLevel ?? 0) > 0
            ? "degraded"
            : a.status === "degraded"
              ? "online"
              : a.status,
        updatedAt: now(),
      });
      return next;
    });
  }

  getItem(agentName: string): AgentState | undefined {
    return this.get().get(agentName);
  }

  list(): AgentState[] {
    return [...this.get().values()].sort((a, b) =>
      a.agentName.localeCompare(b.agentName)
    );
  }
}

export function createAgent(
  init: Partial<AgentState> & { agentName: string }
): AgentState {
  return {
    status: "offline",
    capabilities: [],
    degradationLevel: 0,
    updatedAt: now(),
    ...init,
  };
}
