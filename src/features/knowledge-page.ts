/**
 * 知识库页 — 新建库 / 添加知识 / 检索（供 RAG 使用）
 */

import * as React from "react";
import { PageShell, EmptyState, LoadingState, phaseOf } from "./page-states.ts";
import { UI } from "../components/index.ts";
import type { RestClient } from "../services/rest.ts";

const e = React.createElement;

export interface KbItem { id: string; name: string; count: number }
export interface KbDoc {
  id: string;
  title: string;
  content: string;
  tags: string[];
  source: string;
  kb: string;
}
export interface KbHit {
  id: string;
  title: string;
  score: number;
  snippet: string;
  kb: string;
}
export interface KbSource {
  id: string;
  kind: string;
  name?: string;
  enabled?: boolean;
  health?: { ok?: boolean; error?: string; [k: string]: unknown };
}

const SOURCE_KINDS = ["auto", "vector", "notion", "docs", "local"] as const;

function detectKindFromText(s: string): string {
  const low = (s || "").trim().toLowerCase();
  if (!low) return "";
  if (low.includes("notion.so") || low.includes("notion.site")) return "notion";
  if (low.startsWith("http://") || low.startsWith("https://")) return "docs";
  if (low.startsWith("file://") || /^[a-zA-Z]:[\\/]/.test(s) || s.startsWith("\\\\")) return "local";
  if (/vector|embedding|qdrant|chroma|milvus|faiss/.test(low)) return "vector";
  return "";
}

