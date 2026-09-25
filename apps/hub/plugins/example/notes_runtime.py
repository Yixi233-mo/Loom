"""Notes 示例插件运行时 — notes.list / notes.create / notes.daily_report。"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class NotesStore:
    """最小内存笔记存储（示例插件用）。"""

    def __init__(self) -> None:
        self._notes: List[Dict[str, Any]] = []

    def create(self, title: str, content: str = "") -> Dict[str, Any]:
        note = {
            "id": f"n{len(self._notes) + 1}",
            "title": title,
            "content": content,
            "created_at": time.time(),
        }
        self._notes.append(note)
        return note

    def list_notes(self) -> List[Dict[str, Any]]:
        return list(self._notes)


def make_notes_tools(store: Optional[NotesStore] = None) -> Dict[str, Any]:
    """返回 tool_name → callable(**kwargs) 映射，供 Workflow 执行器调用。"""
    st = store or NotesStore()

    def notes_list(**_: Any) -> Dict[str, Any]:
        items = st.list_notes()
        return {"notes": items, "count": len(items)}

    def notes_create(**kwargs: Any) -> Dict[str, Any]:
        title = kwargs.get("title") or "无标题"
        content = kwargs.get("content") or ""
        note = st.create(str(title), str(content))
        return {"created": note}

    def notes_daily_report(**_: Any) -> Dict[str, Any]:
        items = st.list_notes()
        lines = [f"- {n['title']}: {n.get('content', '')}" for n in items]
        return {
            "report": "今日笔记日报\n" + ("\n".join(lines) if lines else "（无笔记）"),
            "count": len(items),
        }

    return {
        "notes.list": notes_list,
        "notes.create": notes_create,
        "notes.daily_report": notes_daily_report,
    }
