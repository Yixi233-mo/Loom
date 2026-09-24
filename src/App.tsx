import * as React from "react";
import { SchemaRenderer } from "./shell/schema-renderer.impl.ts";
import { Workspace, LlmSettingsPanel, McpPanel } from "./views/index.ts";
import {
  ChatWorkbench,
  TaskCenter,
  SettingsPage,
} from "./features/index.ts";
import { useHashRoute, navigate, type AppRoute } from "./hooks/index.ts";
import { createAppStores, createTask, createAgent } from "./state/index.ts";
import { createServiceLayer } from "./services/index.ts";
import { ModelChatClient } from "./services/model-chat.ts";
import { probeMcp, fetchProviderModels } from "./services/llm-api.ts";
import { createPlatformLayer, registerPayload } from "./platform/index.ts";
import {
  sampleNotesPlugin,
  sampleNotesData,
} from "./demo/sample-plugin.ts";
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
  const [chatSize, setChatSize] = React.useState<"default" | "expanded">("default");
  const [chatBusy, setChatBusy] = React.useState(false);
  const modelChat = React.useMemo(() => new ModelChatClient(), []);
  const [llmError, setLlmError] = React.useState("");
  const [llmTestResult, setLlmTestResult] = React.useState("");
  const [mcpUrl, setMcpUrl] = React.useState("http://127.0.0.1:3900/mcp");
  const [mcpResult, setMcpResult] = React.useState<any>(null);
  const [mcpBusy, setMcpBusy] = React.useState(false);
  const [llmDraft, setLlmDraft] = React.useState<{
    name: string;
    baseUrl: string;
    apiKey: string;
    providerId?: string;
  }>({ name: '', baseUrl: '', apiKey: '' });
  const [llmProviders, setLlmProviders] = React.useState<Array<any>>([]);
  const [settingsTab, setSettingsTab] = React.useState<"llm" | "mcp">("llm");
  const [pageLoading, setPageLoading] = React.useState(false);
  const [pageError, setPageError] = React.useState<string | null>(null);
  const route = useHashRoute();
  const activeRoute: AppRoute = route.route;
  const [files, setFiles] = React.useState([
    {
      fileId: "f-demo-1",
      name: "spec.pdf",
      size: 2048,
      mime: "application/pdf",
      uri: "hub://files/f-demo-1",
      uploadedAt: Date.now(),
    },
  ]);

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
    return () => {
      offs.forEach((off) => off());
      window.removeEventListener("resize", onResize);
    };
  }, []);

  void tick;

  const session = stores.session.get();
  const tasks = stores.tasks.list();
  const agents = stores.agents.list();
  const reg = registerPayload(platform.device, `web-${platform.device.deviceType}-1`);

  return e(
    "div",
    {
      className: `app-shell layout-${platform.layout}`,
      "data-app": "loom-shell",
      "data-device": platform.device.deviceType,
      "data-layout": platform.layout,
    },
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
        "span",
        { className: "app-badge", "data-platform-badge": "true" },
        `${platform.device.deviceType} · ${platform.layout}${
          platform.tauri.available ? " · Tauri" : " · Web"
        }`
      )
    ),

    /* FE.3 核心页面：hash 路由 */
    activeRoute === "chat"
      ? e(ChatWorkbench, {
          session,
          loading: pageLoading,
          error: pageError,
          busy: chatBusy,
          modelLabel: llmProviders.find((p) => p.defaultModel)?.defaultModel,
          chatSize,
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
            const active = llmProviders.find((p) => p.defaultModel && p.baseUrl);
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
              onMcpProbe: () => {
                setMcpBusy(true);
                setMcpResult(null);
                void (async () => {
                  try {
                    const r = await probeMcp(services.rest, mcpUrl);
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
            ),

    e(Workspace, {
      session,
      tasks,
      files,
      filter,
      chatSize,
      onToggleSize: () =>
        setChatSize((s) => (s === "default" ? "expanded" : "default")),
      chatBusy,
      modelLabel: llmProviders.find((p) => p.defaultModel)?.defaultModel,
      onSend: (text: string) => {
        stores.session.appendMessage({ role: "user", content: text });
        stores.session.setDraft("");
        stores.session.setStatus("streaming");
        setChatBusy(true);
        const active = llmProviders.find((p) => p.defaultModel && p.baseUrl);
        void (async () => {
          try {
            if (active) {
              const reply = await modelChat.complete(
                {
                  providerId: active.providerId,
                  baseUrl: active.baseUrl,
                  apiKey: (active as any).apiKeyPlain || (active as any)._apiKey || "",
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
      onDraft: (text: string) => stores.session.setDraft(text),
      onFilter: (f: TaskStatus | "all") => setFilter(f),
      onUpload: (file: { name: string; type: string; size: number }) => {
        const ref = {
          fileId: `f-${Date.now()}`,
          name: file.name,
          size: file.size,
          mime: file.type || "application/octet-stream",
          uri: `hub://files/${Date.now()}`,
          uploadedAt: Date.now(),
        };
        setFiles((prev) => [ref, ...prev]);
        services.bus.emit({ type: "file.uploaded", file: ref });
      },
      onDeleteFile: (fileId: string) => {
        setFiles((prev) => prev.filter((f) => f.fileId !== fileId));
      },
    }),

    e(
      "section",
      { className: "app-section", "data-view": "platform" },
      e("h2", null, "三端适配"),
      e(
        "p",
        { className: "hint" },
        `设备=${reg.device_type} · 布局=${platform.layout} · 能力=${platform.capabilities.join(
          ", "
        )}`
      ),
      e(
        "div",
        { className: "plugin-tools" },
        platform.capabilities.map((c) => e("code", { key: c }, c))
      )
    ),

    e(LlmSettingsPanel, {
      error: llmError,
      testResult: llmTestResult,
      providers: llmProviders,
      draft: llmDraft,
      onDraft: setLlmDraft,
      onSave: () => {
        // REST 优先，失败回退本地内存
        setLlmProviders((prev) => {
          const prevItem = llmDraft.providerId
            ? prev.find((x) => x.providerId === llmDraft.providerId)
            : undefined;
          const plain = llmDraft.apiKey || (prevItem as any)?.apiKeyPlain || "";
          const item = {
            providerId: llmDraft.providerId || 'p-' + Date.now(),
            name: llmDraft.name,
            baseUrl: (llmDraft.baseUrl || '').trim().replace(/\/+$/, ''),
            apiKeyMasked: llmDraft.apiKey
              ? llmDraft.apiKey.slice(0, 4) + '***' + llmDraft.apiKey.slice(-3)
              : (prevItem as any)?.apiKeyMasked || '',
            hasApiKey: !!plain,
            apiKeyPlain: plain,
            defaultModel: prevItem?.defaultModel || '',
            models: prevItem?.models || [],
          };
          const idx = prev.findIndex((x) => x.providerId === item.providerId);
          if (idx >= 0) {
            const next = [...prev];
            next[idx] = {
              ...next[idx],
              ...item,
              apiKeyPlain: (item as any).apiKeyPlain || (prev[idx] as any).apiKeyPlain,
              models: item.models?.length ? item.models : prev[idx].models,
            };
            return next;
          }
          return [item, ...prev];
        });
        setLlmDraft({ name: '', baseUrl: '', apiKey: '' });
      },
      onFetchModels: (pid) => {
        setLlmError("");
        void (async () => {
          const p = llmProviders.find((x) => x.providerId === pid);
          if (!p) return;
          try {
            // 1) 后端代拉（密钥在服务端解密，最稳）
            // 2) 浏览器直拉（需本页保存过明文 Key）
            let models: string[] = [];
            let backendErr: unknown = null;
            try {
              const r = await services.llm.fetchModels(pid);
              models = r.models || [];
            } catch (e) {
              backendErr = e;
            }
            if (!models.length) {
              const key = (p as any).apiKeyPlain || "";
              if (!key) {
                const backendMsg =
                  backendErr instanceof Error ? backendErr.message : String(backendErr ?? "");
                throw new Error(
                  "本页缺少 API Key 明文，请在上方重新填入 Key 并「保存配置」后再拉取" +
                    (backendMsg ? `（后端：${backendMsg}）` : "")
                );
              }
              models = await fetchProviderModels(p.baseUrl, key);
            }
            if (!models.length) throw new Error("服务商未返回任何模型 id");
            setLlmProviders((prev) =>
              prev.map((x) =>
                x.providerId === pid ? { ...x, models } : x
              )
            );
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            setLlmError("拉取模型失败：" + msg);
            setLlmProviders((prev) =>
              prev.map((x) =>
                x.providerId === pid ? { ...x, models: [] } : x
              )
            );
          }
        })();
      },
      onSelectModel: (pid, model) => {
        setLlmProviders((prev) =>
          prev.map((p) => (p.providerId === pid ? { ...p, defaultModel: model } : p))
        );
        void services.llm.select(pid, model).catch(() => {});
      },
      onDelete: (pid) => setLlmProviders((prev) => prev.filter((p) => p.providerId !== pid)),
      onTestChat: (pid) => {
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
              [{ id: "t1", role: "user", content: "你好，请用一句话介绍你自己", createdAt: Date.now() }]
            );
            setLlmTestResult(reply.slice(0, 120));
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            setLlmError(msg.startsWith("模型对话失败") || msg.startsWith("请先") ? msg : "模型对话失败：" + msg);
          }
        })();
      },
    }),

    e(McpPanel, {
      url: mcpUrl,
      onUrl: setMcpUrl,
      result: mcpResult,
      busy: mcpBusy,
      onProbe: () => {
        setMcpBusy(true);
        setMcpResult(null);
        void (async () => {
          try {
            const r = await probeMcp(services.rest, mcpUrl);
            setMcpResult(r);
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
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
    }),

    e(
      "section",
      { className: "app-section", "data-view": "agents" },
      e("h2", null, "Agent 状态"),
      e(
        "div",
        { className: "plugin-tools" },
        agents.map((a) =>
          e(
            "code",
            {
              key: a.agentName,
              "data-agent": a.agentName,
              "data-status": a.status,
            },
            `${a.agentName} · ${a.status} · deg=${a.degradationLevel}`
          )
        )
      )
    ),

    e(
      "section",
      { className: "app-section", "data-panel": "plugin" },
      e("h2", null, "示例插件 UI"),
      e(SchemaRenderer, {
        schema: sampleNotesPlugin.ui,
        data: sampleNotesData,
      })
    )
  );
}
