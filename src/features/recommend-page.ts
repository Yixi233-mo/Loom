/**
 * 推荐 — 外部 Agent 应用卡片（毛玻璃）· 启动 / 展开详情（官网 + MCP）
 */

import * as React from "react";
import { PageShell } from "./page-states.ts";
import { UI } from "../components/index.ts";

const e = React.createElement;

export interface AgentApp {
  id: string;
  name: string;
  vendor: string;
  tagline: string;
  /** 本机可执行路径或命令；空则不可启动 */
  exePath?: string;
  /** 备用启动命令（如 npx / 相对路径） */
  command?: string;
  website: string;
  mcpUrl?: string;
  mcpHint?: string;
  tags: string[];
  /** 是否已检测到本机安装（由上层探测结果覆盖） */
  installed?: boolean;
}

export const RECOMMENDED_AGENTS: AgentApp[] = [
  {
    id: "claude_code",
    name: "Claude Code",
    vendor: "Anthropic",
    tagline: "终端编码 Agent，改代码 / Review / Shell，MCP 工具链成熟",
    exePath: "claude",
    command: "claude",
    website: "https://claude.com/claude-code",
    mcpUrl: "http://127.0.0.1:3001/mcp",
    mcpHint: "以本机 Claude Code 的 MCP 配置端口为准",
    tags: ["编码", "CLI", "MCP", "热门"],
  },
  {
    id: "chatgpt",
    name: "ChatGPT",
    vendor: "OpenAI",
    tagline: "全球使用最广的对话/Agent 入口，可配 GPTs 与插件",
    website: "https://chatgpt.com/",
    mcpUrl: "",
    mcpHint: "网页端；开发者可用 OpenAI API 作 LLM 后端",
    tags: ["对话", "热门"],
  },
  {
    id: "work_buddy",
    name: "Work Buddy",
    vendor: "Tencent / CodeBuddy",
    tagline: "桌面 AI 助手：邮件 / 云文档 / 自动化工具集",
    exePath: "D:\Workbuddy\WorkBuddy.exe",
    command: "D:\Workbuddy\WorkBuddy.exe",
    website: "https://www.workbuddy.cn/docs/workbuddy/Overview",
    mcpUrl: "http://127.0.0.1:54916/mcp",
    mcpHint: "本机 connector-proxy；Bearer 见 LOOM_WORK_BUDDY_TOKEN",
    tags: ["桌面", "MCP", "办公", "热门"],
  },
  {
    id: "qwen",
    name: "通义千问 Qwen",
    vendor: "阿里云",
    tagline: "国内高使用率大模型 / App / API，中文与工具调用强",
    website: "https://tongyi.aliyun.com/qianwen/",
    mcpUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1",
    mcpHint: "OpenAI 兼容 API：设置 · 自定义 LLM 填 DashScope 兼容地址 + Key",
    tags: ["LLM", "中文", "热门"],
  },
  {
    id: "trae",
    name: "Trea / Trae",
    vendor: "ByteDance",
    tagline: "AI IDE（国内常用），内置 Builder / Chat 模式",
    exePath: "trae",
    command: "trae",
    website: "https://www.trae.cn/",
    mcpUrl: "",
    mcpHint: "在 Trea 设置 → MCP 添加外部 MCP Server",
    tags: ["IDE", "编码", "热门"],
  },
  {
    id: "pi",
    name: "Pi",
    vendor: "Inflection",
    tagline: "对话型个人 AI，语气自然，适合日常问答与陪伴",
    website: "https://pi.ai/",
    mcpUrl: "",
    mcpHint: "以网页/移动 App 为主，无固定本地 MCP 端口",
    tags: ["对话", "个人"],
  },
  {
    id: "deepseek",
    name: "DeepSeek",
    vendor: "DeepSeek",
    tagline: "高性价比推理模型，适合做 LLM 后端 / 编程 Harness",
    website: "https://platform.deepseek.com/",
    mcpUrl: "https://api.deepseek.com/v1",
    mcpHint: "OpenAI 兼容 API：设置 · 自定义 LLM 推荐首选之一",
    tags: ["LLM", "推理", "热门"],
  },
  {
    id: "codex",
    name: "Codex CLI",
    vendor: "OpenAI",
    tagline: "OpenAI 终端编码 Agent，可挂 MCP 工具",
    exePath: "codex",
    command: "codex",
    website: "https://developers.openai.com/codex/cli",
    mcpUrl: "http://127.0.0.1:3002/mcp",
    mcpHint: "MCP 端口以本机 Codex / MCP Server 配置为准",
    tags: ["编码", "CLI", "MCP"],
  },
  {
    id: "cursor",
    name: "Cursor",
    vendor: "Anysphere",
    tagline: "高使用率 AI IDE，Composer / Agent 模式",
    exePath: "cursor",
    command: "cursor",
    website: "https://cursor.com/",
    mcpUrl: "",
    mcpHint: "Cursor Settings → MCP 可添加 Loom 或外部 MCP",
    tags: ["IDE", "编码", "热门"],
  },
  {
    id: "windsurf",
    name: "Windsurf",
    vendor: "Cognition",
    tagline: "AI IDE（原 Codeium），Cascade 流式 Agent",
    exePath: "windsurf",
    command: "windsurf",
    website: "https://windsurf.com/",
    mcpUrl: "",
    mcpHint: "在 Windsurf 插件/MCP 设置中添加 Server",
    tags: ["IDE", "编码"],
  },
  {
    id: "gemini_cli",
    name: "Gemini CLI",
    vendor: "Google",
    tagline: "终端 Gemini Agent，检索与多模态任务好用",
    exePath: "gemini",
    command: "gemini",
    website: "https://github.com/google-gemini/gemini-cli",
    mcpUrl: "",
    mcpHint: "通过 MCP 配置文件接入工具；无固定本地端口",
    tags: ["编码", "CLI", "多模态"],
  },
  {
    id: "kimi",
    name: "Kimi",
    vendor: "Moonshot AI",
    tagline: "长上下文对话与文档问答，国内常用",
    website: "https://www.kimi.com/",
    mcpUrl: "https://api.moonshot.cn/v1",
    mcpHint: "OpenAI 兼容 API：设置 · 自定义 LLM 可接",
    tags: ["对话", "LLM", "热门"],
  },
  {
    id: "doubao",
    name: "豆包",
    vendor: "字节跳动",
    tagline: "国内高 DAU 对话 App / 豆包编程等场景",
    website: "https://www.doubao.com/",
    mcpUrl: "",
    mcpHint: "以 App/网页为主；火山方舟提供 API（可作 LLM）",
    tags: ["对话", "热门"],
  },
  {
    id: "copilot",
    name: "GitHub Copilot",
    vendor: "GitHub / Microsoft",
    tagline: "编码补全与 Chat，IDE 插件覆盖率高",
    exePath: "copilot",
    command: "copilot",
    website: "https://github.com/features/copilot",
    mcpUrl: "",
    mcpHint: "IDE 插件；可通过 Copilot Chat 配置外部工具",
    tags: ["编码", "补全", "热门"],
  },
  {
    id: "cline",
    name: "Cline",
    vendor: "Cline",
    tagline: "VS Code 编码 Agent，支持 MCP 工具与自主改文件",
    exePath: "code",
    command: "code",
    website: "https://cline.bot/",
    mcpUrl: "",
    mcpHint: "VS Code 扩展设置 → MCP Servers 添加",
    tags: ["编码", "VS Code", "MCP"],
  },
  {
    id: "aider",
    name: "Aider",
    vendor: "Aider AI",
    tagline: "开源终端结对编程，Git 集成好",
    exePath: "aider",
    command: "aider",
    website: "https://aider.chat/",
    mcpUrl: "",
    mcpHint: "CLI；可配合本地 MCP/工具脚本扩展",
    tags: ["编码", "CLI", "开源"],
  },
  {
    id: "grok",
    name: "Grok",
    vendor: "xAI",
    tagline: "实时信息与对话，X 生态集成",
    website: "https://grok.com/",
    mcpUrl: "",
    mcpHint: "以网页/App 为主",
    tags: ["对话", "实时"],
  },
  {
    id: "ernie",
    name: "文心一言",
    vendor: "百度",
    tagline: "国内对话与办公场景，文心快码等衍生",
    website: "https://yiyan.baidu.com/",
    mcpUrl: "",
    mcpHint: "千帆平台提供 OpenAI 风格兼容 API 时可接 LLM",
    tags: ["对话", "中文"],
  },
  {
    id: "zhipu",
    name: "智谱 / ChatGLM",
    vendor: "智谱 AI",
    tagline: "GLM 系列模型与开放平台，编程与对话",
    website: "https://chatglm.cn/",
    mcpUrl: "https://open.bigmodel.cn/api/paas/v4",
    mcpHint: "OpenAI 兼容 API：设置 · 自定义 LLM 可接",
    tags: ["LLM", "中文"],
  },
  {
    id: "manus",
    name: "Manus",
    vendor: "Monica / Butterfly Effect",
    tagline: "通用 Agent 任务执行，偏自动化流水线",
    website: "https://manus.im/",
    mcpUrl: "",
    mcpHint: "云端 Agent 产品，无本地 MCP 端口",
    tags: ["Agent", "自动化"],
  },
];



