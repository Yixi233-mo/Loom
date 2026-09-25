/**
 * WebSocket 传输 — 挂到 EventBus。
 */

import type { BusMessage, Transport, TransportHandlers } from "./event-bus.ts";

export class WsTransport implements Transport {
  ws: WebSocket | null = null;
  handlers: TransportHandlers | null = null;
  url: string;
  wsFactory?: (url: string) => WebSocket;

  constructor(url: string, wsFactory?: (url: string) => WebSocket) {
    this.url = url;
    this.wsFactory = wsFactory;
  }

  start(handlers: TransportHandlers): void {
    this.handlers = handlers;
    const create =
      this.wsFactory ?? ((u: string) => new WebSocket(u) as WebSocket);
    this.ws = create(this.url);
    this.ws.onopen = () => this.handlers?.onOpen?.();
    this.ws.onclose = () => this.handlers?.onClose?.();
    this.ws.onerror = (e: unknown) => this.handlers?.onError?.(e);
    this.ws.onmessage = (ev: { data: unknown }) => {
      try {
        const msg = JSON.parse(String(ev.data)) as BusMessage;
        this.handlers?.onMessage(msg);
      } catch {
        /* ignore */
      }
    };
  }

  send(msg: BusMessage): void {
    if (this.ws && (this.ws as any).readyState === 1) {
      (this.ws as any).send(JSON.stringify(msg));
    }
  }

  stop(): void {
    (this.ws as any)?.close?.();
    this.ws = null;
  }
}
