"""本地知识库 — JSON 存储 + 关键词检索（可被 builtin_rag / 外部 KB 复用）。

支持多库（knowledge base）：
  - builtin：内置默认库
  - 可扩展其它库 id（前端「新建知识库」）
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class KnowledgeDoc:
    id: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    source: str = "manual"  # manual | file | import
    kb: str = "builtin"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class SearchHit:
    doc: KnowledgeDoc
    score: int
    snippet: str


_TOKEN_RE = re.compile(r"[\w一-鿿]+")


def _tokens(text: str) -> List[str]:
    """中英文混合分词：英文整词 + 中文双字滑窗，保证「部署」能命中「部署流程」。"""
    out: List[str] = []
    for t in _TOKEN_RE.findall(text or ""):
        low = t.lower()
        if not low.strip():
            continue
        if _TOKEN_RE_CJK.search(low):
            out.append(low)
            # 中文按 2-gram 拆，便于部分匹配
            if len(low) >= 2:
                out.extend(low[i : i + 2] for i in range(len(low) - 1))
        else:
            out.append(low)
    return out


_TOKEN_RE_CJK = re.compile(r"[\u4e00-\u9fff]")


class KnowledgeStore:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self.docs: List[KnowledgeDoc] = []
        self.kbs: Dict[str, str] = {"builtin": "内置知识库"}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        self.kbs = raw.get("kbs") or {"builtin": "内置知识库"}
        for row in raw.get("docs") or []:
            try:
                self.docs.append(
                    KnowledgeDoc(
                        id=row["id"],
                        title=row["title"],
                        content=row["content"],
                        tags=list(row.get("tags") or []),
                        source=row.get("source") or "manual",
                        kb=row.get("kb") or "builtin",
                        created_at=float(row.get("created_at") or time.time()),
                        updated_at=float(row.get("updated_at") or time.time()),
                    )
                )
            except Exception:
                continue

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "kbs": self.kbs,
            "docs": [asdict(d) for d in self.docs],
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def list_kbs(self) -> List[Dict[str, object]]:
        out = []
        for kb_id, name in self.kbs.items():
            out.append(
                {
                    "id": kb_id,
                    "name": name,
                    "count": sum(1 for d in self.docs if d.kb == kb_id),
                }
            )
        return out

    def ensure_kb(self, kb_id: str, name: Optional[str] = None) -> None:
        if kb_id not in self.kbs:
            self.kbs[kb_id] = name or kb_id
            self.save()

    def list_docs(self, kb: Optional[str] = None) -> List[KnowledgeDoc]:
        items = [d for d in self.docs if kb is None or d.kb == kb]
        return sorted(items, key=lambda d: d.updated_at, reverse=True)

    def get(self, doc_id: str) -> Optional[KnowledgeDoc]:
        for d in self.docs:
            if d.id == doc_id:
                return d
        return None

    def add(
        self,
        title: str,
        content: str,
        tags: Optional[List[str]] = None,
        source: str = "manual",
        kb: str = "builtin",
    ) -> KnowledgeDoc:
        self.ensure_kb(kb)
        doc = KnowledgeDoc(
            id="kb-" + uuid.uuid4().hex[:12],
            title=title.strip() or "未命名",
            content=content or "",
            tags=[t.strip() for t in (tags or []) if t.strip()],
            source=source,
            kb=kb,
        )
        self.docs.append(doc)
        self.save()
        return doc

    def remove(self, doc_id: str) -> bool:
        before = len(self.docs)
        self.docs = [d for d in self.docs if d.id != doc_id]
        if len(self.docs) != before:
            self.save()
            return True
        return False

    def search(self, query: str, kb: Optional[str] = None, limit: int = 5) -> List[SearchHit]:
        q_tokens = set(_tokens(query))
        if not q_tokens:
            return []
        hits: List[SearchHit] = []
        for doc in self.docs:
            if kb and doc.kb != kb:
                continue
            title_t = set(_tokens(doc.title))
            body_t = set(_tokens(doc.content))
            tag_t = set(_tokens(" ".join(doc.tags)))
            score = (
                3 * len(q_tokens & title_t)
                + 2 * len(q_tokens & tag_t)
                + len(q_tokens & body_t)
            )
            if score <= 0:
                continue
            hits.append(
                SearchHit(doc=doc, score=score, snippet=_snippet(doc.content, query))
            )
        hits.sort(key=lambda h: (-h.score, -h.doc.updated_at))
        return hits[:limit]


def _snippet(content: str, query: str, width: int = 80) -> str:
    text = content or ""
    q_tokens = _tokens(query)
    low = text.lower()
    idx = -1
    for t in q_tokens:
        idx = low.find(t)
        if idx >= 0:
            break
    if idx < 0:
        return text[:width] + ("…" if len(text) > width else "")
    start = max(0, idx - 20)
    end = min(len(text), start + width)
    prefix = "…" if start > 0 else ""
    suffix = "…" if end < len(text) else ""
    return prefix + text[start:end] + suffix


def answer_from_kb(store: KnowledgeStore, prompt: str, kb: Optional[str] = None) -> Dict[str, object]:
    """builtin_rag：检索知识库并给出摘要式回答（引用条目）。"""
    hits = store.search(prompt, kb=kb, limit=5)
    if not hits:
        return {
            "summary": "知识库中没有找到相关内容。可在「知识库」页添加资料后再问。",
            "citations": [],
            "hits": 0,
        }
    parts = []
    citations = []
    for i, h in enumerate(hits, 1):
        parts.append(f"[{i}] {h.doc.title}：{h.snippet}")
        citations.append(
            {
                "id": h.doc.id,
                "title": h.doc.title,
                "score": h.score,
                "snippet": h.snippet,
                "kb": h.doc.kb,
            }
        )
    summary = "根据知识库检索：\n" + "\n".join(parts)
    return {"summary": summary, "citations": citations, "hits": len(hits)}
