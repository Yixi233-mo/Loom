"""知识导入识别 — 本地文件 / 路径 / 链接 → 自动识别类型并入库。"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# 扩展名 → (类型标签, 是否可读为文本)
EXT_MAP: Dict[str, Tuple[str, bool]] = {
    ".md": ("markdown", True),
    ".markdown": ("markdown", True),
    ".txt": ("text", True),
    ".log": ("text", True),
    ".json": ("json", True),
    ".yaml": ("yaml", True),
    ".yml": ("yaml", True),
    ".toml": ("toml", True),
    ".ini": ("text", True),
    ".cfg": ("text", True),
    ".csv": ("csv", True),
    ".tsv": ("csv", True),
    ".html": ("html", True),
    ".htm": ("html", True),
    ".xml": ("xml", True),
    ".py": ("code", True),
    ".ts": ("code", True),
    ".js": ("code", True),
    ".tsx": ("code", True),
    ".jsx": ("code", True),
    ".go": ("code", True),
    ".rs": ("code", True),
    ".java": ("code", True),
    ".sh": ("code", True),
    ".ps1": ("code", True),
    ".sql": ("code", True),
    ".pdf": ("pdf", False),
    ".docx": ("docx", False),
    ".doc": ("doc", False),
    ".png": ("image", False),
    ".jpg": ("image", False),
    ".jpeg": ("image", False),
    ".webp": ("image", False),
    ".gif": ("image", False),
}

_TEXT_LIMIT = 200_000


def guess_kind(filename: str) -> Tuple[str, bool]:
    """返回 (类型标签, 是否可直接读成文本)。"""
    ext = Path(filename or "").suffix.lower()
    return EXT_MAP.get(ext, ("unknown", True))


def _strip_html(html: str) -> str:
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text(filename: str, content: str) -> str:
    """按类型抽取正文（纯文本/代码直接用；HTML 去标签）。"""
    kind, _ = guess_kind(filename)
    raw = content or ""
    if kind == "html":
        return _strip_html(raw)[:_TEXT_LIMIT]
    return raw[:_TEXT_LIMIT]


def auto_tags(filename: str, kind: str) -> List[str]:
    tags = {kind} if kind and kind != "unknown" else set()
    stem = Path(filename or "").stem.lower()
    for word in re.split(r"[_\-\s.]+", stem):
        if 2 <= len(word) <= 16 and word.isalpha():
            tags.add(word)
    return sorted(tags)[:8]


def detect_source_kind(url_or_path: str) -> Optional[str]:
    """从链接/路径猜外部源类型：notion / docs / vector / local。"""
    s = (url_or_path or "").strip()
    if not s:
        return None
    low = s.lower()
    if "notion.so" in low or "notion.site" in low:
        return "notion"
    if low.startswith(("http://", "https://")):
        return "docs"
    if low.startswith(("file://",)) or re.match(r"^[a-zA-Z]:[\\/]", s) or s.startswith("\\\\"):
        return "local"
    if (
        any(x in low for x in ("vector", "embedding", "qdrant", "chroma", "milvus", "faiss"))
        or re.search(r"\bvec\b|vec[-_]", low)
    ):
        return "vector"
    return None


def import_file(
    store: Any,
    *,
    filename: str,
    content: str = "",
    kb: str = "builtin",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """单文件入库。返回 {id, title, kind, tags, skipped?}。"""
    kind, is_text = guess_kind(filename)
    name = Path(filename or "未命名").name
    if not is_text:
        return {
            "id": None,
            "title": name,
            "kind": kind,
            "tags": [],
            "skipped": True,
            "reason": f"{kind} 暂不支持正文抽取",
        }
    text = extract_text(filename, content)
    if not text.strip():
        return {
            "id": None,
            "title": name,
            "kind": kind,
            "tags": [],
            "skipped": True,
            "reason": "内容为空",
        }
    doc_title = (title or Path(name).stem or name).strip()
    doc = store.add(
        title=doc_title,
        content=text,
        tags=auto_tags(name, kind),
        source="import",
        kb=kb or "builtin",
    )
    return {
        "id": doc.id,
        "title": doc.title,
        "kind": kind,
        "tags": doc.tags,
        "skipped": False,
    }


def import_path(
    store: Any,
    *,
    path: str,
    kb: str = "builtin",
    max_files: int = 50,
    max_depth: int = 3,
) -> Dict[str, Any]:
    """扫描本地目录并导入可读文本文件。"""
    root = Path(path or "").expanduser()
    if not root.exists():
        raise FileNotFoundError(f"路径不存在: {path}")
    files: List[Path] = []
    if root.is_file():
        files = [root]
    else:
        for p in root.rglob("*"):
            if not p.is_file():
                continue
            try:
                rel = p.relative_to(root)
            except ValueError:
                continue
            if len(rel.parts) - 1 > max_depth:
                continue
            if any(part.startswith(".") for part in rel.parts):
                continue
            files.append(p)
            if len(files) >= max_files:
                break

    imported: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for p in files:
        try:
            raw = p.read_bytes()
        except Exception as e:
            skipped.append({"title": p.name, "reason": str(e)})
            continue
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = raw.decode("gbk")
            except Exception:
                kind, is_text = guess_kind(p.name)
                skipped.append({"title": p.name, "kind": kind, "reason": "非文本或编码不支持"})
                continue
        item = import_file(store, filename=p.name, content=content, kb=kb)
        if item.get("skipped"):
            skipped.append(item)
        else:
            imported.append(item)

    return {
        "imported": imported,
        "skipped": skipped,
        "total": len(imported) + len(skipped),
    }
