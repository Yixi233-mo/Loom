/**
 * Tauri IPC 桥 — 无 Tauri 环境时优雅降级到 mock / 抛出友好错误。
 *
 * 对齐 src-tauri plugin_loader 等命令名（# 需确认当前版本API 可扩展）。
 */

export interface TauriInvokeArgs {
  [key: string]: unknown;
}

export type TauriInvokeFn = (cmd: string, args?: TauriInvokeArgs) => Promise<any>;

export interface TauriLike {
  invoke: TauriInvokeFn;
}

/** 探测是否运行在 Tauri WebView */
export function getTauri(): TauriLike | null {
  const t = (globalThis as any).__TAURI__;
  if (t?.core?.invoke) {
    return { invoke: t.core.invoke.bind(t.core) };
  }
  if (t?.tauri?.invoke) {
    return { invoke: t.tauri.invoke.bind(t.tauri) };
  }
  return null;
}

export class TauriBridge {
  impl: TauriLike | null;
  mockCalls: Array<{ cmd: string; args?: TauriInvokeArgs }> = [];
  mockResult: unknown = null;

  constructor(impl?: TauriLike | null) {
    this.impl = impl === undefined ? getTauri() : impl;
  }

  get available(): boolean {
    return this.impl !== null;
  }

  async invoke(cmd: string, args?: TauriInvokeArgs): Promise<any> {
    if (this.impl) {
      return this.impl.invoke(cmd, args);
    }
    // 降级：记录 mock 调用，返回 mockResult（便于测试/无 Tauri 演示）
    this.mockCalls.push({ cmd, args });
    if (this.mockResult !== null) return this.mockResult;
    if (cmd === "list_plugins") return [];
    if (cmd === "read_text_file") return "";
    if (cmd === "write_text_file") return { ok: true };
    return { ok: true, mock: true, cmd, args };
  }

  /** 插件加载器（Rust plugin_loader.rs） */
  listPlugins(root?: string): Promise<Array<{ name: string; version: string }>> {
    return this.invoke("list_plugins", { root });
  }

  /** 文件读写（DSL 编辑器可接） */
  readTextFile(path: string): Promise<string> {
    return this.invoke("read_text_file", { path });
  }

  writeTextFile(path: string, content: string): Promise<unknown> {
    return this.invoke("write_text_file", { path, content });
  }
}
