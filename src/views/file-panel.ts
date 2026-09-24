/**
 * 文件区 — 上传 + 列表。
 */

import * as React from "react";
import type { FileRef } from "../contracts/index.ts";

const e = React.createElement;

export function FilePanel(props: {
  files: FileRef[];
  onUpload?: (file: { name: string; type: string; size: number }) => void;
  onDelete?: (fileId: string) => void;
}) {
  const { files, onUpload, onDelete } = props;
  return e(
    "section",
    { className: "panel file-panel", "data-view": "files" },
    e(
      "header",
      { className: "panel-header" },
      e("h2", null, "文件区"),
      e(
        "label",
        { className: "file-upload", "data-action": "upload" },
        "上传文件",
        e("input", {
          type: "file",
          "data-field": "file-input",
          style: { display: "none" },
          onChange: (ev: { target: { files: FileList | null } }) => {
            const f = ev.target.files?.[0];
            if (f && onUpload) {
              onUpload({ name: f.name, type: f.type, size: f.size });
            }
          },
        })
      )
    ),
    e(
      "ul",
      { className: "file-list", "data-file-count": files.length },
      files.length === 0
        ? e("p", { className: "empty-hint" }, "暂无文件")
        : files.map((f) =>
            e(
              "li",
              {
                key: f.fileId,
                className: "file-item",
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
                  "data-action": "delete-file",
                  onClick: () => onDelete?.(f.fileId),
                },
                "删除"
              )
            )
          )
    )
  );
}
