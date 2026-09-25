/**
 * 会话状态 — 对话区数据源。
 */

import { Store } from "./store.ts";
import type { SessionMessage, SessionState, SessionStatus } from "../contracts/index.ts";

export type { SessionState };

function now(): number {
  return Date.now();
}

export function createSessionState(
  sessionId: string,
  title = "新会话"
): SessionState {
  return {
    sessionId,
    title,
    status: "idle",
    messages: [],
    updatedAt: now(),
    draft: "",
  };
}

export class SessionStore extends Store<SessionState> {
  static create(sessionId: string, title?: string): SessionStore {
    return new SessionStore(createSessionState(sessionId, title));
  }

  setStatus(status: SessionStatus): void {
    this.patch({ status, updatedAt: now() });
  }

  setDraft(draft: string): void {
    this.patch({ draft });
  }

  setTitle(title: string): void {
    this.patch({ title, updatedAt: now() });
  }

  appendMessage(msg: Omit<SessionMessage, "id" | "createdAt"> & Partial<SessionMessage>): SessionMessage {
    const full: SessionMessage = {
      id: msg.id ?? `msg-${now()}-${Math.random().toString(36).slice(2, 8)}`,
      createdAt: msg.createdAt ?? now(),
      role: msg.role,
      content: msg.content,
      taskId: msg.taskId,
      fileIds: msg.fileIds,
    };
    this.set((s) => ({
      ...s,
      messages: [...s.messages, full],
      updatedAt: now(),
    }));
    return full;
  }

  updateMessage(id: string, patch: Partial<SessionMessage>): void {
    this.set((s) => ({
      ...s,
      messages: s.messages.map((m) => (m.id === id ? { ...m, ...patch } : m)),
      updatedAt: now(),
    }));
  }

  /** 流式增量：追加到末条 assistant 消息或新建 */
  appendDelta(delta: string): SessionMessage {
    const s = this.get();
    const last = s.messages[s.messages.length - 1];
    if (last && last.role === "assistant") {
      const updated = { ...last, content: last.content + delta };
      this.updateMessage(last.id, updated);
      return updated;
    }
    return this.appendMessage({ role: "assistant", content: delta });
  }

  endSession(): void {
    this.setStatus("ended");
  }

  /** U2 新建对话：清空消息与草稿，换会话 */
  resetForNew(sessionId?: string, title = "新会话"): void {
    const id = sessionId ?? `sess-${Date.now()}`;
    this.reset(createSessionState(id, title));
  }
}
