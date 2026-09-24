/**
 * 使用说明 SOP — 项目功能与用法（应用内「使用说明」页）
 */

import * as React from "react";
import { PageShell } from "./page-states.ts";

const e = React.createElement;

export interface HelpSection {
  id: string;
  title: string;
  summary: string;
  steps: string[];
  tips?: string[];
}

export const HELP_SECTIONS: HelpSection[] = [
  {
    id: "overview",
    title: "项目是什么",
    summary: "Loom（织巢）= 跨端 Agent 工作台：把 Win / 平板 / 手机编织成一台电脑，把 Claude Code、Work Buddy 等 AI 编织成一个团队。",
    steps: [
      "一句话：用户说话 → 意图识别 → 选执行端 → 调工具或连外部 AI → 结果同步多端",
      "架构：本地 Hub（路由/状态） + Device Mesh（跨端） + DSL（YAML 声明扩展）",
      "原则：改 YAML 即扩展，尽量不改主程序",
    ],
    tips: ["开发中（0.1.0），接口可能调整；密钥勿提交仓库"],
  },
  {
    id: "startup",
    title: "快速启动（SOP）",
    summary: "三步跑通：起 Hub → 开前端 →（可选）起演示 MCP。",
    steps: [
      "1. 安装依赖：npm install",
      "2. 启动 Hub：npm run start:hub（端口 8765）",
      "3. 启动前端：npm run dev（端口 5173）→ 浏览器打开 http://localhost:5173/",
      "一键：npm run start（Hub + 前端同时拉起）",
      "可选演示 MCP：npm run mcp:demo 或 python scripts/mock_mcp_server.py（3900）",
      "离线预览 UI：npm run build:single → 打开 app.html",
    ],
    tips: ["自检：npm run test（Py + JS + Rust）；npm run lint"],
  },
  {
    id: "nav",
    title: "界面导航怎么用",
    summary: "左侧栏切换模块；右侧只显示当前页。手机为底部 Tab。",
    steps: [
      "对话 — 与 AI 协作，默认铺满窗口，消息区可滑动",
      "任务 — 查看排队/执行中/完成，看结果卡片（tokens / 延迟 / 降级）",
      "跨端 — 设备在线状态、同步摘要、手机/平板能做什么、下发测试任务",
      "设置 — 自定义 LLM：填 API、拉模型、选用配置、测试对话",
      "MCP — 外接 Claude Code / Work Buddy：检测连接、试调用工具",
      "使用说明 — 本页，功能与用法 SOP",
    ],
  },
  {
    id: "chat",
    title: "对话工作台",
    summary: "与 Loom 对话；可指定模型；一句话触发跨端任务。",
    steps: [
      "在「设置」里先保存并选用一条 LLM 配置（推荐 DeepSeek 等 OpenAI 兼容 API）",
      "左侧「对话」→ 输入框输入需求 → Enter 或点「发送」",
      "点「收起 / 放大」切换小窗；消息多时在框内上下滑动",
      "示例：「帮我把这份 PDF 转成 Markdown 并总结」→ 会进入任务流",
    ],
    tips: ["未配置模型时会本地回声，仅用于测 UI"],
  },
  {
    id: "tasks",
    title: "任务中心",
    summary: "跨端编排的结果都在这里；可按状态筛选。",
    steps: [
      "顶部筛选：全部 / 待处理 / 执行中 / 已完成 / 失败",
      "结果卡片显示：workflow、trace_id、设备、tokens_used、latency_ms、degradation_level",
      "「刷新」拉最新状态；「跨端」页可下发测试任务后回到本页看流转",
    ],
  },
  {
    id: "llm",
    title: "自定义 LLM（设置）",
    summary: "OpenAI 兼容 API；Key 加密；可选用多条配置。",
    steps: [
      "1. 填名称（如 DeepSeek）、Base URL（https://api.deepseek.com/v1）、API Key → 保存配置",
      "2. 点「拉取模型」→ 从服务商真实拉取列表",
      "3. 下拉选择具体模型；点模型 chip 也可选",
      "4. 顶部「当前模型配置」选用要使用的那条 → 对话优先用它",
      "5. 「测试对话」验证连通",
    ],
    tips: ["Base URL 会自动补 /v1；缺 Key 时先重新保存再拉模型"],
  },
  {
    id: "mcp",
    title: "MCP 外接服务",
    summary: "让 Loom 调用 Claude Code、Work Buddy 等外部工具（JSON-RPC）。",
    steps: [
      "MCP 一般只在 PC/Hub 配置一次；手机看结果即可",
      "填协议地址（如 Work Buddy：http://127.0.0.1:54916/mcp）→ 检测连接",
      "看到服务名与工具列表即连通；点「试调用工具」或点工具名验证 tools/call",
      "无外部服务：npm run mcp:demo → http://127.0.0.1:3900/mcp",
      "目录里有「下载 Work Buddy」推荐与一键填入地址",
    ],
    tips: [
      "链路：对话 → 意图识别 → 选端 → 工具调用 / 连 Claude Code · Work Buddy",
      "鉴权：Work Buddy 需 Bearer token（环境变量 LOOM_WORK_BUDDY_TOKEN）",
    ],
  },
  {
    id: "cross",
    title: "跨端协同（手机 / 平板）",
    summary: "MCP 在 PC；手机负责查看与分发。信息与任务经 Sync 实时同步。",
    steps: [
      "PC/Hub：MCP、LLM Key、DSL、Shell/重计算",
      "手机/平板：任务列表、任务分发、对话下任务、文件上传、通知与技能树",
      "同步：任务状态/会话/文件列表版本号 + 增量广播；离线排队、上线分发",
      "在「跨端」页看设备在线、同步版本、下发测试任务",
    ],
  },
  {
    id: "dsl",
    title: "DSL 扩展（进阶）",
    summary: "YAML 声明 Workflow / Plugin / Agent / Trigger，热加载。",
    steps: [
      "示例目录：plugins/example/（notes 插件 + 4 场景 workflow）",
      "改 YAML 保存 → Hub 约 2s 热生效，不用重启",
      "保存前会做 Schema 校验，非法 DSL 不会落盘",
      "对话式生成 DSL：说出需求 → 生成 → diff 确认后才写入",
    ],
  },
  {
    id: "sop",
    title: "日常 SOP 速查",
    summary: "从零到跑通一条「对话 → 任务 → 跨端」的最短路径。",
    steps: [
      "Day 0 装好：npm install → npm run start",
      "Step 1 设置 LLM：保存配置 → 拉取模型 → 选用 → 测试对话",
      "Step 2 （可选）MCP：连接 Work Buddy / 演示 MCP → 检测连接",
      "Step 3 对话下发任务 → 任务中心看结果卡片",
      "Step 4 手机打开同一 Hub 地址 → 跨端查看/分发",
      "扩展：改 plugins/ 下 YAML 热加载新能力",
    ],
    tips: ["出问题先看 Hub 日志（trace_id）与 任务 → 错误卡片"],
  },
];

export function HelpPage() {
  return e(
    PageShell,
    {
      route: "help",
      title: "使用说明",
      subtitle: "Loom 功能介绍与操作 SOP — 从启动到跨端协作",
    },
    e(
      "div",
      {
        className: "help-page",
        "data-page": "help",
        "data-view": "help-sop",
      },
      HELP_SECTIONS.map((sec) =>
        e(
          "section",
          {
            key: sec.id,
            className: "help-card glass",
            "data-help-id": sec.id,
          },
          e("h3", null, sec.title),
          e("p", { className: "help-summary" }, sec.summary),
          e(
            "ol",
            { className: "help-steps" },
            sec.steps.map((s, i) => e("li", { key: i }, s))
          ),
          sec.tips && sec.tips.length
            ? e(
                "ul",
                { className: "help-tips" },
                sec.tips.map((t, i) => e("li", { key: i }, t))
              )
            : null
        )
      ),
      e(
        "p",
        { className: "hint help-foot" },
        "完整文档见仓库 目录/使用说明SOP.md · 目录/MCP_工具调用说明.md · 目录/项目介绍.md"
      )
    )
  );
}
