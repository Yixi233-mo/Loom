/**
 * Agent 状态页 — 谁能干活、干得好不好（中文说明）
 */

import * as React from "react";
import type { AgentState } from "../contracts/index.ts";
import { PageShell, EmptyState } from "./page-states.ts";
import { UI } from "../components/index.ts";

const e = React.createElement;

const STATUS_TXT: Record<string, string> = {
  online: "在线可用",
  busy: "忙碌中",
  degraded: "降级备用",
  offline: "离线",
};

const AGENT_META: Record<string, { title: string; desc: string }> = {
  builtin_rag: {
    title: "知识检索（RAG）",
    desc: "本地/内置资料问答。对话里问「查资料、检索、知识库」时会派它。",
  },
  cloud_api: {
    title: "云端大模型",
    desc: "主力写代码、总结、生成任务。失败时会自动降到本地模型或规则。",
  },
  claude_code: {
    title: "Claude Code",
    desc: "外部编码助手（需本机/MCP 已连接）。",
  },
  work_buddy: {
    title: "Work Buddy",
    desc: "腾讯桌面助手：邮件/云服务等工具（已连 connector-proxy）。",
  },
  ollama: {
    title: "本地模型（Ollama）",
    desc: "断网时的备用生成能力。",
  },
};

const CAP_TXT: Record<string, string> = {
  "rag.query": "资料检索",
  "code.gen": "写代码",
  "file.edit": "改文件",
  "shell.exec": "跑命令",
  "*": "通用",
  "buddy.task": "办公任务",
  "buddy.chat": "对话协助",
  "buddy.assist": "辅助执行",
};

const DEG_TXT: Record<number, string> = {
  0: "全功能",
  1: "备用通道",
  2: "规则兜底",
};

function metaFor(name: string) {
  return (
    AGENT_META[name] ?? {
      title: name,
      desc: "联邦中的一个助手节点。",
    }
  );
}

export function AgentsPage(props: {
  agents: AgentState[];
  onTest?: (agentName: string) => void;
  onRefresh?: () => void;
}) {
  const online = props.agents.filter((a) => a.status === "online").length;

  return e(
    PageShell,
    {
      route: "agents",
      title: "Agent 状态",
      subtitle: "看看谁能帮你干活 · 现在健不健康",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "agents-refresh",
          onClick: () => props.onRefresh?.(),
        },
        "刷新"
      ),
    },
    e(
      "div",
      { className: "agents-page", "data-page": "agents", "data-view": "agents" },

      e(
        "div",
        { className: "agent-help glass", "data-view": "agent-help" },
        e("h3", null, "这页是干什么的？"),
        e("p", null, "Loom 会把你的活派给不同的「助手」去干。这里列出所有助手，告诉你："),
        e(
          "ul",
          null,
          e("li", null, e("b", null, "状态"), " — 现在能不能干活（在线 / 忙碌 / 降级 / 离线）"),
          e("li", null, e("b", null, "能干什么"), " — 比如写代码、查资料、跑命令"),
          e("li", null, e("b", null, "降级档位"), " — 主力挂了以后退到哪一档"),
          e("li", null, e("b", null, "延迟 / tokens"), " — 上次调用快不快、费了多少")
        ),
        e(
          "p",
          { className: "hint" },
          `当前 ${online} 个在线 / 共 ${props.agents.length} 个。对话里点「测试调用」验证链路是否通。`
        )
      ),

      props.agents.length === 0
        ? e(EmptyState, {
            title: "还没有助手",
            hint: "在「设置」配好模型，或在「MCP」连上 Work Buddy / Claude Code 后，这里会出现成员。",
          })
        : e(
            "ul",
            { className: "agent-list", "data-agent-count": String(props.agents.length) },
            props.agents.map((a) => {
              const meta = metaFor(a.agentName);
              const deg = DEG_TXT[a.degradationLevel] ?? `档位 ${a.degradationLevel}`;
              return e(
                "li",
                {
                  key: a.agentName,
                  className: "agent-row glass",
                  "data-agent": a.agentName,
                  "data-status": a.status,
                },
                e(
                  "div",
                  { className: "agent-row-head" },
                  e(
                    "div",
                    null,
                    e("strong", { className: "agent-title" }, meta.title),
                    e("p", { className: "hint agent-desc" }, meta.desc)
                  ),
                  e(
                    "span",
                    {
                      className:
                        "badge " +
                        (a.status === "online" || a.status === "busy"
                          ? "ok"
                          : a.status === "degraded"
                            ? "todo"
                            : "todo"),
                    },
                    STATUS_TXT[a.status] ?? a.status
                  )
                ),
                e(
                  "div",
                  { className: "plugin-tools" },
                  (a.capabilities || []).map((c) =>
                    e(
                      "code",
                      { key: c, title: c },
                      CAP_TXT[c] ?? c
                    )
                  )
                ),
                e(
                  "div",
                  { className: "agent-row-meta" },
                  `质量：${deg}` +
                    (a.lastLatencyMs != null ? ` · 速度：${a.lastLatencyMs} 毫秒` : "") +
                    (a.lastTokensUsed != null ? ` · 上次消耗：${a.lastTokensUsed} tokens` : "")
                ),
                e(
                  "button",
                  {
                    type: "button",
                    className: UI.button + " " + UI.buttonPrimary,
                    "data-action": "test-agent",
                    disabled: a.status === "offline",
                    onClick: () => props.onTest?.(a.agentName),
                  },
                  "发一条测试消息"
                )
              );
            })
          )
    )
  );
}
