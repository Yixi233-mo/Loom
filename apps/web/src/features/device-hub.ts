/**
 * 一个 Loom — 跨端无感接力（手机发起 · PC 执行 · 全端可见）
 * 回答：MCP 在 PC/Hub；手机看任务、分发、触发；状态经 Sync 实时同步。
 */

import * as React from "react";
import { PageShell } from "./page-states.ts";
import { UI } from "../components/index.ts";

const e = React.createElement;

export type DeviceKind = "pc" | "tablet" | "mobile";

export interface DeviceCard {
  deviceId: string;
  name: string;
  kind: DeviceKind;
  online: boolean;
  lastSeen?: string;
  capabilities?: string[];
}

export function DeviceHubPage(props: {
  devices?: DeviceCard[];
  hubOnline?: boolean;
  syncVersion?: number;
  pendingTasks?: number;
  runningTasks?: number;
  doneTasks?: number;
  onlineAgents?: number;
  onRefresh?: () => void;
  onPing?: (deviceId: string) => void;
  layout?: "wide" | "medium" | "compact" | "narrow";
}) {
  const devices = props.devices ?? [
    { deviceId: "hub-pc-1", name: "本机 Hub / PC", kind: "pc" as const, online: true, lastSeen: "刚刚", capabilities: ["shell.exec", "file.read", "MCP 工具"] },
    { deviceId: "tablet-demo", name: "平板（示例）", kind: "tablet" as const, online: false, lastSeen: "未连接", capabilities: ["file.read", "查看任务"] },
    { deviceId: "mobile-demo", name: "手机（示例）", kind: "mobile" as const, online: false, lastSeen: "未连接", capabilities: ["任务分发", "拍照上传", "通知"] },
  ];

  const pcOnly = [
    { t: "MCP 外接", d: "Claude Code / Work Buddy 连接与工具调用（在 Hub/PC 配置一次）" },
    { t: "DSL 编辑 / 热加载", d: "改 YAML 扩展能力，Hub 2s 内生效" },
    { t: "自定义 LLM Key", d: "密钥加密存 PC/Hub，端上只用不存" },
    { t: "文件重操作 / Shell", d: "PC 能力：shell.exec、大文件处理" },
  ];
  const phoneCan = [
    { t: "任务列表 / 详情", d: "实时看排队、执行中、结果卡片（tokens/延迟/降级）" },
    { t: "任务分发", d: "点选目标设备（PC/平板）触发 Workflow，离线自动排队" },
    { t: "对话下任务", d: "发一句话 → Hub 意图识别 → 路由到合适端执行" },
    { t: "文件查看 / 上传", d: "手机拍照/选文件上传到 Hub，PC 再处理" },
    { t: "通知与成就", d: "跨端完成弹出暖色成就卡；系统通知" },
    { t: "技能树状态", d: "看设备/Agent/工具点亮情况，点一下跳配置（配置仍在 PC）" },
  ];

  return e(
    PageShell,
    {
      route: "devices",
      title: "跨端控制台",
      subtitle: "信息与任务经 Sync 实时同步 · MCP 只在 PC/Hub 配置一次",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonPrimary,
          "data-action": "devices-refresh",
          onClick: () => props.onRefresh?.(),
        },
        "刷新状态"
      ),
    },
    e(
      "div",
      {
        className: "device-hub",
        "data-page": "devices",
        "data-view": "device-hub",
        "data-layout": props.layout ?? "wide",
      },

      /* 同步摘要 */
      e(
        "div",
        { className: "device-stats glass", "data-view": "sync-summary" },
        e("div", { className: "stat" },
          e("strong", null, props.hubOnline === false ? "离线" : "在线"),
          e("span", null, "Hub")
        ),
        e("div", { className: "stat" },
          e("strong", null, String(props.syncVersion ?? 0)),
          e("span", null, "同步版本")
        ),
        e("div", { className: "stat" },
          e("strong", null, String(props.pendingTasks ?? 0)),
          e("span", null, "排队")
        ),
        e("div", { className: "stat" },
          e("strong", null, String(props.runningTasks ?? 0)),
          e("span", null, "执行中")
        ),
        e("div", { className: "stat" },
          e("strong", null, String(props.doneTasks ?? 0)),
          e("span", null, "已完成")
        ),
        e("div", { className: "stat" },
          e("strong", null, String(props.onlineAgents ?? 0)),
          e("span", null, "Agent 在线")
        )
      ),

      /* 设备列表 */
      e(
        "section",
        { className: "device-list-block" },
        e("h3", null, "设备"),
        e(
          "div",
          { className: "device-list" },
          devices.map((d) =>
            e(
              "article",
              {
                key: d.deviceId,
                className: "device-card glass" + (d.online ? " is-on" : ""),
                "data-device-id": d.deviceId,
                "data-online": d.online ? "true" : "false",
              },
              e(
                "header",
                null,
                e("strong", null, d.name),
                e(
                  "span",
                  { className: "badge " + (d.online ? "ok" : "todo") },
                  d.online ? "在线" : "离线"
                )
              ),
              e("p", { className: "hint" }, `${d.kind} · ${d.lastSeen || ""}`),
              e(
                "div",
                { className: "plugin-tools" },
                (d.capabilities || []).map((c) => e("code", { key: c }, c))
              ),
              e(
                "button",
                {
                  type: "button",
                  className: "ui-button ui-button--ghost",
                  "data-action": "ping-device",
                  disabled: !d.online,
                  onClick: () => props.onPing?.(d.deviceId),
                },
                "下发测试任务"
              )
            )
          )
        )
      ),

      /* 能力矩阵 */
      e(
        "section",
        { className: "device-matrix" },
        e(
          "div",
          { className: "matrix-card glass" },
          e("h3", null, "PC / Hub 负责（只配一次）"),
          e("ul", null, pcOnly.map((x) => e("li", { key: x.t }, e("strong", null, x.t), " — ", x.d)))
        ),
        e(
          "div",
          { className: "matrix-card glass" },
          e("h3", null, "手机 / 平板 能做什么"),
          e("ul", null, phoneCan.map((x) => e("li", { key: x.t }, e("strong", null, x.t), " — ", x.d)))
        )
      ),

      e(
        "p",
        { className: "hint device-sync-note" },
        "同步机制：任务状态 / 会话草稿 / 文件列表经 SyncEngine 版本号 + 增量广播，多端同一 trace_id；离线排队、上线分发。"
      )
    )
  );
}
