"""知识后端协议 — 本地 / 向量库 / Notion / 文档站统一接口。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


@dataclass
class BackendHit:
    id: str
    title: str
    snippet: str
    score: float
    source: str  # local | vector | notion | docs
    url: str = ""
    meta: Dict[str, Any] = field(default_factory=dict)


class KnowledgeBackend(Protocol):
    id: str
    kind: str

    def search(self, query: str, limit: int = 5) -> List[BackendHit]:
        ...

    def health(self) -> Dict[str, Any]:
        ...


class BaseBackend:
    id = "base"
    kind = "base"

    def health(self) -> Dict[str, Any]:
        return {"id": self.id, "kind": self.kind, "ok": True}


def make_backend(conf: Dict[str, Any], store: Any = None) -> KnowledgeBackend:
    kind = (conf.get("kind") or "local").lower()
    bid = str(conf.get("id") or kind)
    if kind == "local":
        from knowledge.backends.local import LocalBackend

        return LocalBackend(id=bid, store=store)
    if kind == "vector":
        from knowledge.backends.vector import VectorBackend

        return VectorBackend(
            id=bid,
            dim=int(conf.get("dim") or 256),
            path=conf.get("path"),
            endpoint=conf.get("endpoint"),
            api_key=conf.get("api_key") or conf.get("apiKey"),
            store=store,
        )
    if kind == "notion":
        from knowledge.backends.notion import NotionBackend

        return NotionBackend(
            id=bid,
            token=conf.get("token") or conf.get("api_key"),
            database_id=conf.get("database_id") or conf.get("databaseId"),
            workspace_url=conf.get("workspace_url") or conf.get("workspaceUrl"),
        )
    if kind == "docs":
        from knowledge.backends.docs_site import DocsSiteBackend

        return DocsSiteBackend(
            id=bid,
            base_url=conf.get("base_url") or conf.get("baseUrl") or "",
            entry=conf.get("entry") or conf.get("base_url") or conf.get("baseUrl") or "",
            max_pages=int(conf.get("max_pages") or 30),
        )
    raise ValueError(f"未知知识后端类型: {kind}")
