/**
 * 状态层核心 — 通用 Store（get / set / subscribe / 内存快照）。
 * 不绑框架，React 可用 useSyncExternalStore。
 */

export type Unsubscribe = () => void;

export class Store<T> {
  private state: T;
  private listeners = new Set<(s: T) => void>();

  constructor(initial: T) {
    this.state = initial;
  }

  get(): T {
    return this.state;
  }

  set(next: T | ((prev: T) => T)): void {
    this.state = typeof next === "function" ? (next as (p: T) => T)(this.state) : next;
    for (const fn of [...this.listeners]) fn(this.state);
  }

  patch(partial: Partial<T>): void {
    this.set((prev) => ({ ...prev, ...partial }));
  }

  subscribe(fn: (s: T) => void): Unsubscribe {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  reset(initial: T): void {
    this.set(initial);
  }
}
