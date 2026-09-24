/**
 * 任务状态 — 任务面板 / 结果卡片数据源。
 */

import { Store } from "./store.ts";
import type { TaskResult, TaskState, TaskStatus } from "../contracts/index.ts";

export type { TaskState };

function now(): number {
  return Date.now();
}

export class TaskStore extends Store<Map<string, TaskState>> {
  static create(): TaskStore {
    return new TaskStore(new Map());
  }

  upsert(task: TaskState): void {
    this.set((m) => {
      const next = new Map(m);
      next.set(task.taskId, { ...next.get(task.taskId), ...task, updatedAt: now() });
      return next;
    });
  }

  setStatus(taskId: string, status: TaskStatus): void {
    this.set((m) => {
      const next = new Map(m);
      const t = next.get(taskId);
      if (!t) return m;
      next.set(taskId, { ...t, status, updatedAt: now() });
      return next;
    });
  }

  setResult(taskId: string, result: TaskResult, status: TaskStatus = "done"): void {
    this.set((m) => {
      const next = new Map(m);
      const t = next.get(taskId);
      if (!t) return m;
      next.set(taskId, { ...t, result, status, updatedAt: now() });
      return next;
    });
  }

  setError(taskId: string, error: string): void {
    this.set((m) => {
      const next = new Map(m);
      const t = next.get(taskId);
      if (!t) return m;
      next.set(taskId, { ...t, error, status: "failed", updatedAt: now() });
      return next;
    });
  }

  getItem(taskId: string): TaskState | undefined {
    return this.get().get(taskId);
  }

  list(): TaskState[] {
    return [...this.get().values()].sort((a, b) => b.updatedAt - a.updatedAt);
  }

  listByStatus(status: TaskStatus): TaskState[] {
    return this.list().filter((t) => t.status === status);
  }
}

export function createTask(init: {
  taskId: string;
  workflowName: string;
  traceId: string;
  device?: TaskState["device"];
  status?: TaskStatus;
  assignedTo?: string;
}): TaskState {
  const ts = now();
  return {
    taskId: init.taskId,
    workflowName: init.workflowName,
    traceId: init.traceId,
    device: init.device ?? "any",
    status: init.status ?? "pending",
    assignedTo: init.assignedTo,
    createdAt: ts,
    updatedAt: ts,
  };
}
