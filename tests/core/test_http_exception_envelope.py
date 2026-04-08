"""QA_ARCH §28: contract of ``http_exception_handler`` (Enum ``code``, ``trace_id``)."""

from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.application.dto.booking_dto import BookingErrorCode
from src.core.http_exception_handler import unified_http_exception_handler


@pytest.mark.asyncio
async def test_http_exception_booking_enum_code_uses_value_not_str_repr() -> None:
    """``str(Enum)`` is qualified name; handler must emit ``.value`` (e.g. clinic_mismatch)."""
    request = MagicMock()
    request.state = MagicMock(trace_id=None)
    exc = HTTPException(
        status_code=400,
        detail={
            "code": BookingErrorCode.CLINIC_MISMATCH,
            "message": "Clinic mismatch",
        },
    )
    resp = await unified_http_exception_handler(request, exc)
    assert resp.status_code == 400
    payload = resp.body.decode()
    assert '"code":"clinic_mismatch"' in payload.replace(" ", "")


@pytest.mark.asyncio
async def test_http_exception_trace_id_from_detail_when_state_empty() -> None:
    request = MagicMock()
    request.state = MagicMock(trace_id=None)
    exc = HTTPException(
        status_code=400,
        detail={"code": "x", "message": "m", "trace_id": "from-body"},
    )
    resp = await unified_http_exception_handler(request, exc)
    body = resp.body.decode()
    assert "from-body" in body
    # trace_id must not duplicate inside details
    assert body.count("from-body") == 1


@pytest.mark.asyncio
async def test_http_exception_trace_id_prefers_request_state() -> None:
    request = MagicMock()
    request.state = MagicMock(trace_id="from-header")
    exc = HTTPException(
        status_code=400,
        detail={"code": "x", "message": "m", "trace_id": "from-body"},
    )
    resp = await unified_http_exception_handler(request, exc)
    assert "from-header" in resp.body.decode()
    assert "from-body" not in resp.body.decode()
