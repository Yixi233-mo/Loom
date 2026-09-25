#!/usr/bin/env python3
"""知识库全链路 E2E：起 Hub → 选库/导入/检索/外部源/联邦 RAG/维护。"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("E2E_BASE", "http://127.0.0.1:8765")
KB_PATH = ROOT / "plugins" / "_e2e_kb.json"
TMP = ROOT / "plugins" / "_e2e_tmp"


def req(method: str, path: str, body=None, timeout=15):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"detail": raw}


def check(name: str, cond: bool, extra=""):
    status = "PASS" if cond else "FAIL"
    print(f"[{status}] {name}" + (f" — {extra}" if extra else ""))
    return cond


def main() -> int:
    results = []
    print("=== 知识库全链路 E2E ===")

    # 0. health
    code, health = req("GET", "/health")
    results.append(check("Hub /health", code == 200 and health.get("ok"), str(health)))

    # 1. 选库/新建库
    code, kbs = req("GET", "/api/knowledge/kbs")
    results.append(check("列出知识库", code == 200 and "items" in kbs, str(kbs)[:120]))
    code, nb = req("POST", "/api/knowledge/kbs", {"id": "产品文档", "name": "产品"})
    ids = [x["id"] for x in nb.get("items", [])]
    results.append(check("新建库", code == 200 and "产品文档" in ids, ",".join(ids)))

    kb = "产品文档"
    # 2. 添加知识
    code, doc = req(
        "POST",
        "/api/knowledge/docs",
        {"title": "部署流程", "content": "docker compose up hub 启动", "tags": ["运维"], "kb": kb},
    )
    doc_id = (doc.get("item") or {}).get("id")
    results.append(check("添加知识", code == 200 and doc_id, doc_id or str(doc)))

    # 3. 本地检索
    code, hit = req("POST", "/api/knowledge/search", {"query": "怎么部署", "kb": kb, "limit": 5})
    results.append(check("本地检索命中", code == 200 and len(hit.get("hits") or []) >= 1, str(hit)[:120]))

    # 4. 路径导入
    code, imp = req(
        "POST",
        "/api/knowledge/import/path",
        {"path": str(TMP), "kb": kb, "max_files": 10},
    )
    results.append(
        check(
            "路径导入",
            code == 200 and len(imp.get("imported") or []) >= 1,
            f"imported={len(imp.get('imported') or [])} skipped={len(imp.get('skipped') or [])}",
        )
    )

    # 5. 单文件导入
    code, one = req(
        "POST",
        "/api/knowledge/import",
        {
            "filename": "faq.md",
            "content": "如何安装 loom？先 npm install 再 npm run start",
            "kb": kb,
        },
    )
    results.append(
        check(
            "单文件导入",
            code == 200 and one.get("ok") and one.get("item", {}).get("kind") == "markdown",
            str(one)[:120],
        )
    )

    # 6. 自动识别 + 外部源
    code, det = req("POST", "/api/knowledge/sources/detect", {"url": "https://acme.notion.so/wiki"})
    results.append(check("识别 Notion 链接", code == 200 and det.get("kind") == "notion", str(det)))

    code, s1 = req("POST", "/api/knowledge/sources", {"id": "vec-demo", "kind": "auto", "name": "向量演示"})
    results.append(check("添加 vector 源(auto)", code == 200 and s1.get("detectedKind") in ("vector", "local"), str(s1)[:120]))

    code, s2 = req(
        "POST",
        "/api/knowledge/sources",
        {"id": "docs-demo", "kind": "auto", "endpoint": "https://docs.example.com"},
    )
    results.append(check("添加 docs 源(auto→docs)", code == 200 and s2.get("detectedKind") == "docs", str(s2)[:120]))

    # 7. 列表 / 测试
    code, sources = req("GET", "/api/knowledge/sources")
    results.append(
        check("外部源列表", code == 200 and len(sources.get("items") or []) >= 2, str([i.get("id") for i in sources.get("items", [])]))
    )
    code, test = req("POST", "/api/knowledge/sources/test", {"id": "vec-demo", "kind": "vector"})
    results.append(check("测试外部源", code == 200 and test.get("ok"), str(test)[:120]))

    # 8. 联邦 RAG
    code, fed = req("POST", "/api/knowledge/federated/search", {"query": "怎么部署"})
    results.append(
        check(
            "联邦 RAG 命中",
            code == 200 and fed.get("hits", 0) >= 1 and len(fed.get("citations") or []) >= 1,
            f"hits={fed.get('hits')} cites={len(fed.get('citations') or [])} summary={str(fed.get('summary'))[:80]}",
        )
    )

    # 9. 文档列表
    code, docs = req("GET", f"/api/knowledge/docs?kb={urllib.request.quote(kb)}")
    titles = [d.get("title") for d in docs.get("items") or []]
    results.append(check("本地文档列表", code == 200 and len(titles) >= 3, str(titles)))

    # 10. 删除维护
    code, d1 = req("DELETE", f"/api/knowledge/docs/{doc_id}")
    results.append(check("删除文档", code == 200 and d1.get("ok"), str(d1)))
    code, d2 = req("DELETE", "/api/knowledge/sources/docs-demo")
    results.append(check("删除外部源", code == 200 and d2.get("ok"), str(d2)))
    code, docs2 = req("GET", f"/api/knowledge/docs?kb={urllib.request.quote(kb)}")
    results.append(check("删除后列表", code == 200 and all(t != "部署流程" for t in [x.get("title") for x in docs2.get("items") or []]), str([x.get("title") for x in docs2.get("items", [])])))

    print("=== SUMMARY ===")
    ok = sum(1 for r in results if r)
    print(f"{ok}/{len(results)} PASS")
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
