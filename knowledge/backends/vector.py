"""向量库后端 — 远程 endpoint 未接通时用哈希演示嵌入，可对共享 store 检索。"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from knowledge.backends.base import BackendHit, BaseBackend


def _hash_vec(text: str, dim: int) -> List[float]:
    vec = [0.0] * dim
    for i, ch in enumerate(text.lower()):
        vec[(ord(ch) + i * 17) % dim] += 1.0
    norm = sum(v * v for v in vec) ** 0.5 or 1.0
    return [v / norm for v in vec]


def _score(a: List[float], b: List[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class VectorBackend(BaseBackend):
    kind = "vector"

    def __init__(
        self,
        id: str = "vector",
        dim: int = 256,
        path: Optional[str] = None,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        store: Any = None,
        **_kw: Any,
    ) -> None:
        self.id = id or "vector"
        self.dim = max(8, int(dim or 256))
        self.path = path
        self.endpoint = endpoint
        self.api_key = api_key
        self.store = store

    def search(self, query: str, limit: int = 5) -> List[BackendHit]:
        if not self.store or not query.strip():
            return []
        qv = _hash_vec(query, self.dim)
        scored: List[BackendHit] = []
        for doc in getattr(self.store, "docs", []) or []:
            text = f"{doc.title} {doc.content} {' '.join(doc.tags)}"
            s = _score(qv, _hash_vec(text, self.dim))
            if s <= 0:
                continue
            snippet = (doc.content or "")[:80]
            scored.append(
                BackendHit(
                    id=doc.id,
                    title=doc.title,
                    snippet=snippet,
                    score=round(float(s) * 10, 3),
                    source="vector",
                    meta={"kb": doc.kb},
                )
            )
        scored.sort(key=lambda h: -h.score)
        return scored[:limit]

    def health(self) -> Dict[str, Any]:
        ok = bool(self.endpoint or self.store)
        return {
            "id": self.id,
            "kind": self.kind,
            "ok": ok,
            "dim": self.dim,
            "mode": "endpoint" if self.endpoint else "hash-demo",
            "docs": len(getattr(self.store, "docs", []) or []),
        }
