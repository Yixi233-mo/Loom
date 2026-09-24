import * as React from "react";
import {
  ChatWorkbench,
  TaskCenter,
  SettingsPage,
  McpWorkspace,
  DeviceHubPage,
  HelpPage,
  PromptsPage,
  FilesPage,
  AgentsPage,
  RecommendPage,
  type AgentApp,
} from "./features/index.ts";
import { useHashRoute, navigate, type AppRoute } from "./hooks/index.ts";
import { createAppStores, createTask, createAgent } from "./state/index.ts";
import { promptStore, type PromptItem } from "./stores/prompt-store.ts";
import { createServiceLayer } from "./services/index.ts";
import { ModelChatClient } from "./services/model-chat.ts";
import { probeMcp, fetchProviderModels } from "./services/llm-api.ts";
import { fetchMcpCatalog, callMcpTool } from "./services/mcp-tools.ts";
import { createPlatformLayer } from "./platform/index.ts";
import type { TaskStatus } from "./contracts/index.ts";

const e = React.createElement;

const stores = createAppStores("sess-demo-1");
const services = createServiceLayer({ baseUrl: "" });

stores.session.appendMessage({
  role: "user",
  content: "帮我把这份 PDF 转成 Markdown 并总结",
});
stores.session.appendMessage({
  role: "assistant",
  content: "已路由到 PC 执行，结果见右侧任务面板。",
  taskId: "t1",
});

stores.tasks.upsert({
  ...createTask({
    taskId: "t1",
    workflowName: "mobile_to_pc_pdf",
    traceId: "tr-demo-1",
    device: "pc",
    assignedTo: "hub-pc-1",
    status: "done",
  }),
  result: {
    summary: "PDF 已转 Markdown 并生成 3 条要点",
    tokensUsed: 860,
    latencyMs: 420,
    degradationLevel: 0,
  },
});

stores.tasks.upsert(
  createTask({
    taskId: "t2",
    workflowName: "daily_report",
    traceId: "tr-demo-2",
    device: "pc",
    status: "running",
  })
);

stores.agents.upsert(
  createAgent({
    agentName: "builtin_rag",
    status: "online",
    capabilities: ["rag.query"],
    degradationLevel: 0,
  })
);
stores.agents.upsert(
  createAgent({
    agentName: "cloud_api",
    status: "degraded",
    degradationLevel: 1,
    lastLatencyMs: 220,
    lastTokensUsed: 40,
  })
);

