"""HTTPException → unified JSON envelope (§28 / 1c-Q2). Kept out of ``main`` so tests need not import the full app."""

from __future__ import annotations

from enum import Enum

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from src.core.api_error_codes import (
    HTTP_EXCEPTION_STANDARD_KEYS,
    HTTP_STATUS_DEFAULT_CODES,
    normalize_api_error_code,
)


async def unified_http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Unify HTTPException into {detail, code, details?, trace_id?}; ``code`` is lowercase snake_case (1c-Q2)."""
    trace_id = getattr(request.state, "trace_id", None)

    code_normalized = ""
    msg_from_detail: str | None = None
    details_extra: dict = {}

    if isinstance(exc.detail, dict):
        raw_code = exc.detail.get("code")
        if isinstance(raw_code, Enum):
            val = raw_code.value
            if val is not None:
                s = str(val).strip()
                if s:
                    code_normalized = normalize_api_error_code(s)
        elif isinstance(raw_code, str) and raw_code.strip():
            code_normalized = normalize_api_error_code(raw_code)
        raw_msg = exc.detail.get("message")
        if isinstance(raw_msg, str) and raw_msg.strip():
            msg_from_detail = raw_msg.strip()
        else:
            inner = exc.detail.get("detail")
            if isinstance(inner, str) and inner.strip():
                msg_from_detail = inner.strip()
        for k, v in exc.detail.items():
            if k not in HTTP_EXCEPTION_STANDARD_KEYS:
                details_extra[k] = v

    code = code_normalized or HTTP_STATUS_DEFAULT_CODES.get(exc.status_code) or "http_error"

    detail_str: str
    if msg_from_detail:
        detail_str = msg_from_detail
    elif isinstance(exc.detail, str):
        detail_str = exc.detail
    else:
        detail_str = "Ошибка"

    body: dict = {"detail": detail_str, "code": code}
    if details_extra:
        body["details"] = details_extra
    effective_trace = trace_id
    if not effective_trace and isinstance(exc.detail, dict):
        dt = exc.detail.get("trace_id")
        if isinstance(dt, str) and dt.strip():
            effective_trace = dt.strip()
    if effective_trace:
        body["trace_id"] = effective_trace
    return JSONResponse(status_code=exc.status_code, content=body)
