"""REST /api/knowledge — 知识库管理与检索（前端加知识 → builtin_rag 使用）。

  GET    /api/knowledge/kbs            知识库列表
  POST   /api/knowledge/kbs            新建知识库
  GET    /api/knowledge/docs           文档列表 ?kb=
  POST   /api/knowledge/docs           添加知识
  DELETE /api/knowledge/docs/{id}      删除
  POST   /api/knowledge/search         本地检索（预览用）
  GET    /api/knowledge/sources        外部源列表（含 health）
  POST   /api/knowledge/sources        添加/更新外部源
  DELETE /api/knowledge/sources/{id}   删除外部源
  POST   /api/knowledge/sources/test   测试外部源连通
  POST   /api/knowledge/federated/search  联邦检索（local+外部源）
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from knowledge.store import KnowledgeStore
from pydantic import BaseModel, Field


class KbIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = ""


class DocIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = ""
    tags: List[str] = Field(default_factory=list)
    source: str = "manual"
    kb: str = "builtin"


class SearchIn(BaseModel):
    query: str = Field(min_length=1)
    kb: Optional[str] = None
    limit: int = 5


class SourceIn(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    kind: str = Field(default="auto", max_length=32)
    name: str = ""
    enabled: bool = True
    endpoint: Optional[str] = None
    api_key: Optional[str] = None
    token: Optional[str] = None
    workspace_url: Optional[str] = None
    database_id: Optional[str] = None
    base_url: Optional[str] = None
    entry: Optional[str] = None
    dim: int = 256
    max_pages: int = 30


class FileIn(BaseModel):
    filename: str = Field(min_length=1, max_length=256)
    content: str = ""
    title: Optional[str] = None
    kb: str = "builtin"


class PathIn(BaseModel):
    path: str = Field(min_length=1, max_length=1024)
    kb: str = "builtin"
    max_files: int = 50


def _source_conf(body: SourceIn) -> Dict[str, Any]:
    conf: Dict[str, Any] = {
        "id": body.id,
        "kind": body.kind,
        "enabled": body.enabled,
        "dim": body.dim,
        "max_pages": body.max_pages,
    }
    for key, val in (
        ("name", body.name),
        ("endpoint", body.endpoint),
        ("api_key", body.api_key),
        ("token", body.token),
        ("workspace_url", body.workspace_url),
        ("database_id", body.database_id),
        ("base_url", body.base_url),
        ("entry", body.entry),
    ):
        if val:
            conf[key] = val
    return conf


def create_knowledge_router(
    store: KnowledgeStore, sources_path: Optional[str] = None
) -> APIRouter:
    router = APIRouter(prefix="/api/knowledge")

    def _fed():
        from knowledge.federated import FederatedKnowledge

        if sources_path:
            return FederatedKnowledge(store, sources_path=sources_path)
        return FederatedKnowledge(store)

    @router.get("/kbs")
    def list_kbs() -> Dict[str, Any]:
        return {"items": store.list_kbs()}

    @router.post("/kbs")
    def create_kb(body: KbIn) -> Dict[str, Any]:
        kb_id = body.id.strip()
        if not kb_id:
            raise HTTPException(400, "知识库 ID 不能为空")
        store.ensure_kb(kb_id, body.name.strip() or kb_id)
        return {"ok": True, "items": store.list_kbs()}

    @router.get("/docs")
    def list_docs(kb: Optional[str] = None) -> Dict[str, Any]:
        docs = store.list_docs(kb)
        return {
            "items": [
                {
                    "id": d.id,
                    "title": d.title,
                    "content": d.content,
                    "tags": d.tags,
                    "source": d.source,
                    "kb": d.kb,
                    "updatedAt": d.updated_at,
                }
                for d in docs
            ]
        }

    @router.post("/docs")
    def add_doc(body: DocIn) -> Dict[str, Any]:
        if not body.title.strip():
            raise HTTPException(400, "标题不能为空")
        doc = store.add(
            title=body.title,
            content=body.content,
            tags=body.tags,
            source=body.source,
            kb=body.kb or "builtin",
        )
        return {
            "ok": True,
            "item": {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "tags": doc.tags,
                "source": doc.source,
                "kb": doc.kb,
                "updatedAt": doc.updated_at,
            },
        }

    @router.delete("/docs/{doc_id}")
    def delete_doc(doc_id: str) -> Dict[str, Any]:
        ok = store.remove(doc_id)
        if not ok:
            raise HTTPException(404, "知识条目不存在")
        return {"ok": True}

    @router.post("/search")
    def search(body: SearchIn) -> Dict[str, Any]:
        hits = store.search(body.query, kb=body.kb, limit=max(1, min(body.limit, 20)))
        return {
            "hits": [
                {
                    "id": h.doc.id,
                    "title": h.doc.title,
                    "score": h.score,
                    "snippet": h.snippet,
                    "kb": h.doc.kb,
                }
                for h in hits
            ]
        }

    @router.get("/sources")
    def list_sources() -> Dict[str, Any]:
        return {"items": _fed().list_sources()}

    @router.post("/sources")
    def add_source(body: SourceIn) -> Dict[str, Any]:
        from knowledge.importer import detect_source_kind

        kind = (body.kind or "").strip()
        if not kind or kind == "auto":
            kind = "local"
            for val in (
                body.endpoint,
                body.base_url,
                body.entry,
                body.workspace_url,
                body.id,
            ):
                if val and detect_source_kind(str(val)):
                    kind = detect_source_kind(str(val))
                    break
        conf = _source_conf(body)
        conf["kind"] = kind
        try:
            item = _fed().add_source(conf)
        except Exception as e:
            raise HTTPException(400, str(e))
        return {"ok": True, "item": item, "detectedKind": kind}

    @router.delete("/sources/{source_id}")
    def remove_source(source_id: str) -> Dict[str, Any]:
        ok = _fed().remove_source(source_id)
        if not ok:
            raise HTTPException(404, "外部源不存在")
        return {"ok": True}

    @router.post("/sources/test")
    def test_source(body: SourceIn) -> Dict[str, Any]:
        from knowledge.backends import make_backend

        conf = _source_conf(body)
        try:
            b = make_backend(conf, store=store)
            return {"ok": True, "health": b.health()}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @router.post("/federated/search")
    def federated_search(body: SearchIn) -> Dict[str, Any]:
        out = _fed().answer(body.query)
        return out

    @router.post("/import")
    def import_file(body: FileIn) -> Dict[str, Any]:
        from knowledge.importer import import_file as _imp

        try:
            item = _imp(
                store,
                filename=body.filename,
                content=body.content,
                kb=body.kb or "builtin",
                title=body.title,
            )
        except Exception as e:
            raise HTTPException(400, str(e))
        return {"ok": not item.get("skipped", False), "item": item}

    @router.post("/import/files")
    def import_files(body: Dict[str, Any]) -> Dict[str, Any]:
        from knowledge.importer import import_file as _imp

        items = body.get("files") or []
        if not isinstance(items, list) or not items:
            raise HTTPException(400, "files 不能为空")
        kb = str(body.get("kb") or "builtin")
        out = []
        for row in items[:50]:
            if not isinstance(row, dict):
                continue
            out.append(
                _imp(
                    store,
                    filename=str(row.get("filename") or "未命名"),
                    content=str(row.get("content") or ""),
                    kb=kb,
                    title=row.get("title"),
                )
            )
        imported = [i for i in out if not i.get("skipped")]
        return {"ok": True, "imported": imported, "skipped": [i for i in out if i.get("skipped")], "count": len(imported)}

    @router.post("/import/path")
    def import_path(body: PathIn) -> Dict[str, Any]:
        from knowledge.importer import import_path as _imp_path

        try:
            result = _imp_path(
                store,
                path=body.path,
                kb=body.kb or "builtin",
                max_files=max(1, min(body.max_files, 200)),
            )
        except FileNotFoundError as e:
            raise HTTPException(404, str(e))
        except Exception as e:
            raise HTTPException(400, str(e))
        return {"ok": True, **result}

    @router.post("/sources/detect")
    def detect_source(body: Dict[str, Any]) -> Dict[str, Any]:
        from knowledge.importer import detect_source_kind

        raw = str(body.get("url") or body.get("path") or body.get("value") or "")
        kind = detect_source_kind(raw)
        return {"ok": True, "kind": kind, "value": raw}

    return router


def mount_knowledge_api(
    app: Any, store: KnowledgeStore, sources_path: Optional[str] = None
) -> None:
    app.include_router(create_knowledge_router(store, sources_path=sources_path))
