/**
 * 文件页 — 上传 / 列表 / 删除，Hub 同步 + 本地回退
 */

import * as React from "react";
import type { FileRef } from "../contracts/index.ts";
import { PageShell, EmptyState } from "./page-states.ts";
import { UI } from "../components/index.ts";
import type { ServiceLayer } from "../services/index.ts";

const e = React.createElement;

export function FilesPage(props: {
  services: ServiceLayer;
  localFiles?: FileRef[];
}) {
  const [files, setFiles] = React.useState<FileRef[]>(props.localFiles ?? []);
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const refresh = React.useCallback(async () => {
    setError(null);
    try {
      const list = await props.services.files.list();
      setFiles(list);
    } catch {
      // Hub 不可用时保留本地
    }
  }, [props.services]);

  React.useEffect(() => {
    void refresh();
    return props.services.bus.onAny((msg: { type?: string; file?: FileRef }) => {
      if (msg.type === "file.uploaded" && msg.file) {
        setFiles((prev) => {
          if (prev.some((f) => f.fileId === msg.file!.fileId)) return prev;
          return [msg.file!, ...prev];
        });
      }
    });
  }, [props.services, refresh]);

  const onUpload = (meta: { name: string; type: string; size: number }) => {
    setBusy(true);
    setError(null);
    void (async () => {
      try {
        const ref = await props.services.files.upload({
          name: meta.name,
          type: meta.type,
          size: meta.size,
        });
        setFiles((prev) => {
          if (prev.some((f) => f.fileId === ref.fileId)) return prev;
          return [ref, ...prev];
        });
      } catch (err) {
        // Hub 未连时本地占位
        const ref: FileRef = {
          fileId: `f-local-${Date.now()}`,
          name: meta.name,
          size: meta.size,
          mime: meta.type || "application/octet-stream",
          uri: `local://${meta.name}`,
          uploadedAt: Date.now(),
        };
        setFiles((prev) => [ref, ...prev]);
        setError(err instanceof Error ? err.message : "已保存到本地列表（Hub 未连）");
      } finally {
        setBusy(false);
      }
    })();
  };

  const onDelete = (fileId: string) => {
    void (async () => {
      try {
        await props.services.files.delete(fileId);
      } catch {
        /* 本地删 */
      }
      setFiles((prev) => prev.filter((f) => f.fileId !== fileId));
    })();
  };

  return e(
    PageShell,
    {
      route: "files",
      title: "文件区",
      subtitle: "上传 / 列表 / 删除 · Hub 集中存储",
      actions: e(
        "button",
        {
          type: "button",
          className: UI.button + " " + UI.buttonGhost,
          "data-action": "files-refresh",
          onClick: () => void refresh(),
        },
        "刷新"
      ),
    },
    e(
      "div",
      { className: "files-page", "data-page": "files", "data-view": "files" },
      e(
        "div",
        { className: "file-upload-bar glass" },
        e(
          "label",
          { className: "file-upload-btn", "data-action": "upload" },
          "选择文件",
          e("input", {
            type: "file",
            "data-field": "file-input",
            style: { display: "none" },
            disabled: busy,
            onChange: (ev: { target: { files: FileList | null } }) => {
              const f = ev.target.files?.[0];
              if (f) onUpload({ name: f.name, type: f.type, size: f.size });
            },
          })
        ),
        e("span", { className: "hint" }, busy ? "上传中…" : "Hub 存储 · 多端可见")
      ),
      error ? e("p", { className: "hint", "data-file-error": "true" }, error) : null,
      files.length === 0
        ? e(EmptyState, {
            title: "还没有文件",
            hint: "上传 PDF / 图片 / Markdown 等，供跨端任务使用。",
          })
        : e(
            "ul",
            { className: "file-list", "data-file-count": String(files.length) },
            files.map((f) =>
              e(
                "li",
                {
                  key: f.fileId,
                  className: "file-item glass",
                  "data-file-id": f.fileId,
                },
                e("span", { className: "file-name" }, f.name),
                e(
                  "span",
                  { className: "file-meta" },
                  `${f.mime} · ${f.size}B · ${f.uri}`
                ),
                e(
                  "button",
                  {
                    type: "button",
                    className: UI.button + " " + UI.buttonDanger,
                    "data-action": "delete-file",
                    onClick: () => onDelete(f.fileId),
                  },
                  "删除"
                )
              )
            )
          )
    )
  );
}
