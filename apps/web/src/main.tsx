import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./styles/index.css";

// 兼容：任意环境启动异常时不静默崩（手机 WebView / 旧内核）
if (typeof window !== "undefined") {
  window.addEventListener("error", (ev) => {
    try {
      console.error("[Loom]", ev?.message || ev);
      const el = document.getElementById("root");
      if (el && !el.getAttribute("data-boot-error")) {
        el.setAttribute("data-boot-error", "1");
        el.innerHTML =
          '<div style="padding:24px;font-family:sans-serif"><h3>Loom 启动遇到问题</h3><pre style="white-space:pre-wrap">' +
          String(ev?.message || ev).replace(/[<>&]/g, "") +
          "</pre></div>";
      }
    } catch {
      /* ignore */
    }
  });
  window.addEventListener("unhandledrejection", (ev) => {
    console.error("[Loom] unhandledrejection", ev);
  });
}

const el = document.getElementById("root");
if (!el) throw new Error("缺少 #root 挂载点");
createRoot(el).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
