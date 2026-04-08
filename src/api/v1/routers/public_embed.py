"""Public embed / widget API and webhook inbox (SaaS §24, Phase 1e)."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import get_session
from src.application.services.embed_public_ai_service import run_embed_public_assistant_turn
from src.application.services.organization_embed_service import (
    get_embed_settings_by_route_token,
    record_embed_inbound_idempotency,
    resolve_embed_api_key_from_request,
    verify_embed_webhook_hmac_if_present,
    verify_webhook_bearer_and_org,
)
from src.application.services.organization_entitlement_access import (
    ensure_org_entitlement_keys_for_public_client,
)
from src.application.services.organization_rag_kb_service import (
    get_rag_kb_search_mode_label,
    search_documents_for_org,
)
from src.core.config import settings
from src.core.metrics import (
    embed_public_request_total,
    embed_rag_search_duration_seconds,
    embed_rag_search_outcomes_total,
)
from src.core.request_ip import client_ip_for_public_rate_limit
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

router = APIRouter(prefix="/public/embed/v1", tags=["public-embed"])

# 1c-Q4: явные схемы успеха + пример доменного 400 для OpenAPI (/openapi.json).
_OPENAPI_EMBED_ASSISTANT_400: dict[int | str, dict] = {
    400: {
        "description": "Превышен лимит токенов на входе (`embed_ai_input_too_long`).",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ApiHttpErrorBody"},
                "example": {
                    "detail": "Текст слишком длинный для публичного ассистента",
                    "code": "embed_ai_input_too_long",
                    "details": {
                        "tokens_estimated_input": 12000,
                        "max_input_tokens": 4096,
                    },
                },
            }
        },
    },
}

def _openapi_embed_403_entitlement(*, keys: list[str]) -> dict[int | str, dict]:
    return {
        403: {
            "description": "Нет опции тарифа для организации (`entitlement_required`).",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ApiHttpErrorBody"},
                    "example": {
                        "detail": "Требуется активная опция тарифа для этой организации.",
                        "code": "entitlement_required",
                        "details": {"keys": keys},
                    },
                }
            },
        },
    }


_OPENAPI_EMBED_403_ASSISTANT = _openapi_embed_403_entitlement(keys=["ai.assistant.chat"])
_OPENAPI_EMBED_403_RAG = _openapi_embed_403_entitlement(keys=["ai.rag.org_kb"])


def _embed_public_metric_result(exc: HTTPException) -> str:
    """Low-cardinality labels for Prometheus."""
    code = exc.status_code
    if code == status.HTTP_429_TOO_MANY_REQUESTS:
        return "rate_limited"
    if code == status.HTTP_413_CONTENT_TOO_LARGE:
        return "payload_too_large"
    if code == status.HTTP_409_CONFLICT:
        return "conflict"
    if code == status.HTTP_404_NOT_FOUND:
        return "not_found"
    if code == status.HTTP_401_UNAUTHORIZED:
        return "unauthorized"
    if code == status.HTTP_400_BAD_REQUEST:
        return "bad_request"
    if code >= 500:
        return "server_error"
    return "client_error"


async def _embed_public_ip_rate_limit(request: Request, rate_limiter: RateLimiter) -> None:
    if settings.rate_embed_public_ip_limit <= 0:
        return
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:embed_public:ip:{client_ip}",
            limit=settings.rate_embed_public_ip_limit,
            window=settings.rate_embed_public_ip_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Слишком много запросов"},
        ) from None


async def _embed_rag_search_ip_rate_limit(request: Request, rate_limiter: RateLimiter) -> None:
    """
    RAG search: общий лимит embed public + опционально отдельный bucket (§24.3 хвост эпика).

    При rate_embed_rag_search_ip_limit > 0 второй счётчик сужает частоту именно POST /rag/search.
    """
    await _embed_public_ip_rate_limit(request, rate_limiter)
    lim = settings.rate_embed_rag_search_ip_limit
    if lim <= 0:
        return
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:embed_rag_search:ip:{client_ip}",
            limit=lim,
            window=settings.rate_embed_rag_search_ip_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Слишком много запросов"},
        ) from None


async def _embed_session_ip_rate_limit(request: Request, rate_limiter: RateLimiter) -> None:
    """Session: отдельный лимит по IP при rate_embed_session_ip_limit > 0, иначе общий embed public."""
    lim = settings.rate_embed_session_ip_limit
    if lim <= 0:
        await _embed_public_ip_rate_limit(request, rate_limiter)
        return
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    try:
        await rate_limiter.check_or_raise(
            key=f"rate:embed_session:ip:{client_ip}",
            limit=lim,
            window=settings.rate_embed_session_ip_window_seconds,
        )
    except RateLimitExceeded:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Слишком много запросов"},
        ) from None


@router.get("/health")
async def embed_health(
    request: Request,
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict[str, str]:
    try:
        await _embed_public_ip_rate_limit(request, rate_limiter)
        embed_public_request_total.labels(endpoint="health", result="ok").inc()
        return {"status": "ok"}
    except HTTPException as e:
        embed_public_request_total.labels(endpoint="health", result=_embed_public_metric_result(e)).inc()
        raise


class EmbedSessionResponse(BaseModel):
    status: str
    organization_id: str
    api_key_id: str


@router.get("/session", response_model=EmbedSessionResponse)
async def embed_session(
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> EmbedSessionResponse:
    try:
        await _embed_session_ip_rate_limit(request, rate_limiter)
        auth = request.headers.get("Authorization")
        org_id, key_row = await resolve_embed_api_key_from_request(session, auth)
        await session.commit()
        embed_public_request_total.labels(endpoint="session", result="ok").inc()
        return EmbedSessionResponse(
            status="ok",
            organization_id=str(org_id),
            api_key_id=str(key_row.id),
        )
    except HTTPException as e:
        embed_public_request_total.labels(endpoint="session", result=_embed_public_metric_result(e)).inc()
        raise


def _reject_webhook_payload_too_large() -> None:
    raise HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail={
            "code": "embed_webhook_payload_too_large",
            "message": "Тело запроса превышает embed_webhook_max_body_bytes",
        },
    )


async def _read_request_body_with_cap(request: Request, max_bytes: int) -> bytes:
    """
    Read body with hard cap (1e-F7): защита при отсутствии/обмане Content-Length — не читать безлимитно.
    """
    cl = request.headers.get("content-length")
    if cl:
        try:
            declared = int(cl.strip())
        except ValueError:
            declared = -1
        if declared > max_bytes:
            _reject_webhook_payload_too_large()
    buf = bytearray()
    async for chunk in request.stream():
        buf.extend(chunk)
        if len(buf) > max_bytes:
            _reject_webhook_payload_too_large()
    return bytes(buf)


@router.post("/hooks/{inbound_route_token}/inbox")
async def embed_webhook_inbox(
    inbound_route_token: uuid.UUID,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict[str, Any]:
    endpoint = "webhook_inbox"
    try:
        await _embed_public_ip_rate_limit(request, rate_limiter)
        if settings.rate_embed_webhook_token_ip_limit > 0:
            client_ip = client_ip_for_public_rate_limit(
                request,
                trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
            )
            try:
                await rate_limiter.check_or_raise(
                    key=f"rate:embed_webhook:{inbound_route_token}:ip:{client_ip}",
                    limit=settings.rate_embed_webhook_token_ip_limit,
                    window=settings.rate_embed_webhook_token_ip_window_seconds,
                )
            except RateLimitExceeded:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={"code": "rate_limited", "message": "Слишком много запросов"},
                ) from None

        settings_row = await get_embed_settings_by_route_token(session, inbound_route_token)
        if settings_row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "embed_route_unknown", "message": "Неизвестный inbound_route_token"},
            )

        auth = request.headers.get("Authorization")
        org_id, bearer_plain = await verify_webhook_bearer_and_org(session, settings_row, auth)

        max_b = settings.embed_webhook_max_body_bytes
        body_bytes = await _read_request_body_with_cap(request, max_b)

        body_sha = hashlib.sha256(body_bytes).hexdigest()

        verify_embed_webhook_hmac_if_present(
            body_bytes,
            bearer_plain,
            request.headers.get("X-Embed-Signature"),
            signature_required=settings.embed_webhook_signature_required,
        )

        idem = request.headers.get("X-Embed-Idempotency-Key") or request.headers.get("Idempotency-Key")
        is_new, is_dup = await record_embed_inbound_idempotency(session, org_id, idem, body_sha)
        idem_active = bool(idem and idem.strip())

        try:
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else None
        except (json.JSONDecodeError, UnicodeDecodeError):
            body = None

        payload_type = (
            "empty"
            if not body_bytes
            else ("json" if isinstance(body, (dict, list)) else "non_json")
        )

        await session.commit()
        embed_public_request_total.labels(endpoint=endpoint, result="ok").inc()
        return {
            "received": True,
            "duplicate": is_dup,
            "idempotency_recorded": idem_active and is_new and not is_dup,
            "organization_id": str(org_id),
            "payload_type": payload_type,
        }
    except HTTPException as e:
        embed_public_request_total.labels(endpoint=endpoint, result=_embed_public_metric_result(e)).inc()
        raise


class EmbedAssistantMessageBody(BaseModel):
    message: str = Field(..., min_length=1, max_length=32_000)

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"message": "Запишите меня на гигиену на завтра"}]},
    )


class EmbedAssistantMessageResponse(BaseModel):
    organization_id: str
    reply: str
    mode: str = Field(
        ...,
        description="Режим ответа: llm, echo_no_provider, provider_error, empty",
    )
    tokens_estimated_input: int
    provider_called: bool

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
                    "reply": "Добрый день! Могу подсказать по записи.",
                    "mode": "llm",
                    "tokens_estimated_input": 24,
                    "provider_called": True,
                }
            ]
        },
    )


@router.post(
    "/assistant/message",
    response_model=EmbedAssistantMessageResponse,
    summary="Публичный ассистент (embed)",
    responses={**_OPENAPI_EMBED_ASSISTANT_400, **_OPENAPI_EMBED_403_ASSISTANT},
)
async def embed_public_assistant_message(
    body: EmbedAssistantMessageBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict[str, Any]:
    endpoint = "assistant_message"
    try:
        await _embed_public_ip_rate_limit(request, rate_limiter)
        auth = request.headers.get("Authorization")
        org_id, _key_row = await resolve_embed_api_key_from_request(session, auth)
        await ensure_org_entitlement_keys_for_public_client(session, org_id, "ai.assistant.chat")
        result = await run_embed_public_assistant_turn(session, org_id, body.message)
        if result.get("mode") == "input_too_long":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "embed_ai_input_too_long",
                    "message": "Текст слишком длинный для публичного ассистента",
                    "tokens_estimated_input": result.get("tokens_estimated_input"),
                    "max_input_tokens": result.get("max_input_tokens"),
                },
            )
        await session.commit()
        embed_public_request_total.labels(endpoint=endpoint, result="ok").inc()
        return {"organization_id": str(org_id), **result}
    except HTTPException as e:
        embed_public_request_total.labels(endpoint=endpoint, result=_embed_public_metric_result(e)).inc()
        raise


class EmbedRagSearchBody(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"query": "гарантия на имплант"}]},
    )


class EmbedRagSearchItem(BaseModel):
    id: str
    title: str
    snippet: str = Field(..., description="Фрагмент текста документа (до ~400 символов)")


class EmbedRagSearchResponse(BaseModel):
    organization_id: str
    items: list[EmbedRagSearchItem]

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "organization_id": "550e8400-e29b-41d4-a716-446655440000",
                    "items": [
                        {
                            "id": "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
                            "title": "Гарантия",
                            "snippet": "Гарантийный срок на имплант …",
                        }
                    ],
                }
            ]
        },
    )


@router.post(
    "/rag/search",
    response_model=EmbedRagSearchResponse,
    summary="Поиск по организационному KB (RAG v1)",
    responses=_OPENAPI_EMBED_403_RAG,
)
async def embed_public_rag_search(
    body: EmbedRagSearchBody,
    request: Request,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> dict[str, Any]:
    """
    §24.3: поиск только в KB текущей организации.

    `organization_id` для фильтрации берётся из валидного embed-ключа (см.
    `resolve_embed_api_key_from_request`), а не из тела запроса — граница
    арендатора не задаётся клиентом.
    """
    endpoint = "rag_search"
    try:
        await _embed_rag_search_ip_rate_limit(request, rate_limiter)
        auth = request.headers.get("Authorization")
        org_id, _key_row = await resolve_embed_api_key_from_request(session, auth)
        await ensure_org_entitlement_keys_for_public_client(session, org_id, "ai.rag.org_kb")
        mode_lbl = get_rag_kb_search_mode_label()
        t0 = time.perf_counter()
        try:
            hits = await search_documents_for_org(session, org_id, body.query, limit=8)
        except Exception:
            embed_rag_search_duration_seconds.labels(search_mode=mode_lbl).observe(
                time.perf_counter() - t0
            )
            embed_rag_search_outcomes_total.labels(outcome="db_error", search_mode=mode_lbl).inc()
            raise
        embed_rag_search_duration_seconds.labels(search_mode=mode_lbl).observe(time.perf_counter() - t0)
        embed_rag_search_outcomes_total.labels(
            outcome="empty" if not hits else "hits",
            search_mode=mode_lbl,
        ).inc()
        await session.commit()
        embed_public_request_total.labels(endpoint=endpoint, result="ok").inc()
        return {
            "organization_id": str(org_id),
            "items": [
                {"id": str(d.id), "title": d.title, "snippet": (d.body[:400] + "…") if len(d.body) > 400 else d.body}
                for d in hits
            ],
        }
    except HTTPException as e:
        embed_public_request_total.labels(endpoint=endpoint, result=_embed_public_metric_result(e)).inc()
        raise
