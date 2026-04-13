"""Публичные заявки «Корпоративный» и просмотр для Основателя платформы."""

import csv
import hashlib
import io
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies import (
    PlatformFounderPrincipal,
    get_current_platform_founder,
    get_session,
)
from src.application.services.enterprise_lead_notify_service import send_enterprise_lead_created_webhook
from src.application.services.turnstile_service import verify_turnstile
from src.core.config import settings
from src.core.metrics import (
    auth_captcha_required_total,
    auth_captcha_verified_total,
    enterprise_lead_rate_limited_total,
    enterprise_lead_submitted_total,
)
from src.core.platform_audit import log_platform_audit
from src.core.request_ip import client_ip_for_public_rate_limit
from src.domain.entities.enterprise_lead import EnterpriseLead
from src.infrastructure.rate_limiter import RateLimitExceeded, RateLimiter, get_rate_limiter

EnterpriseLeadStatus = Literal["NEW", "IN_PROGRESS", "CLOSED"]
EnterpriseLeadSource = Literal["corporate", "sandbox_demo"]

public_router = APIRouter(prefix="/platform-leads", tags=["platform-leads"])
internal_router = APIRouter(prefix="/platform/internal/enterprise-leads", tags=["platform-internal"])


class EnterpriseLeadCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    phone_or_email: str = Field(..., min_length=3, max_length=320)
    lead_source: EnterpriseLeadSource = "corporate"
    #: При ``TURNSTILE_ENABLED=true`` обязателен (как на checkout).
    turnstile_token: str | None = None


class EnterpriseLeadCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    status: str
    lead_source: str


class EnterpriseLeadItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    company_name: str
    phone_or_email: str
    status: str
    lead_source: str
    created_at: str


class EnterpriseLeadPatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EnterpriseLeadStatus


def _contact_rate_fingerprint(phone_or_email: str) -> str:
    n = (phone_or_email or "").strip().lower()
    return hashlib.sha256(n.encode("utf-8")).hexdigest()


def _row_to_item(r: EnterpriseLead) -> EnterpriseLeadItem:
    return EnterpriseLeadItem(
        id=str(r.id),
        name=r.name,
        company_name=r.company_name,
        phone_or_email=r.phone_or_email,
        status=r.status,
        lead_source=r.lead_source,
        created_at=r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
    )


def _webhook_payload(row: EnterpriseLead) -> dict[str, Any]:
    return {
        "event": "enterprise_lead.created",
        "id": str(row.id),
        "lead_source": row.lead_source,
        "status": row.status,
        "name": row.name,
        "company_name": row.company_name,
        "phone_or_email": row.phone_or_email,
        "created_at": row.created_at.isoformat() if isinstance(row.created_at, datetime) else str(row.created_at),
    }


