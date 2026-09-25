"""SSE 流式契约（N16 6.4）— delta / final 事件。"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator, Dict, List, Optional, Union

from fastapi import APIRouter, FastAPI
from fastapi.responses import StreamingResponse


def iso_now() -> str:
    """6.9 ISO 8601 含时区（UTC）。"""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def iso_ts(ts: Optional[float] = None) -> str:
    t = ts if ts is not None else time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(t)) + "Z"


async def sse_events(
    chunks: Union[AsyncIterator[str], List[str]],
    *,
    final_payload: Optional[Dict[str, Any]] = None,
) -> AsyncIterator[str]:
    """产出 `event: delta|final` + `data: json`。"""
    if isinstance(chunks, list):

        async def _gen() -> AsyncIterator[str]:
            for c in chunks:
                yield c

        stream: AsyncIterator[str] = _gen()
    else:
        stream = chunks

    async for text in stream:
        payload = {"type": "delta", "text": text, "ts": iso_now()}
        yield f"event: delta\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        await asyncio.sleep(0)
    done = {"type": "final", "ts": iso_now(), **(final_payload or {})}
    yield f"event: final\ndata: {json.dumps(done, ensure_ascii=False)}\n\n"


def create_stream_router() -> APIRouter:
    router = APIRouter(prefix="/api/stream")

    @router.get("/chat")
    async def chat_stream(q: str = "ping"):
        """示例流式：回声分片 + final。"""
        text = q or "ping"
        parts = [text[i : i + 8] for i in range(0, max(1, len(text)), 8)] or ["ping"]
        return StreamingResponse(
            sse_events(
                parts,
                final_payload={"ok": True, "trace_id": f"tr-stream-{int(time.time())}"},
            ),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return router


def mount_stream_api(app: FastAPI) -> None:
    app.include_router(create_stream_router())
