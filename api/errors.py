"""S1 统一错误契约 — {code, message, trace_id}。"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from observability.security import redact_secrets

# 业务码映射（HTTP status → code）
_CODE_BY_STATUS = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    500: "INTERNAL",
    502: "UPSTREAM_ERROR",
    503: "NOT_READY",
    504: "TIMEOUT",
}


def make_error(
    status: int,
    message: str,
    code: Optional[str] = None,
    trace_id: str = "",
    **extra: Any,
) -> Dict[str, Any]:
    body = {
        "code": code or _CODE_BY_STATUS.get(status, "ERROR"),
        "message": redact_secrets(str(message)),
        "trace_id": trace_id or f"tr-{uuid.uuid4().hex[:12]}",
    }
    if extra:
        body.update(extra)
    return body


def error_response(
    status: int,
    message: str,
    code: Optional[str] = None,
    trace_id: str = "",
    **extra: Any,
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=make_error(status, message, code=code, trace_id=trace_id, **extra),
    )


def _trace_of(request: Request) -> str:
    return (
        getattr(request.state, "trace_id", "")
        or request.headers.get("x-trace-id", "")
        or f"tr-{uuid.uuid4().hex[:12]}"
    )


def install_error_contract(app: FastAPI) -> None:
    """挂载统一错误体（S1）。"""

    @app.exception_handler(HTTPException)
    async def _http_exc(request: Request, exc: HTTPException) -> JSONResponse:
        detail = exc.detail
        if isinstance(detail, dict):
            message = str(detail.get("message") or detail)
            code = detail.get("code")
        else:
            message = str(detail)
            code = None
        return error_response(
            exc.status_code,
            message,
            code=code,
            trace_id=_trace_of(request),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        return error_response(
            500,
            "内部错误，已记录日志",
            code="INTERNAL",
            trace_id=_trace_of(request),
        )
