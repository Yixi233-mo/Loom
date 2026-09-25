/**
 * 提示词库 — localStorage 持久化，可被对话套用
 */

export interface PromptItem {
  id: string;
  title: string;
  body: string;
  tag?: string;
  updatedAt?: number;
}

const KEY = "loom.prompts.v1";

const SEED: PromptItem[] = [
  {
    id: "p-code-review",
    title: "代码审查",
    body: "请审查以下代码：指出潜在 bug、安全风险与可读性问题，并给出修改建议：\n",
    tag: "编码",
    updatedAt: Date.now(),
  },
  {
    id: "p-summarize",
    title: "总结要点",
    body: "请用不超过 5 条要点总结以下内容，保留关键数字与结论：\n",
    tag: "办公",
    updatedAt: Date.now(),
  },
  {
    id: "p-translate",
    title: "中英互译",
    body: "将以下内容在中文与英文之间互译，保留术语与语气：\n",
    tag: "语言",
    updatedAt: Date.now(),
  },
];

function safeNow(): number {
  return Date.now();
}

export class PromptStore {
  private items: PromptItem[] = [];
  private listeners = new Set<() => void>();

  constructor() {
    this.items = this.load();
  }

  private load(): PromptItem[] {
    try {
      if (typeof localStorage === "undefined") return [...SEED];
      const raw = localStorage.getItem(KEY);
      if (!raw) return [...SEED];
      const parsed = JSON.parse(raw) as PromptItem[];
      return Array.isArray(parsed) ? parsed : [...SEED];
    } catch {
      return [...SEED];
    }
  }

  private persist(): void {
    try {
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(KEY, JSON.stringify(this.items));
      }
    } catch {
      /* ignore quota */
    }
    for (const fn of this.listeners) fn();
  }

  list(): PromptItem[] {
    return [...this.items].sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0));
  }

  get(id: string): PromptItem | undefined {
    return this.items.find((p) => p.id === id);
  }

  upsert(data: { id?: string; title: string; body: string; tag?: string }): PromptItem {
    const now = safeNow();
    if (data.id) {
      const idx = this.items.findIndex((p) => p.id === data.id);
      if (idx >= 0) {
        const next = { ...this.items[idx], ...data, updatedAt: now };
        this.items[idx] = next;
        this.persist();
        return next;
      }
    }
    const item: PromptItem = {
      id: "p-" + now.toString(36),
      title: data.title,
      body: data.body,
      tag: data.tag,
      updatedAt: now,
    };
    this.items.push(item);
    this.persist();
    return item;
  }

  remove(id: string): void {
    this.items = this.items.filter((p) => p.id !== id);
    this.persist();
  }

  clearAll(): void {
    this.items = [];
    this.persist();
  }

  resetDemo(): void {
    this.items = [...SEED];
    this.persist();
  }

  subscribe(fn: () => void): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }
}

export const promptStore = new PromptStore();