export function KnowledgePage(props: {
  rest: RestClient;
}) {
  const [kbs, setKbs] = React.useState<KbItem[]>([]);
  const [docs, setDocs] = React.useState<KbDoc[]>([]);
  const [hits, setHits] = React.useState<KbHit[]>([]);
  const [kb, setKb] = React.useState("builtin");
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const [tags, setTags] = React.useState("");
  const [query, setQuery] = React.useState("");
  const [newKb, setNewKb] = React.useState("");
  const [newKbName, setNewKbName] = React.useState("");
  const [kbMsg, setKbMsg] = React.useState<string | null>(null);
  const [sources, setSources] = React.useState<KbSource[]>([]);
  const [srcKind, setSrcKind] = React.useState<string>("vector");
  const [srcId, setSrcId] = React.useState("");
  const [srcName, setSrcName] = React.useState("");
  const [srcToken, setSrcToken] = React.useState("");
  const [srcExtra, setSrcExtra] = React.useState("");
  const [srcMsg, setSrcMsg] = React.useState<string | null>(null);
  const [importMsg, setImportMsg] = React.useState<string | null>(null);
  const [importPath, setImportPath] = React.useState("");
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);

  const rest = props.rest;

  const refresh = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [kbRes, docRes, srcRes] = await Promise.all([
        rest.requestPublic<{ items: KbItem[] }>("/api/knowledge/kbs"),
        rest.requestPublic<{ items: KbDoc[] }>(
          "/api/knowledge/docs" + (kb ? `?kb=${encodeURIComponent(kb)}` : "")
        ),
        rest
          .requestPublic<{ items: KbSource[] }>("/api/knowledge/sources")
          .catch(() => ({ items: [] as KbSource[] })),
      ]);
      setKbs(kbRes.items || []);
      setDocs(docRes.items || []);
      setSources(srcRes.items || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "加载失败，请确认 Hub 已启动");
    } finally {
      setLoading(false);
    }
  }, [rest, kb]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  const addDoc = () => {
    if (!title.trim()) return;
    void (async () => {
      try {
        await rest.requestPublic("/api/knowledge/docs", {
          method: "POST",
          body: {
            title: title.trim(),
            content,
            tags: tags.split(/[,，\s]+/).filter(Boolean),
            kb,
            source: "manual",
          },
        });
        setTitle("");
        setContent("");
        setTags("");
        await refresh();
      } catch (err) {
        setError(err instanceof Error ? err.message : "保存失败");
      }
    })();
  };

  const removeDoc = (id: string) => {
    void (async () => {
      try {
        await rest.requestPublic(`/api/knowledge/docs/${id}`, { method: "DELETE" });
        await refresh();
      } catch {
        /* ignore */
      }
    })();
  };

  const search = () => {
    if (!query.trim()) return;
    void (async () => {
      try {
        const res = await rest.requestPublic<{ hits: KbHit[] }>(
          "/api/knowledge/search",
          { method: "POST", body: { query: query.trim(), kb, limit: 8 } }
        );
        setHits(res.hits || []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "检索失败");
      }
    })();
  };

  const createKb = () => {
    const id = newKb.trim().replace(/\s+/g, "_");
    if (!id) {
      setKbMsg("请填写知识库 ID");
      return;
    }
    const name = newKbName.trim() || id;
    void (async () => {
      try {
        const res = await rest.requestPublic<{ ok: boolean; items?: KbItem[] }>(
          "/api/knowledge/kbs",
          { method: "POST", body: { id, name } }
        );
        if (res.items) setKbs(res.items);
        setNewKb("");
        setNewKbName("");
        setKb(id);
        setHits([]);
        setKbMsg(`已新建知识库「${name}」，可直接添加知识`);
        await refresh();
      } catch (err) {
        setKbMsg(err instanceof Error ? err.message : "新建失败");
      }
    })();
  };

  const switchKb = (next: string) => {
    if (!next || next === kb) return;
    setKb(next);
    setHits([]);
    setKbMsg(null);
  };

  const sourceBody = () => {
    let auto = srcKind;
    if (auto === "auto") {
      auto =
        detectKindFromText(srcId) ||
        detectKindFromText(srcToken) ||
        detectKindFromText(srcExtra) ||
        "local";
    }
    const body: Record<string, unknown> = {
      id: srcId.trim(),
      kind: auto,
      name: srcName.trim(),
    };
    if (auto === "notion") {
      body.token = srcToken.trim();
      if (srcExtra.trim()) body.database_id = srcExtra.trim();
    } else if (auto === "docs") {
      body.base_url = srcExtra.trim() || srcToken.trim();
      body.entry = body.base_url;
    } else if (auto === "vector") {
      if (srcToken.trim()) body.endpoint = srcToken.trim();
      if (srcExtra.trim()) body.api_key = srcExtra.trim();
    } else if (auto === "local") {
      if (srcExtra.trim() || srcToken.trim()) body.entry = srcExtra.trim() || srcToken.trim();
    }
    return body;
  };

  const onPickFiles = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    void (async () => {
      try {
        const payload: Array<{ filename: string; content: string }> = [];
        const skipped: string[] = [];
        for (const f of Array.from(files).slice(0, 30)) {
          const isText =
            /\.(md|markdown|txt|log|json|ya?ml|toml|ini|cfg|csv|tsv|html?|xml|py|ts|tsx|js|jsx|go|rs|java|sh|ps1|sql)$/i.test(
              f.name
            ) || (f.type || "").startsWith("text/");
          if (!isText) {
            skipped.push(f.name);
            continue;
          }
          const content = await f.text();
          payload.push({ filename: f.name, content });
        }
        if (!payload.length) {
          setImportMsg(
            skipped.length
              ? `未识别到可读文本：${skipped.join("、")}（pdf/图片等暂不支持抽取）`
              : "未选择文件"
          );
          return;
        }
        const res = await rest.requestPublic<{
          ok: boolean;
          count?: number;
          skipped?: Array<{ title?: string; reason?: string }>;
        }>("/api/knowledge/import/files", {
          method: "POST",
          body: { kb, files: payload },
        });
        const skipN = (res.skipped || []).length + skipped.length;
        setImportMsg(
          `已导入 ${res.count ?? payload.length} 个文件` +
            (skipN ? `，跳过 ${skipN} 个` : "") +
            "。已按扩展名自动识别类型并写入当前库。"
        );
        await refresh();
      } catch (err) {
        setImportMsg(err instanceof Error ? err.message : "导入失败");
      }
    })();
  };

  const importFromPath = () => {
    const p = importPath.trim();
    if (!p) return;
    void (async () => {
      try {
        const res = await rest.requestPublic<{
          ok: boolean;
          imported?: unknown[];
          skipped?: unknown[];
        }>("/api/knowledge/import/path", {
          method: "POST",
          body: { path: p, kb, max_files: 50 },
        });
        const n = (res.imported || []).length;
        const s = (res.skipped || []).length;
        setImportMsg(
          `从路径导入 ${n} 个文件` + (s ? `，跳过 ${s} 个` : "") + `（${p}）`
        );
        setImportPath("");
        await refresh();
      } catch (err) {
        setImportMsg(err instanceof Error ? err.message : "路径导入失败（需 Hub 可访问该路径）");
      }
    })();
  };

  const autoFillKind = (text: string, which: "id" | "token" | "extra") => {
    const k = detectKindFromText(text);
    if (k) setSrcKind(k);
    if (which === "id" && text.includes("/") && !srcName) {
      // 粘贴 URL 时若无名称，用最后一段做默认 ID
      const seg = text.split(/[/?#]/).filter(Boolean).pop() || "";
      if (seg && !srcId) setSrcId(seg.slice(0, 48));
    }
  };

  const addSource = () => {
    if (!srcId.trim()) return;
    void (async () => {
      try {
        await rest.requestPublic("/api/knowledge/sources", {
          method: "POST",
          body: sourceBody(),
        });
        setSrcMsg(`已添加外部源 ${srcId.trim()}`);
        setSrcId("");
        setSrcName("");
        setSrcToken("");
        setSrcExtra("");
        await refresh();
      } catch (err) {
        setSrcMsg(err instanceof Error ? err.message : "添加失败");
      }
    })();
  };

  const testSource = (s?: KbSource) => {
    const body = s
      ? {
          id: s.id,
          kind: s.kind,
          name: s.name || "",
          token: (s as { token?: string }).token,
          endpoint: (s as { endpoint?: string }).endpoint,
          api_key: (s as { api_key?: string }).api_key,
          base_url: (s as { base_url?: string }).base_url,
          entry: (s as { entry?: string }).entry,
          database_id: (s as { database_id?: string }).database_id,
        }
      : sourceBody();
    void (async () => {
      try {
        const res = await rest.requestPublic<{ ok: boolean; health?: unknown; error?: string }>(
          "/api/knowledge/sources/test",
          { method: "POST", body }
        );
        setSrcMsg(
          res.ok
            ? `测试通过：${JSON.stringify(res.health || {})}`
            : `测试失败：${res.error || "未知错误"}`
        );
        await refresh();
      } catch (err) {
        setSrcMsg(err instanceof Error ? err.message : "测试失败");
      }
    })();
  };

  const removeSource = (id: string) => {
    void (async () => {
      try {
        await rest.requestPublic(`/api/knowledge/sources/${encodeURIComponent(id)}`, {
          method: "DELETE",
        });
        setSrcMsg(`已删除外部源 ${id}`);
        await refresh();
      } catch (err) {
        setSrcMsg(err instanceof Error ? err.message : "删除失败");
      }
    })();
  };

  const phase = phaseOf({ loading, error, empty: !loading && !error && docs.length === 0 });
  const currentKbName =
    kbs.find((k) => k.id === kb)?.name || kb || "builtin";
  // 保证受控 select 始终有合法 value（列表未载入 / 新建后未同步时）
  const kbOptions: KbItem[] = kbs.some((k) => k.id === kb)
    ? kbs
    : [{ id: kb || "builtin", name: currentKbName, count: 0 }, ...kbs];

  return e(
    PageShell,
    {
      route: "knowledge",
      title: "知识库",
      subtitle: "添加资料 → 对话里问「查资料 / 知识库」时由 RAG 检索引用",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "kb-refresh",
          onClick: () => void refresh(),
        },
        "刷新"
      ),
    },
    e(
      "div",
      { className: "kb-page", "data-page": "knowledge", "data-view": "knowledge" },

      /* 选库 / 新建库 */
      e(
        "div",
        { className: "kb-bar glass", "data-view": "kb-switch" },
        e(
          "div",
          { className: "kb-bar-row" },
          e("label", { className: "kb-bar-label", htmlFor: "kb-select" }, "当前知识库"),
          e(
            "select",
            {
              id: "kb-select",
              className: UI.input,
              "data-field": "kb-select",
              "data-kb": kb,
              value: kb,
              onChange: (ev: { target: { value: string } }) => switchKb(ev.target.value),
            },
            ...kbOptions.map((k) =>
              e("option", { key: k.id, value: k.id }, `${k.name}（${k.count}）`)
            )
          ),
          e(
            "span",
            { className: "hint", "data-view": "kb-current" },
            `写入 / 检索均作用于「${currentKbName}」`
          )
        ),
        e(
          "div",
          { className: "kb-bar-row kb-create-row" },
          e("label", { className: "kb-bar-label", htmlFor: "kb-new" }, "新建库"),
          e("input", {
            id: "kb-new",
            className: UI.input,
            "data-field": "kb-new",
            placeholder: "ID，如：产品文档",
            value: newKb,
            onChange: (ev: { target: { value: string } }) => setNewKb(ev.target.value),
            onKeyDown: (ev: { key: string }) => {
              if (ev.key === "Enter") createKb();
            },
          }),
          e("input", {
            id: "kb-new-name",
            className: UI.input,
            "data-field": "kb-new-name",
            placeholder: "显示名（可选）",
            value: newKbName,
            onChange: (ev: { target: { value: string } }) => setNewKbName(ev.target.value),
            onKeyDown: (ev: { key: string }) => {
              if (ev.key === "Enter") createKb();
            },
          }),
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonPrimary,
              "data-action": "kb-create",
              disabled: !newKb.trim(),
              onClick: createKb,
            },
            "新建库"
          )
        ),
        kbMsg
          ? e("p", { className: "hint", "data-kb-msg": "true" }, kbMsg)
          : null
      ),

      /* 添加知识 */
      e(
        "div",
        { className: "prompt-editor glass", "data-view": "kb-add" },
        e("h3", null, "添加知识"),
        e(
          "p",
          { className: "hint", "data-view": "kb-add-target" },
          `将存入「${currentKbName}」`
        ),
        e("input", {
          className: UI.input,
          "data-field": "kb-title",
          placeholder: "标题，例如：部署流程",
          value: title,
          onChange: (ev: { target: { value: string } }) => setTitle(ev.target.value),
        }),
        e("input", {
          className: UI.input,
          "data-field": "kb-tags",
          placeholder: "标签（逗号分隔），例如：运维, 部署",
          value: tags,
          onChange: (ev: { target: { value: string } }) => setTags(ev.target.value),
        }),
        e("textarea", {
          className: UI.input,
          "data-field": "kb-content",
          placeholder: "正文内容…（支持多段）",
          rows: 5,
          value: content,
          onChange: (ev: { target: { value: string } }) => setContent(ev.target.value),
        }),
        e(
          "button",
          {
            type: "button",
            className: UI.button + " " + UI.buttonPrimary,
            "data-action": "kb-add",
            disabled: !title.trim(),
            onClick: addDoc,
          },
          "存入知识库"
        )
      ),

      /* 检索预览 */
      e(
        "div",
        { className: "kb-search glass" },
        e("input", {
          className: UI.input,
          "data-field": "kb-query",
          placeholder: "试试检索，例如：怎么部署？",
          value: query,
          onChange: (ev: { target: { value: string } }) => setQuery(ev.target.value),
          onKeyDown: (ev: { key: string }) => {
            if (ev.key === "Enter") search();
          },
        }),
        e(
          "button",
          {
            type: "button",
            className: UI.button + " " + UI.buttonPrimary,
            "data-action": "kb-search",
            disabled: !query.trim(),
            onClick: search,
          },
          "检索"
        )
      ),
      hits.length > 0
        ? e(
            "ul",
            { className: "kb-hits", "data-view": "kb-hits" },
            hits.map((h) =>
              e(
                "li",
                { key: h.id, className: "kb-hit glass", "data-hit-id": h.id },
                e("strong", null, `${h.title}（${h.score}分）`),
                e("p", { className: "hint" }, h.snippet)
              )
            )
          )
        : null,

      /* 外部源管理 */
      e(
        "div",
        { className: "kb-sources glass", "data-view": "kb-sources" },
        e("h3", null, "外部源 / 导入"),
        e(
          "p",
          { className: "hint" },
          "像打开文件一样导入本地资料（自动识别类型），或粘贴链接自动判断 Notion / 文档站。"
        ),

        /* 本地文件导入 */
        e(
          "div",
          { className: "kb-import-row" },
          e("input", {
            ref: fileInputRef,
            type: "file",
            multiple: true,
            accept: ".md,.markdown,.txt,.log,.json,.yaml,.yml,.toml,.ini,.csv,.tsv,.html,.htm,.xml,.py,.ts,.tsx,.js,.jsx,.go,.rs,.java,.sh,.ps1,.sql,text/*",
            style: { display: "none" },
            "data-field": "kb-import-file",
            onChange: (ev: {
              target: { files: FileList | null; value?: string };
              currentTarget: { value: string };
            }) => {
              onPickFiles(ev.target.files);
              try {
                ev.currentTarget.value = "";
              } catch {
                /* ignore */
              }
            },
          }),
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonPrimary,
              "data-action": "kb-import-file",
              onClick: () => fileInputRef.current?.click(),
            },
            "导入本地文件"
          ),
          e("input", {
            className: UI.input,
            "data-field": "kb-import-path",
            placeholder: "或填本机文件夹路径，如 E:\\docs\\wiki",
            value: importPath,
            onChange: (ev: { target: { value: string } }) => setImportPath(ev.target.value),
            onKeyDown: (ev: { key: string }) => {
              if (ev.key === "Enter") importFromPath();
            },
          }),
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonGhost,
              "data-action": "kb-import-path",
              disabled: !importPath.trim(),
              onClick: importFromPath,
            },
            "从路径导入"
          )
        ),
        importMsg
          ? e("p", { className: "hint", "data-import-msg": "true" }, importMsg)
          : null,

        e(
          "ul",
          { className: "kb-source-list", "data-source-count": String(sources.length) },
          sources.length === 0
            ? e("li", { className: "hint" }, "暂无外部源")
            : sources.map((s) =>
                e(
                  "li",
                  { key: s.id, className: "kb-source-item", "data-source-id": s.id },
                  e(
                    "div",
                    null,
                    e("strong", null, s.name || s.id),
                    e("code", null, ` ${s.kind}`),
                    e(
                      "span",
                      {
                        className: s.health?.ok ? "kb-src-ok" : "kb-src-bad",
                        "data-source-health": s.health?.ok ? "ok" : "bad",
                      },
                      s.health?.ok ? " · 可用" : " · 不可用"
                    )
                  ),
                  e(
                    "div",
                    { className: "kb-source-actions" },
                    e(
                      "button",
                      {
                        type: "button",
                        className: UI.button + " " + UI.buttonGhost,
                        "data-action": "kb-source-test",
                        onClick: () => testSource(s),
                      },
                      "测试"
                    ),
                    e(
                      "button",
                      {
                        type: "button",
                        className: "ui-button ui-button--danger",
                        "data-action": "kb-source-delete",
                        onClick: () => removeSource(s.id),
                      },
                      "删除"
                    )
                  )
                )
              )
        ),
        e(
          "div",
          { className: "kb-source-form" },
          e(
            "select",
            {
              className: UI.input,
              "data-field": "src-kind",
              value: srcKind,
              onChange: (ev: { target: { value: string } }) => setSrcKind(ev.target.value),
            },
            ...SOURCE_KINDS.map((k) =>
              e("option", { key: k, value: k }, k === "auto" ? "自动识别" : k)
            )
          ),
          e("input", {
            className: UI.input,
            "data-field": "src-id",
            placeholder: "源 ID 或粘贴链接，如 https://xxx.notion.so/...",
            value: srcId,
            onChange: (ev: { target: { value: string } }) => {
              setSrcId(ev.target.value);
              autoFillKind(ev.target.value, "id");
            },
          }),
          e("input", {
            className: UI.input,
            "data-field": "src-name",
            placeholder: "显示名（可选）",
            value: srcName,
            onChange: (ev: { target: { value: string } }) => setSrcName(ev.target.value),
          }),
          e("input", {
            className: UI.input,
            "data-field": "src-token",
            placeholder:
              srcKind === "notion"
                ? "Notion token"
                : srcKind === "vector"
                  ? "endpoint（可选）"
                  : "token / endpoint / 路径（可选）",
            value: srcToken,
            onChange: (ev: { target: { value: string } }) => {
              setSrcToken(ev.target.value);
              autoFillKind(ev.target.value, "token");
            },
          }),
          e("input", {
            className: UI.input,
            "data-field": "src-extra",
            placeholder:
              srcKind === "notion"
                ? "database_id"
                : srcKind === "docs"
                  ? "文档站 base_url"
                  : srcKind === "local"
                    ? "本地文件夹路径"
                    : "api_key / base_url（可选）",
            value: srcExtra,
            onChange: (ev: { target: { value: string } }) => {
              setSrcExtra(ev.target.value);
              autoFillKind(ev.target.value, "extra");
            },
          }),
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonPrimary,
              "data-action": "kb-source-add",
              disabled: !srcId.trim(),
              onClick: addSource,
            },
            "添加源"
          ),
          e(
            "button",
            {
              type: "button",
              className: UI.button + " " + UI.buttonGhost,
              "data-action": "kb-source-test-form",
              disabled: !srcId.trim(),
              onClick: () => testSource(),
            },
            "测试"
          )
        ),
        srcMsg ? e("p", { className: "hint", "data-source-msg": "true" }, srcMsg) : null
      ),

      error ? e("p", { className: "hint", "data-kb-error": "true" }, error) : null,

      phase === "loading"
        ? e(LoadingState, { label: "载入知识库…", rows: 3 })
        : phase === "error"
          ? null
          : phase === "empty"
            ? e(EmptyState, {
                title: "知识库还是空的",
                hint: "在上方添加文档或笔记。之后对话里问「查资料」就会引用这里的内容。",
              })
            : e(
                "ul",
                { className: "kb-list", "data-doc-count": String(docs.length) },
                docs.map((d) =>
                  e(
                    "li",
                    { key: d.id, className: "kb-doc glass", "data-doc-id": d.id },
                    e(
                      "header",
                      null,
                      e("strong", null, d.title),
                      e(
                        "div",
                        null,
                        ...d.tags.map((t) => e("code", { key: t }, t)),
                        e(
                          "button",
                          {
                            type: "button",
                            className: "ui-button ui-button--danger",
                            "data-action": "kb-delete",
                            onClick: () => removeDoc(d.id),
                          },
                          "删除"
                        )
                      )
                    ),
                    e("p", { className: "kb-doc-content" }, d.content)
                  )
                )
              )
    )
  );
}
