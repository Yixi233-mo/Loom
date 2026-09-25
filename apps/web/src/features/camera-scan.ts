/**
 * RS4 移动端相机扫码 — 扫电脑上的配对码/链接
 * 浏览器 BarcodeDetector；不支持时退回手动输入
 */
import * as React from "react";
import { UI } from "../components/index.ts";

const e = React.createElement;

export type ScanResult = {
  text: string;
  /** 解析出的 host/port（若有） */
  host?: string;
  port?: number;
};

export function parseScanText(text: string): ScanResult {
  const t = (text || "").trim();
  // loom://pair?host=x&port=8765 或 http://ip/#/devices?pair=..&host=..&port=8765
  try {
    const u = new URL(t);
    const host =
      u.searchParams.get("host") ||
      u.hostname ||
      undefined;
    const port = Number(u.searchParams.get("port") || u.port || 8765) || 8765;
    return { text: t, host: host || undefined, port };
  } catch {
    // host:port 或 纯 IP
    const m = t.match(/^(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{1,5}))?$/);
    if (m) return { text: t, host: m[1], port: Number(m[2] || 8765) };
    return { text: t };
  }
}

type BarcodeDetectorLike = {
  detect(source: CanvasImageSource): Promise<Array<{ rawValue: string }>>;
};

function getBarcodeDetector(): BarcodeDetectorLike | null {
  const g = globalThis as any;
  if (typeof g.BarcodeDetector === "function") {
    try {
      return new g.BarcodeDetector({ formats: ["qr_code"] });
    } catch {
      return null;
    }
  }
  return null;
}

export function CameraScanner(props: {
  onResult?: (r: ScanResult) => void;
  onClose?: () => void;
}) {
  const videoRef = React.useRef<HTMLVideoElement | null>(null);
  const [err, setErr] = React.useState("");
  const [manual, setManual] = React.useState("");
  const [scanning, setScanning] = React.useState(false);
  const streamRef = React.useRef<MediaStream | null>(null);

  const stop = React.useCallback(() => {
    try {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    } catch {
      /* ignore */
    }
    streamRef.current = null;
    setScanning(false);
  }, []);

  React.useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    async function start() {
      const nav: any = (globalThis as any).navigator;
      if (!nav?.mediaDevices?.getUserMedia) {
        setErr("当前环境不支持相机，请用手动输入");
        return;
      }
      try {
        const stream = await nav.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
          audio: false,
        });
        if (cancelled) {
          stream.getTracks().forEach((t: MediaStreamTrack) => t.stop());
          return;
        }
        streamRef.current = stream;
        const video = videoRef.current;
        if (video) {
          video.srcObject = stream;
          await video.play().catch(() => undefined);
        }
        setScanning(true);
        const det = getBarcodeDetector();
        if (!det) {
          setErr("此浏览器无扫码引擎，请手动输入连接信息");
          return;
        }
        const tick = async () => {
          if (cancelled || !videoRef.current) return;
          try {
            const hits = await det.detect(videoRef.current);
            const raw = hits?.[0]?.rawValue;
            if (raw) {
              stop();
              props.onResult?.(parseScanText(raw));
              return;
            }
          } catch {
            /* ignore frame */
          }
          timer = setTimeout(() => void tick(), 400);
        };
        void tick();
      } catch {
        setErr("无法打开相机（请允许相机权限），或使用手动输入");
      }
    }

    void start();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      stop();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return e(
    "div",
    {
      className: "camera-scanner glass",
      "data-view": "camera-scanner",
      "data-testid": "camera-scanner",
    },
    e(
      "div",
      { className: "camera-scanner-head" },
      e("strong", null, "扫码连接"),
      e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "scan-close",
          onClick: () => {
            stop();
            props.onClose?.();
          },
        },
        "关闭"
      )
    ),
    e(
      "div",
      { className: "camera-frame" },
      e("video", {
        ref: videoRef,
        playsInline: true,
        muted: true,
        "data-scanning": scanning ? "true" : "false",
        "aria-label": "相机取景",
      }),
      e("div", { className: "camera-hint" }, "把电脑上的二维码对准框内")
    ),
    err ? e("p", { className: "pairing-err" }, err) : null,
    e(
      "div",
      { className: "pairing-manual" },
      e("span", { className: "pairing-code-label" }, "手动连接"),
      e(
        "div",
        { className: "pairing-manual-row" },
        e("input", {
          className: "pairing-input",
          placeholder: "192.168.x.x:8765 或粘贴链接",
          value: manual,
          "data-field": "scan-manual",
          onChange: (ev: any) => setManual(String(ev.target.value || "")),
        }),
        e(
          "button",
          {
            type: "button",
            className: UI.button + " " + UI.buttonPrimary,
            "data-action": "scan-manual-submit",
            onClick: () => {
              const r = parseScanText(manual);
              if (!r.host && !r.text) return;
              stop();
              props.onResult?.(r);
            },
          },
          "连接"
        )
      )
    )
  );
}
