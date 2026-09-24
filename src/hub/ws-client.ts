/**
 * Loom Hub WebSocket 客户端 — 浏览器端注册 / 触发 / 收结果。
 */

export type HubMessage = {
  type: string;
  [key: string]: unknown;
};

export type HubClientEvents = {
  onOpen?: () => void;
  onClose?: () => void;
  onMessage?: (msg: HubMessage) => void;
  onError?: (err: Event | Error) => void;
};

const WS_URL =
  (import.meta as any).env?.VITE_WS_URL ?? "ws://127.0.0.1:8765/ws";
const WS_SECRET =
  (import.meta as any).env?.VITE_WS_SECRET ?? "dev-secret";

async function hmacSha256Hex(key: string, message: string): Promise<string> {
  const enc = new TextEncoder();
  const cryptoKey = await crypto.subtle.importKey(
    "raw",
    enc.encode(key),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", cryptoKey, enc.encode(message));
  return [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export async function signRegister(
  deviceId: string,
  deviceType: string,
  ts: number,
  secret: string = WS_SECRET
): Promise<string> {
  return hmacSha256Hex(secret, `${deviceId}:${deviceType}:${ts}`);
}

export class HubClient {
  private ws: WebSocket | null = null;
  private deviceId: string;
  private deviceType: string;
  private events: HubClientEvents;
  private closedByUser = false;

  constructor(
    deviceId: string,
    deviceType: "pc" | "tablet" | "mobile",
    events: HubClientEvents = {}
  ) {
    this.deviceId = deviceId;
    this.deviceType = deviceType;
    this.events = events;
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /** 是否由调用方主动 close（用于区分异常断开） */
  get intentionalClose(): boolean {
    return this.closedByUser;
  }

  async connect(): Promise<void> {
    this.closedByUser = false;
    this.ws = new WebSocket(WS_URL);
    this.ws.onopen = async () => {
      await this.register();
      this.events.onOpen?.();
    };
    this.ws.onclose = () => {
      this.events.onClose?.();
    };
    this.ws.onerror = (e) => {
      this.events.onError?.(e);
    };
    this.ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(String(ev.data)) as HubMessage;
        this.events.onMessage?.(msg);
      } catch {
        /* ignore non-json */
      }
    };
  }

  async register(): Promise<void> {
    const ts = Date.now() / 1000;
    const signature = await signRegister(this.deviceId, this.deviceType, ts);
    this.send({
      type: "register",
      device_id: this.deviceId,
      device_type: this.deviceType,
      capabilities: ["notifications"],
      ts,
      signature,
    });
  }

  trigger(workflowName: string, traceId?: string): void {
    this.send({
      type: "trigger",
      workflow: { name: workflowName, device: "pc" },
      trace_id: traceId ?? `web-${Date.now()}`,
    });
  }

  heartbeat(): void {
    this.send({
      type: "heartbeat",
      device_id: this.deviceId,
      ts: Date.now() / 1000,
    });
  }

  private send(obj: Record<string, unknown>): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(obj));
    }
  }

  close(): void {
    this.closedByUser = true;
    this.ws?.close();
  }
}