export default function App() {
  const [tick, setTick] = React.useState(0);
  const [filter, setFilter] = React.useState<TaskStatus | "all">("all");
  const [platform, setPlatform] = React.useState(() =>
    createPlatformLayer(undefined, undefined, null)
  );
  const [chatSize, setChatSize] = React.useState<"default" | "expanded">("expanded");
  const [chatBusy, setChatBusy] = React.useState(false);
  const modelChat = React.useMemo(() => new ModelChatClient(), []);
  const [llmError, setLlmError] = React.useState("");
  const [llmTestResult, setLlmTestResult] = React.useState("");
  const [mcpUrl, setMcpUrl] = React.useState("http://127.0.0.1:54916/mcp");
  const [mcpToken, setMcpToken] = React.useState("k46BofoxqxEHe9K1uWpxZfvvVB1LwXdp-IWzi_abM6c");
  const [mcpResult, setMcpResult] = React.useState<any>(null);
  const [mcpBusy, setMcpBusy] = React.useState(false);
  const [mcpCatalog, setMcpCatalog] = React.useState<any[]>([]);
  const [mcpToolResult, setMcpToolResult] = React.useState<string | null>(null);
  const [mcpToolBusy, setMcpToolBusy] = React.useState(false);
  const [llmDraft, setLlmDraft] = React.useState<{
    name: string;
    baseUrl: string;
    apiKey: string;
    providerId?: string;
  }>({ name: '', baseUrl: '', apiKey: '' });
  const [llmProviders, setLlmProviders] = React.useState<Array<any>>([]);
  const [activeProviderId, setActiveProviderId] = React.useState<string | null>(null);
  const [launchState, setLaunchState] = React.useState<Record<string, "idle" | "ok" | "missing" | "error">>({});
  const [promptItems, setPromptItems] = React.useState<PromptItem[]>(() => promptStore.list());
  const [activePrompt, setActivePrompt] = React.useState<PromptItem | null>(null);
  const [settingsTab, setSettingsTab] = React.useState<"llm" | "mcp">("llm");
  const [pageLoading, setPageLoading] = React.useState(false);
  const [pageError, setPageError] = React.useState<string | null>(null);
  const route = useHashRoute();
  const activeRoute: AppRoute = route.route;

  React.useEffect(() => {
    const offs = [
      stores.session.subscribe(() => setTick((t) => t + 1)),
      stores.tasks.subscribe(() => setTick((t) => t + 1)),
      stores.agents.subscribe(() => setTick((t) => t + 1)),
    ];
    const onResize = () => {
      setPlatform((prev) => {
        const next = createPlatformLayer(
          window.innerWidth,
          window.innerHeight,
          prev.tauri.impl ?? null
        );
        return next;
      });
    };
    window.addEventListener("resize", onResize);
    onResize();
    const offPrompt = promptStore.subscribe(() => setPromptItems(promptStore.list()));
    void fetchMcpCatalog(services.rest).then((c: { items: any[] }) => setMcpCatalog(c.items || [])).catch(() => {});
    return () => {
      offs.forEach((off) => off());
      offPrompt();
      window.removeEventListener("resize", onResize);
    };
  }, []);

  void tick;

  const session = stores.session.get();
  const tasks = stores.tasks.list();
  const agents = stores.agents.list();

  return e(
    "div",
    {
      className: `app-shell layout-${platform.layout}`,
      "data-app": "loom-shell",
      "data-device": platform.device.deviceType,
      "data-layout": platform.layout,
    },

    e(
      "aside",
      { className: "app-side", "data-view": "sidebar" },
      e(
        "div",
        { className: "side-brand" },
        e("div", { className: "mark" }, "织"),
        e(
          "div",
          null,
          e("strong", null, "Loom"),
          e("div", { className: "side-label" }, "跨端 Agent 工作台")
        )
      ),
      e("div", { className: "side-label" }, "导航"),
      e(
        "nav",
        { className: "side-nav", "aria-label": "侧栏导航", "data-view": "side-nav" },
        e("div", { className: "side-label" }, "工作区"),
        (
          [
            ["chat", "对话"],
            ["prompts", "提示词"],
            ["tasks", "任务"],
            ["files", "文件"],
            ["agents", "Agent"],
          ] as Array<[AppRoute, string]>
        ).map(([id, label]) =>
          e(
            "button",
            {
              key: id,
              type: "button",
              className: "nav-link" + (activeRoute === id ? " is-active" : ""),
              "data-route": id,
              onClick: () => navigate(id),
            },
            label
          )
        ),
        e("div", { className: "side-label" }, "设置 · 跨端"),
        (
          [
            ["settings", "设置"],
            ["devices", "跨端"],
          ] as Array<[AppRoute, string]>
        ).map(([id, label]) =>
          e(
            "button",
            {
              key: id,
              type: "button",
              className: "nav-link" + (activeRoute === id ? " is-active" : ""),
              "data-route": id,
              onClick: () => navigate(id),
            },
            label
          )
        ),
        e("div", { className: "side-label" }, "MCP · 推荐"),
        (
          [
            ["mcp", "MCP"],
            ["recommend", "推荐"],
          ] as Array<[AppRoute, string]>
        ).map(([id, label]) =>
          e(
            "button",
            {
              key: id,
              type: "button",
              className: "nav-link" + (activeRoute === id ? " is-active" : ""),
              "data-route": id,
              onClick: () => navigate(id),
            },
            label
          )
        ),
        e("div", { className: "side-label" }, "帮助"),
        e(
          "button",
          {
            type: "button",
            className: "nav-link" + (activeRoute === "help" ? " is-active" : ""),
            "data-route": "help",
            onClick: () => navigate("help"),
          },
          "使用说明"
        )
      ),
      e(
        "div",
        { className: "side-foot" },
        platform.device.deviceType + " · " + platform.layout
      )
    ),
    e(
      "header",
      { className: "app-header" },
      e(
        "div",
        null,
        e("h1", { className: "app-title" }, "Loom · 织巢"),
        e(
          "p",
          { className: "app-subtitle" },
          "跨端 Agent 工作台 — 对话 · 任务 · 文件 · Agent"
        )
      ),
      e(
        "nav",
        { className: "app-nav", "data-view": "nav", "aria-label": "主导航" },
        (
          [
            ["chat", "对话"],
            ["tasks", "任务"],
            ["settings", "设置"],
            ["devices", "跨端"],
            ["help", "使用说明"],
            ["recommend", "推荐"],
            ["mcp", "MCP"],
          ] as Array<[AppRoute, string]>
        ).map(([id, label]) =>
          e(
            "button",
            {
              key: id,
              type: "button",
              className:
                "nav-link" + (activeRoute === id ? " is-active" : ""),
              "data-route": id,
              "aria-current": activeRoute === id ? "page" : undefined,
              onClick: () => navigate(id),
            },
            label
          )
        )
      ),
      e(
        "button",
        {
          type: "button",
          className: "task-progress-pill",
          "data-view": "task-progress-pill",
          "data-action": "goto-tasks",
          onClick: () => navigate("tasks"),
          title: "打开任务中心",
        },
        e("span", { className: "pill-label" }, "任务"),
        e(
          "span",
          { className: "pill-count" },
          String(tasks.filter((x) => x.status === "done").length) +
            "/" +
            String(tasks.length)
        ),
        e("i", {
          className: "pill-bar",
          style: {
            width:
              String(
                tasks.length
                  ? Math.round(
                      (tasks.filter((x) => x.status === "done").length /
                        tasks.length) *
                        100
                    )
                  : 0
              ) + "%",
          },
        })
      ),
      e(
        "span",
        { className: "app-badge", "data-platform-badge": "true" },
        `${platform.device.deviceType} · ${platform.layout}${
          platform.tauri.available ? " · Tauri" : " · Web"
        }`
      )
    ),

    e(
      "div",
      { className: "app-main", "data-view": "main" },
    /* FE.3 核心页面：hash 路由 */
    activeRoute === "chat"
      ? e(ChatWorkbench, {
          session,
          loading: pageLoading,
          error: pageError,
          busy: chatBusy,
          modelLabel: llmProviders.find((p) => p.defaultModel)?.defaultModel,
          chatSize,
          prompts: promptItems,
          activePromptId: activePrompt?.id ?? null,
          activePromptTitle: activePrompt?.title,
          onPickPrompt: (p: { id: string; title: string; body: string; updatedAt?: number }) => {
            setActivePrompt(p);
            stores.session.setDraft(p.body + (stores.session.get().draft ? "\n" + stores.session.get().draft : ""));
          },
          onClearPrompt: () => setActivePrompt(null),
          onManagePrompts: () => navigate("prompts"),
          onToggleSize: () =>
            setChatSize((s) => (s === "default" ? "expanded" : "default")),
          onRetry: () => {
            setPageError(null);
            setPageLoading(true);
            setTimeout(() => setPageLoading(false), 200);
          },
          onDraft: (text: string) => stores.session.setDraft(text),
          onSend: (text: string) => {
            stores.session.appendMessage({ role: "user", content: text });
            stores.session.setDraft("");
            stores.session.setStatus("streaming");
            setChatBusy(true);
            const active = llmProviders.find((p) => p.providerId === activeProviderId && p.defaultModel && p.baseUrl) || llmProviders.find((p) => p.defaultModel && p.baseUrl);
            void (async () => {
              try {
                if (active) {
                  const reply = await modelChat.complete(
                    {
                      providerId: active.providerId,
                      baseUrl: active.baseUrl,
                      apiKey:
                        (active as any).apiKeyPlain || (active as any)._apiKey || "",
                      model: active.defaultModel,
                    },
                    stores.session.get().messages
                  );
                  stores.session.appendMessage({ role: "assistant", content: reply });
                } else {
                  stores.session.appendMessage({
                    role: "assistant",
                    content: "（未配置模型，本地回声）" + text.slice(0, 40),
                  });
                }
              } catch (err) {
                const msg = err instanceof Error ? err.message : String(err);
                stores.session.appendMessage({
                  role: "assistant",
                  content: msg.startsWith("模型对话失败") || msg.startsWith("请先")
                    ? msg
                    : "模型对话失败：" + msg,
                });
              } finally {
                stores.session.setStatus("idle");
                setChatBusy(false);
              }
            })();
          },
        })
      : activeRoute === "prompts"
        ? e(PromptsPage, {
            onUseInChat: (p: PromptItem) => {
              setActivePrompt(p);
              stores.session.setDraft(p.body);
              navigate("chat");
            },
          })
      : activeRoute === "files"
        ? e(FilesPage, {
            services,
            
          })
      : activeRoute === "agents"
        ? e(AgentsPage, {
            agents,
            onRefresh: () => setTick((x) => x + 1),
            onTest: (name: string) => {
              stores.agents.recordCall(name, { lastLatencyMs: 42, lastTokensUsed: 10 });
              stores.agents.setStatus(name, "busy");
              setTimeout(() => stores.agents.setStatus(name, "online"), 400);
            },
          })
      : activeRoute === "tasks"
        ? e(TaskCenter, {
            tasks,
            filter,
            loading: pageLoading,
            error: pageError,
            onFilter: (f: TaskStatus | "all") => setFilter(f),
            onRetry: () => {
              setPageError(null);
              setPageLoading(true);
              setTimeout(() => setPageLoading(false), 200);
            },
            onRefresh: () => {
              setPageLoading(true);
              setPageError(null);
              setTimeout(() => setPageLoading(false), 300);
            },
          })
        : activeRoute === "devices"
          ? e(DeviceHubPage, {
              layout: platform.layout,
              hubOnline: true,
              pendingTasks: tasks.filter((t) => t.status === "pending").length,
              runningTasks: tasks.filter((t) => t.status === "running").length,
              doneTasks: tasks.filter((t) => t.status === "done").length,
              onlineAgents: agents.filter((a) => a.status === "online").length,
              onRefresh: () => { setPageLoading(true); setTimeout(() => setPageLoading(false), 200); },
              onPing: (id: string) => {
                stores.tasks.upsert({
                  ...createTask({
                    taskId: "ping-" + Date.now(),
                    workflowName: "ping_" + id,
                    traceId: "tr-ping-" + Date.now(),
                    device: id.includes("mobile") ? "mobile" : id.includes("tablet") ? "tablet" : "pc",
                    status: "running",
                  }),
                });
                navigate("tasks");
              },
            })
          : activeRoute === "mcp"
          ? e(McpWorkspace, {
              url: mcpUrl,
              onUrl: setMcpUrl,
              result: mcpResult,
              busy: mcpBusy,
              catalog: mcpCatalog,
              toolCallResult: mcpToolResult,
              toolCallBusy: mcpToolBusy,
              onUseEndpoint: (u: string) => { setMcpUrl(u); if (u.includes("54916")) setMcpToken(mcpToken); },
              onToolsCall: (tool: string) => {
                setMcpToolBusy(true);
                setMcpToolResult(null);
                void (async () => {
                  try {
                    const r = await callMcpTool(services.rest, {
                      url: mcpUrl,
                      tool,
                      arguments: { prompt: "Loom 试调用" },
                      token: mcpToken,
                    });
                    setMcpToolResult(
                      r.ok
                        ? tool + " → " + JSON.stringify(r.result).slice(0, 160)
                        : "失败：" + (r.error || "unknown")
                    );
                  } catch (err) {
                    setMcpToolResult(err instanceof Error ? err.message : String(err));
                  } finally {
                    setMcpToolBusy(false);
                  }
                })();
              },
              onProbe: () => {
                setMcpBusy(true);
                setMcpResult(null);
                void (async () => {
                  try {
                    const r = await probeMcp(services.rest, mcpUrl, 12, mcpToken);
                    setMcpResult(r);
                  } catch (err) {
                    const msg = err instanceof Error ? err.message : String(err);
                    setMcpResult({ ok: false, url: mcpUrl, message: msg, tools: [], serverInfo: null });
                  } finally {
                    setMcpBusy(false);
                  }
                })();
              },
            })
          : activeRoute === "recommend"
          ? e(RecommendPage, {
              launchState,
              onLaunch: (app: AgentApp) => {
                // 浏览器无法直接拉起 exe；尝试自定义协议 workbuddy:// / claude-code:// ，失败标记 missing
                const protoMap: Record<string, string> = {
                  work_buddy: "workbuddy://",
                  claude_code: "claude-code://",
                  codex: "codex://",
                  gemini_cli: "gemini-cli://",
                  cursor: "cursor://",
                  trae: "trae://",
                  windsurf: "windsurf://",
                  copilot: "copilot://",
                  aider: "aider://",
                  cline: "vscode://",
                };
                const proto = protoMap[app.id];
                if (!app.exePath && !app.command && !proto) {
                  setLaunchState((s) => ({ ...s, [app.id]: "missing" }));
                  return;
                }
                try {
                  if (proto && typeof location !== "undefined") {
                    // 尝试唤起本机协议；浏览器会拦截未知协议
                    window.location.href = proto;
                  }
                  setLaunchState((s) => ({ ...s, [app.id]: "ok" }));
                } catch {
                  setLaunchState((s) => ({ ...s, [app.id]: "error" }));
                }
              },
            })
          : activeRoute === "help"
          ? e(HelpPage)
          : activeRoute === "settings"
          ? e(SettingsPage, {
              tab: settingsTab,
              onTab: (t) => {
                setSettingsTab(t);
                navigate("settings", t);
              },
              loading: pageLoading,
              error: pageError,
              onRetry: () => setPageError(null),
              llmError,
              llmTestResult,
              activeProviderId,
              onActiveProvider: (id: string) => setActiveProviderId(id),
              providers: llmProviders,
              llmDraft,
              onLlmDraft: setLlmDraft,
              onSaveLlm: () => {
                setLlmProviders((prev) => {
                  const prevItem = llmDraft.providerId
                    ? prev.find((x) => x.providerId === llmDraft.providerId)
                    : undefined;
                  const plain =
                    llmDraft.apiKey || (prevItem as any)?.apiKeyPlain || "";
                  const item = {
                    providerId: llmDraft.providerId || "p-" + Date.now(),
                    name: llmDraft.name,
                    baseUrl: (llmDraft.baseUrl || "")
                      .trim()
                      .replace(/\/+$/, ""),
                    apiKeyMasked: llmDraft.apiKey
                      ? llmDraft.apiKey.slice(0, 4) +
                        "***" +
                        llmDraft.apiKey.slice(-3)
                      : (prevItem as any)?.apiKeyMasked || "",
                    hasApiKey: !!plain,
                    apiKeyPlain: plain,
                    defaultModel: prevItem?.defaultModel || "",
                    models: prevItem?.models || [],
                  };
                  const idx = prev.findIndex(
                    (x) => x.providerId === item.providerId
                  );
                  if (idx >= 0) {
                    const next = [...prev];
                    next[idx] = {
                      ...next[idx],
                      ...item,
                      apiKeyPlain:
                        (item as any).apiKeyPlain ||
                        (prev[idx] as any).apiKeyPlain,
                      models: item.models?.length
                        ? item.models
                        : prev[idx].models,
                    };
                    return next;
                  }
                  setActiveProviderId(item.providerId);
                  return [item, ...prev];
                });
                setLlmDraft({ name: "", baseUrl: "", apiKey: "" });
              },
              onFetchModels: (pid: string) => {
                setLlmError("");
                void (async () => {
                  const p = llmProviders.find((x) => x.providerId === pid);
                  if (!p) return;
                  try {
                    let models: string[] = [];
                    try {
                      const r = await services.llm.fetchModels(pid);
                      models = r.models || [];
                    } catch {
                      /* 浏览器直拉回退 */
                    }
                    if (!models.length) {
                      const key = (p as any).apiKeyPlain || "";
                      if (!key) {
                        throw new Error(
                          "本页缺少 API Key 明文，请重新保存后再拉取"
                        );
                      }
                      models = await fetchProviderModels(p.baseUrl, key);
                    }
                    if (!models.length)
                      throw new Error("服务商未返回任何模型 id");
                    setLlmProviders((prev) =>
                      prev.map((x) =>
                        x.providerId === pid ? { ...x, models } : x
                      )
                    );
                  } catch (err) {
                    const msg =
                      err instanceof Error ? err.message : String(err);
                    setLlmError("拉取模型失败：" + msg);
                    setLlmProviders((prev) =>
                      prev.map((x) =>
                        x.providerId === pid ? { ...x, models: [] } : x
                      )
                    );
                  }
                })();
              },
              onSelectModel: (pid: string, model: string) => {
                setLlmProviders((prev) =>
                  prev.map((p) =>
                    p.providerId === pid ? { ...p, defaultModel: model } : p
                  )
                );
                void services.llm.select(pid, model).catch(() => {});
              },
              onDeleteProvider: (pid: string) =>
                setLlmProviders((prev) =>
                  prev.filter((p) => p.providerId !== pid)
                ),
              onTestChat: (pid: string) => {
                setLlmError("");
                setLlmTestResult("");
                void (async () => {
                  const p = llmProviders.find((x) => x.providerId === pid);
                  if (!p || !p.defaultModel) return;
                  try {
                    const reply = await modelChat.complete(
                      {
                        providerId: pid,
                        baseUrl: p.baseUrl,
                        apiKey: (p as any).apiKeyPlain || "",
                        model: p.defaultModel,
                      },
                      [
                        {
                          id: "t1",
                          role: "user",
                          content: "你好，请用一句话介绍你自己",
                          createdAt: Date.now(),
                        },
                      ]
                    );
                    setLlmTestResult(reply.slice(0, 120));
                  } catch (err) {
                    const msg =
                      err instanceof Error ? err.message : String(err);
                    setLlmError(
                      msg.startsWith("模型对话失败") || msg.startsWith("请先")
                        ? msg
                        : "模型对话失败：" + msg
                    );
                  }
                })();
              },
              mcpUrl,
              onMcpUrl: setMcpUrl,
              mcpResult,
              mcpBusy,
              mcpCatalog,
              mcpToolResult,
              mcpToolBusy,
              onMcpUseEndpoint: (u: string) => setMcpUrl(u),
              onMcpToolsCall: (tool: string) => {
                setMcpToolBusy(true);
                setMcpToolResult(null);
                void (async () => {
                  try {
                    const r = await callMcpTool(services.rest, {
                      url: mcpUrl,
                      tool,
                      arguments: { prompt: "Loom 试调用" },
                      token: mcpToken,
                    });
                    setMcpToolResult(r.ok ? tool + " → " + JSON.stringify(r.result).slice(0, 120) : "失败：" + (r.error || "unknown"));
                  } catch (err) {
                    setMcpToolResult(err instanceof Error ? err.message : String(err));
                  } finally {
                    setMcpToolBusy(false);
                  }
                })();
              },
              onMcpProbe: () => {
                setMcpBusy(true);
                setMcpResult(null);
                void (async () => {
                  try {
                    const r = await probeMcp(services.rest, mcpUrl, 12, mcpToken);
                    setMcpResult(r);
                  } catch (err) {
                    const msg =
                      err instanceof Error ? err.message : String(err);
                    setMcpResult({
                      ok: false,
                      url: mcpUrl,
                      message: msg,
                      tools: [],
                      serverInfo: null,
                    });
                  } finally {
                    setMcpBusy(false);
                  }
                })();
              },
            })
          : e(
              "section",
              { className: "app-section", "data-view": "not-found" },
              e("h2", null, "未找到页面"),
              e(
                "button",
                {
                  type: "button",
                  className: "ui-button ui-button--primary",
                  onClick: () => navigate("chat"),
                },
                "回到对话"
              )
            )
    ),

    e(
      "nav",
      { className: "tabbar", "data-view": "tabbar", "aria-label": "底部导航" },
      (
        [
          ["chat", "对话"],
          ["tasks", "任务"],
          ["devices", "跨端"],
            ["help", "说明"],
          ["recommend", "推荐"],
          ["settings", "设置"],
          ["mcp", "MCP"],
        ] as Array<[AppRoute, string]>
      ).map(([id, label]) =>
        e(
          "button",
          {
            key: id,
            type: "button",
            className: "navbtn" + (activeRoute === id ? " is-on" : ""),
            "data-route": id,
            onClick: () => navigate(id),
          },
          label
        )
      )
    )
  );
}
