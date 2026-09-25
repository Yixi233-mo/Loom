/**
 * SSE 传输 — 事件流挂在同一 EventBus（可选通道）。
 */

import type { BusMessage, Transport, TransportHandlers } from "./event-bus.ts";

export class SseTransport implements Transport {
  es: any = null;
  handlers: TransportHandlers | null = null;
  url: string;

  constructor(url: string) {
    this.url = url;
  }

  start(handlers: TransportHandlers): void {
    this.handlers = handlers;
    const ES = (globalThis as any).EventSource;
    if (!ES) {
      this.handlers?.onError?.(new Error("EventSource 不可用"));
      return;
    }
    this.es = new ES(this.url);
    this.es.onopen = () => this.handlers?.onOpen?.();
    this.es.onerror = (e: unknown) => this.handlers?.onError?.(e);
    this.es.onmessage = (ev: { data: string }) => {
      try {
        this.handlers?.onMessage(JSON.parse(ev.data) as BusMessage);
      } catch {
        /* ignore */
      }
    };
    for (const name of [
      "session.upsert",
      "message.appended",
      "message.delta",
      "task.updated",
      "task.result",
      "agent.status",
      "file.uploaded",
      "sync_broadcast",
    ]) {
      this.es.addEventListener?.(name, (ev: { data: string }) => {
        try {
          const data = JSON.parse(ev.data);
          this.handlers?.onMessage({ type: name, ...data });
        } catch {
          /* ignore */
        }
      });
    }
  }

  send(_msg: BusMessage): void {
    // SSE 单向：上行走 WS/REST
  }

  stop(): void {
    this.es?.close?.();
    this.es = null;
  }
}