@public_router.post(
    "/",
    response_model=EnterpriseLeadCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Заявка на корпоративный тариф (публичный сайт)",
    description="При включённом Turnstile требуется `turnstile_token` (см. `TURNSTILE_*` в `.env.example`).",
)
async def create_enterprise_lead(
    request: Request,
    body: EnterpriseLeadCreateRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> EnterpriseLeadCreateResponse:
    trace_id = getattr(request.state, "trace_id", None)
    client_ip = client_ip_for_public_rate_limit(
        request,
        trusted_proxy_cidrs=settings.public_rate_limit_trusted_proxy_cidrs,
    )
    if settings.rate_public_enterprise_lead_ip_limit > 0:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:public_enterprise_lead:ip:{client_ip}",
                limit=settings.rate_public_enterprise_lead_ip_limit,
                window=settings.rate_public_enterprise_lead_ip_window_seconds,
            )
        except RateLimitExceeded:
            enterprise_lead_rate_limited_total.labels(reason="ip").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limited",
                    "message": "Слишком много запросов с этого адреса. Попробуйте позже.",
                    "trace_id": trace_id,
                },
            ) from None

    if settings.rate_public_enterprise_lead_contact_limit > 0:
        fp = _contact_rate_fingerprint(body.phone_or_email)
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:public_enterprise_lead:contact:{fp}",
                limit=settings.rate_public_enterprise_lead_contact_limit,
                window=settings.rate_public_enterprise_lead_contact_window_seconds,
            )
        except RateLimitExceeded:
            enterprise_lead_rate_limited_total.labels(reason="contact").inc()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "rate_limited",
                    "message": "Слишком много заявок с этим контактом. Попробуйте позже.",
                    "trace_id": trace_id,
                },
            ) from None

    if settings.turnstile_enabled:
        token = (body.turnstile_token or "").strip()
        if not token:
            auth_captcha_required_total.labels(reason="enterprise_lead_required").inc()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "captcha_required",
                    "message": "Требуется подтверждение Turnstile.",
                    "site_key": settings.turnstile_site_key,
                    "trace_id": trace_id,
                },
            )
        vr = await verify_turnstile(token, remote_ip=client_ip)
        auth_captcha_verified_total.labels(status="ok" if vr.ok else "denied").inc()
        if not vr.ok:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "captcha_required",
                    "message": "Требуется подтверждение Turnstile.",
                    "site_key": settings.turnstile_site_key,
                    "trace_id": trace_id,
                },
            ) from None

    row = EnterpriseLead(
        name=body.name.strip(),
        company_name=body.company_name.strip(),
        phone_or_email=body.phone_or_email.strip(),
        status="NEW",
        lead_source=body.lead_source,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    enterprise_lead_submitted_total.labels(lead_source=row.lead_source).inc()
    log_platform_audit(
        action="enterprise_lead_created",
        actor_founder_id=None,
        resource_type="enterprise_lead",
        resource_id=str(row.id),
        extra={"lead_source": body.lead_source},
    )
    if (settings.enterprise_lead_notify_webhook_url or "").strip():
        background_tasks.add_task(send_enterprise_lead_created_webhook, payload=_webhook_payload(row))
    return EnterpriseLeadCreateResponse(
        id=str(row.id),
        status=row.status,
        lead_source=row.lead_source,
    )


@internal_router.get(
    "/export",
    summary="Выгрузка заявок в CSV (Основатель)",
    response_class=Response,
)
async def export_enterprise_leads_csv(
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> Response:
    res = await session.execute(select(EnterpriseLead).order_by(EnterpriseLead.created_at.desc()))
    rows = res.scalars().all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "id",
            "created_at",
            "updated_at",
            "lead_source",
            "status",
            "name",
            "company_name",
            "phone_or_email",
        ],
    )
    for r in rows:
        w.writerow(
            [
                str(r.id),
                r.created_at.isoformat() if isinstance(r.created_at, datetime) else str(r.created_at),
                r.updated_at.isoformat() if isinstance(r.updated_at, datetime) else str(r.updated_at),
                r.lead_source,
                r.status,
                r.name,
                r.company_name,
                r.phone_or_email,
            ],
        )
    body = "\ufeff" + buf.getvalue()
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": 'attachment; filename="enterprise_leads.csv"',
        },
    )


@internal_router.get(
    "",
    response_model=list[EnterpriseLeadItem],
    summary="Список заявок на корпоративный тариф",
)
async def list_enterprise_leads(
    _principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> list[EnterpriseLeadItem]:
    res = await session.execute(select(EnterpriseLead).order_by(EnterpriseLead.created_at.desc()))
    rows = res.scalars().all()
    return [_row_to_item(r) for r in rows]


@internal_router.patch(
    "/{lead_id}",
    response_model=EnterpriseLeadItem,
    summary="Сменить статус заявки",
)
async def patch_enterprise_lead(
    lead_id: UUID,
    body: EnterpriseLeadPatchRequest,
    principal: PlatformFounderPrincipal = Depends(get_current_platform_founder),
    session: AsyncSession = Depends(get_session),
) -> EnterpriseLeadItem:
    row = await session.get(EnterpriseLead, lead_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    prev = row.status
    row.status = body.status
    await session.commit()
    await session.refresh(row)
    log_platform_audit(
        action="enterprise_lead_status_changed",
        actor_founder_id=principal.id,
        resource_type="enterprise_lead",
        resource_id=str(lead_id),
        extra={"from_status": prev, "to_status": body.status},
    )
    return _row_to_item(row)
