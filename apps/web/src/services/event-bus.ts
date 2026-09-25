/**
 * 事件总线 — WS / SSE 统一订阅模型。
 */

export interface BusMessage {
  type: string;
  [key: string]: unknown;
}

export type TransportHandlers = {
  onMessage: (msg: BusMessage) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (err: unknown) => void;
};

/** 传输抽象：WS 与 SSE 均可挂到同一总线 */
export interface Transport {
  start(handlers: TransportHandlers): Promise<void> | void;
  send(msg: BusMessage): void;
  stop(): void;
}

type Listener = (msg: BusMessage) => void;

export class EventBus {
  private listeners = new Map<string, Set<Listener>>();
  private anyListeners = new Set<Listener>();
  private transport: Transport | null = null;
  private queue: BusMessage[] = [];

  on(type: string, fn: Listener): () => void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set());
    this.listeners.get(type)!.add(fn);
    return () => this.listeners.get(type)?.delete(fn);
  }

  onAny(fn: Listener): () => void {
    this.anyListeners.add(fn);
    return () => this.anyListeners.delete(fn);
  }

  /** 本地/回环投递（也供 transport 回调） */
  emit(msg: BusMessage): void {
    for (const fn of this.anyListeners) fn(msg);
    const set = this.listeners.get(msg.type);
    if (set) {
      for (const fn of [...set]) fn(msg);
    }
  }

  async attach(transport: Transport): Promise<void> {
    this.transport = transport;
    await transport.start({
      onMessage: (msg) => this.emit(msg),
    });
    // flush 队列
    const pending = this.queue.splice(0);
    for (const m of pending) transport.send(m);
  }

  send(msg: BusMessage): void {
    if (this.transport) this.transport.send(msg);
    else this.queue.push(msg); // 未连接先排队
  }

  stop(): void {
    this.transport?.stop();
    this.transport = null;
  }
}
