#!/usr/bin/env python3
"""知识库全链路 E2E — 走 HTTP 打真 Hub。

覆盖：选库/新建库 → 导入文件 → 路径导入 → 添加知识 → 检索 → 外部源(自动识别) → 联邦检索 → 删除
用法：python scripts/e2e_knowledge.py [base_url]
默认 http://127.0.0.1:8765
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8765").rstrip("/")

PASS = 0
FAIL = 0


def ok(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}" + (f" — {detail}" if detail else ""))
    else:
        FAIL += 1
        print(f"  ✗ {name}" + (f" — {detail}" if detail else ""))


def req(method: str, path: str, body: dict | None = None, timeout: float = 15.0):
    url = BASE + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    r = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw) if raw else {}
        except Exception:
            return e.code, {"raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}


def main() -> int:
    print(f"=== 知识库全链路 E2E → {BASE} ===")

    print("\n[0] 健康检查")
    code, body = req("GET", "/health")
    ok("Hub /health", code == 200, f"status={code}")

    print("\n[1] 选库/新建库")
    code, body = req("GET", "/api/knowledge/kbs")
    ok("列出知识库", code == 200 and "items" in body, f"items={len(body.get('items') or [])}")
    code, body = req("POST", "/api/knowledge/kbs", {"id": "e2e库", "name": "E2E 产品文档"})
    ok("新建库 e2e库", code == 200 and any(k.get("id") == "e2e库" for k in body.get("items") or []))
    code, body = req("GET", "/api/knowledge/kbs")
    ids = [k["id"] for k in body.get("items") or []]
    ok("下拉可见新库", "e2e库" in ids, ",".join(ids))

    print("\n[2] 导入本地文件（自动识别）")
    code, body = req(
        "POST",
        "/api/knowledge/import/files",
        {
            "kb": "e2e库",
            "files": [
                {"filename": "install-guide.md", "content": "# 安装\n运行 pip install loom 完成安装"},
                {"filename": "notes.txt", "content": "备份使用 rsync 同步数据"},
                {"filename": "logo.png", "content": "not-really-png"},
            ],
        },
    )
    ok(
        "批量导入 2 跳过 1",
        code == 200 and body.get("count") == 2 and len(body.get("skipped") or []) == 1,
        json.dumps(body, ensure_ascii=False)[:120],
    )
    kinds = {i.get("kind") for i in body.get("imported") or []}
    ok("扩展名识别 markdown/text", "markdown" in kinds and "text" in kinds, str(kinds))

    print("\n[3] 路径导入")
    tmp = ROOT / "plugins" / "_e2e_wiki"
    tmp.mkdir(exist_ok=True)
    (tmp / "deploy.md").write_text("使用 docker compose up hub 启动服务", encoding="utf-8")
    code, body = req("POST", "/api/knowledge/import/path", {"path": str(tmp), "kb": "e2e库", "max_files": 10})
    ok(
        "路径扫描入库",
        code == 200 and len(body.get("imported") or []) >= 1,
        f"imported={len(body.get('imported') or [])} skipped={len(body.get('skipped') or [])}",
    )

    print("\n[4] 添加知识 + 列表")
    code, body = req(
        "POST",
        "/api/knowledge/docs",
        {"title": "卸载步骤", "content": "pip uninstall loom 即可卸载", "tags": ["运维"], "kb": "e2e库"},
    )
    ok("手工添加知识", code == 200 and body.get("item", {}).get("id"))
    code, body = req("GET", "/api/knowledge/docs?kb=e2e库")
    docs = body.get("items") or []
    ok("本地文档列表", code == 200 and len(docs) >= 4, f"count={len(docs)}")
    ok("列表含导入文件", any("install" in (d.get("title") or "") for d in docs) or any("安装" in (d.get("title") or "") for d in docs))

    print("\n[5] 本地检索")
    code, body = req("POST", "/api/knowledge/search", {"query": "怎么安装", "kb": "e2e库", "limit": 5})
    hits = body.get("hits") or []
    ok("检索命中安装", code == 200 and len(hits) >= 1, f"hits={len(hits)}")
    code, body = req("POST", "/api/knowledge/search", {"query": "怎么部署", "kb": "e2e库", "limit": 5})
    ok("检索命中部署", code == 200 and len(body.get("hits") or []) >= 1, f"hits={len(body.get('hits') or [])}")

    print("\n[6] 外部源自动识别")
    code, body = req("POST", "/api/knowledge/sources/detect", {"url": "https://acme.notion.so/wiki"})
    ok("识别 Notion 链接", code == 200 and body.get("kind") == "notion", str(body.get("kind")))
    code, body = req("POST", "/api/knowledge/sources/detect", {"url": "https://docs.acme.com"})
    ok("识别文档站链接", code == 200 and body.get("kind") == "docs", str(body.get("kind")))

    code, body = req(
        "POST",
        "/api/knowledge/sources",
        {"id": "e2e-vec", "kind": "auto", "name": "E2E 向量演示"},
    )
    ok(
        "添加 vector 源(auto)",
        code == 200 and body.get("detectedKind") == "vector",
        f"detected={body.get('detectedKind')}",
    )
    code, body = req(
        "POST",
        "/api/knowledge/sources",
        {"id": "e2e-docs", "kind": "auto", "endpoint": "https://docs.example.com", "name": "文档站"},
    )
    ok("粘贴 URL → docs", code == 200 and body.get("detectedKind") == "docs", str(body.get("detectedKind")))

    code, body = req("GET", "/api/knowledge/sources")
    srcs = body.get("items") or []
    ok("外部源列表", code == 200 and len(srcs) >= 2, f"count={len(srcs)}")
    ok("health 已附带", all("health" in s for s in srcs))

    code, body = req("POST", "/api/knowledge/sources/test", {"id": "e2e-vec", "kind": "vector"})
    ok("测试 vector 源", code == 200 and body.get("ok") is True, json.dumps(body, ensure_ascii=False)[:100])

    print("\n[7] 联邦检索（local + 外部源）")
    code, body = req("POST", "/api/knowledge/federated/search", {"query": "怎么安装 loom"})
    ok("联邦检索有命中", code == 200 and body.get("hits", 0) >= 1, f"hits={body.get('hits')}")
    ok("联邦检索有引用", code == 200 and len(body.get("citations") or []) >= 1)
    # 换库再搜部署
    code, body = req("POST", "/api/knowledge/federated/search", {"query": "docker compose 启动"})
    ok("联邦检索部署", code == 200 and body.get("hits", 0) >= 1, f"hits={body.get('hits')}")

    print("\n[8] builtin_rag 链路（Hub Agent）")
    # 若 Hub 已把 federated.answer 接到 builtin_rag，可经 chat/stream 触发；此处直接对比 API 结果结构
    code, body = req("POST", "/api/knowledge/federated/search", {"query": "如何卸载"})
    summary = (body.get("summary") or "")
    ok("answer 含 summary/citations", code == 200 and summary and "citations" in body)

    print("\n[9] 清理")
    code, body = req("DELETE", "/api/knowledge/sources/e2e-vec")
    ok("删除外部源", code == 200 and body.get("ok") is True)
    code, body = req("DELETE", "/api/knowledge/sources/e2e-docs")
    ok("删除文档站源", code == 200)
    for d in docs:
        req("DELETE", f"/api/knowledge/docs/{d['id']}")
    code, body = req("GET", "/api/knowledge/docs?kb=e2e库")
    ok("文档已清空", code == 200 and len(body.get("items") or []) == 0, f"left={len(body.get('items') or [])}")

    for p in tmp.glob("*"):
        p.unlink()
    tmp.rmdir()

    print("\n========== E2E SUMMARY ==========")
    print(f"PASS {PASS}  FAIL {FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
