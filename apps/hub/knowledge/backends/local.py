"""本地知识库后端 — 包装 KnowledgeStore。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from knowledge.backends.base import BackendHit, BaseBackend
from knowledge.store import KnowledgeStore


class LocalBackend(BaseBackend):
    kind = "local"

    def __init__(self, id: str = "local", store: Optional[KnowledgeStore] = None) -> None:
        self.id = id
        self.store = store or KnowledgeStore("plugins/knowledge.json")

    def search(self, query: str, limit: int = 5) -> List[BackendHit]:
        hits = self.store.search(query, limit=limit)
        return [
            BackendHit(
                id=h.doc.id,
                title=h.doc.title,
                snippet=h.snippet,
                score=float(h.score),
                source="local",
                meta={"kb": h.doc.kb, "tags": h.doc.tags},
            )
            for h in hits
        ]

    def health(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "ok": True,
            "docs": len(self.store.docs),
        }