export function RecommendPage(props: {
  agents?: AgentApp[];
  onLaunch?: (app: AgentApp) => void;
  launchState?: Record<string, "idle" | "ok" | "missing" | "error">;
}) {
  const [expanded, setExpanded] = React.useState<Record<string, boolean>>({});
  const list = props.agents ?? RECOMMENDED_AGENTS;
  const state = props.launchState ?? {};

  return e(
    PageShell,
    {
      route: "recommend",
      title: "推荐",
      subtitle: "外部 Agent 应用 · 点击启动（未安装则无效）· 展开看官网与 MCP",
    },
    e(
      "div",
      {
        className: "recommend-grid",
        "data-page": "recommend",
        "data-view": "recommend-agents",
      },
      list.map((app) => {
        const open = !!expanded[app.id];
        const st = state[app.id] ?? (app.installed ? "idle" : app.installed === false ? "missing" : "idle");
        return e(
          "article",
          {
            key: app.id,
            className: "agent-card glass" + (open ? " is-open" : ""),
            "data-agent-id": app.id,
            "data-expanded": open ? "true" : "false",
            "data-launch": st,
          },
          e(
            "header",
            { className: "agent-card-head" },
            e(
              "div",
              null,
              e("h3", null, app.name),
              e("p", { className: "agent-vendor" }, app.vendor)
            ),
            e(
              "span",
              {
                className:
                  "badge " +
                  (st === "ok" ? "ok" : st === "missing" || st === "error" ? "todo" : ""),
              },
              st === "ok" ? "已启动" : st === "missing" ? "未安装" : st === "error" ? "启动失败" : "可启动"
            )
          ),
          e("p", { className: "agent-tagline" }, app.tagline),
          e(
            "div",
            { className: "agent-tags" },
            app.tags.map((t) => e("code", { key: t }, t))
          ),
          e(
            "div",
            { className: "agent-actions" },
            e(
              "button",
              {
                type: "button",
                className: UI.button + " " + UI.buttonPrimary,
                "data-action": "launch-agent",
                "data-agent-id": app.id,
                onClick: () => props.onLaunch?.(app),
              },
              "启动应用"
            ),
            e(
              "button",
              {
                type: "button",
                className: UI.button + " " + UI.buttonGhost,
                "data-action": "toggle-agent-detail",
                "aria-expanded": open ? "true" : "false",
                onClick: () =>
                  setExpanded((s) => ({ ...s, [app.id]: !s[app.id] })),
              },
              open ? "收起详情" : "展开详情"
            )
          ),
          open
            ? e(
                "div",
                { className: "agent-detail", "data-view": "agent-detail" },
                e(
                  "div",
                  { className: "agent-row" },
                  e("b", null, "官网"),
                  e(
                    "a",
                    {
                      href: app.website,
                      target: "_blank",
                      rel: "noreferrer",
                      "data-action": "open-website",
                    },
                    app.website
                  )
                ),
                e(
                  "div",
                  { className: "agent-row" },
                  e("b", null, "MCP"),
                  app.mcpUrl
                    ? e("code", { "data-mcp-url": app.mcpUrl }, app.mcpUrl)
                    : e("span", { className: "hint" }, "无固定 MCP 端点")
                ),
                app.mcpHint
                  ? e("p", { className: "hint agent-mcp-hint" }, app.mcpHint)
                  : null,
                e(
                  "div",
                  { className: "agent-row" },
                  e("b", null, "本机路径"),
                  e("code", null, app.exePath || app.command || "—")
                )
              )
            : null
        );
      })
    )
  );
}
