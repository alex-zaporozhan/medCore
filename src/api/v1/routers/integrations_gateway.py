"""Integration Gateway API endpoints for omnichannel assistant (Phase 2)."""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.integration_gateway_service import IntegrationGatewayService
from src.application.services.omnichannel_chat_service import OmnichannelChatService
from src.application.services.webchat_push_manager import get_webchat_push_manager
from src.application.services.turnstile_service import verify_turnstile
from src.core.config import settings
from src.core.datetime_utils import to_iso8601_utc
from src.domain.entities.clinic import Clinic
from src.infrastructure.database.base import get_db
from src.infrastructure.rate_limiter import RateLimitExceeded, get_rate_limiter
from src.core.metrics import auth_captcha_required_total, auth_captcha_verified_total

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["integrations"])


async def _get_default_business_account_id(session: AsyncSession) -> UUID:
    """MVP: use the first clinic as business_account_id.

    Later can be replaced with explicit mapping per bot/token/host.
    """
    from sqlalchemy import select

    result = await session.execute(select(Clinic).limit(1))
    clinic = result.scalar_one_or_none()
    if not clinic:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No clinics found to bind omnichannel assistant",
        )
    return clinic.id


def _validate_telegram_token(token: str | None) -> None:
    """Simple check that configured token is present. Could be extended to IP / secret checks."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="TELEGRAM_BOT_TOKEN is not configured",
        )


def _validate_telegram_webhook_secret(secret: str | None, header_value: str | None) -> None:
    """If TELEGRAM_WEBHOOK_SECRET is set, require X-Telegram-Bot-Api-Secret-Token to match."""
    if not secret or not secret.strip():
        return
    if not header_value or header_value.strip() != secret.strip():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing webhook secret",
        )


@router.post("/integrations/webhooks/telegram")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Telegram Bot API webhook → NormalizedMessageDTO → omnichannel chat/message.

    If TELEGRAM_WEBHOOK_SECRET is set in env, requests must include header
    X-Telegram-Bot-Api-Secret-Token with the same value.
    """
    _validate_telegram_webhook_secret(
        settings.telegram_webhook_secret,
        x_telegram_bot_api_secret_token,
    )
    raw = await request.json()
    _validate_telegram_token(settings.telegram_bot_token)

    service = IntegrationGatewayService(
        session=db,
        business_account_id=await _get_default_business_account_id(db),
    )
    dto = service.normalize_telegram_update(raw)
    if dto is None:
        # Ignore non-text or unsupported updates
        return {"status": "ignored"}
    # Attach trace_id from HTTP middleware so that omnichannel logs/metrics can be correlated
    dto.trace_id = getattr(request.state, "trace_id", None)
    await service.handle_inbound_normalized_message(dto)
    return {"status": "ok"}


@router.post("/webchat/messages")
async def webchat_inbound_message(
    request: Request,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    rate_limiter=Depends(get_rate_limiter),
):
    """Public endpoint for Web-chat widget to send messages.

    Body (MVP):
    - anonymous_id: str
    - text: str
    - message_id?: str
    - timestamp?: ISO string
    """
    client_ip = request.client.host if request.client else "unknown"
    if settings.turnstile_enabled:
        try:
            await rate_limiter.check_or_raise(
                key=f"rate:webchat_msg:captcha_soft:ip:{client_ip}",
                limit=settings.rate_webchat_message_captcha_soft_ip_limit,
                window=settings.rate_webchat_message_window_seconds,
            )
        except RateLimitExceeded:
            auth_captcha_required_total.labels(reason="webchat_soft_limit").inc()
            vr = await verify_turnstile(payload.get("turnstile_token"), remote_ip=client_ip)
            auth_captcha_verified_total.labels(status="ok" if vr.ok else "denied").inc()
            if not vr.ok:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail={
                        "code": "captcha_required",
                        "message": "Требуется подтверждение Turnstile.",
                        "site_key": settings.turnstile_site_key,
                    },
                ) from None
    service = IntegrationGatewayService(
        session=db,
        business_account_id=await _get_default_business_account_id(db),
    )
    dto = service.normalize_webchat_message(payload)
    if dto is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webchat payload",
        )
    dto.trace_id = getattr(request.state, "trace_id", None)
    await service.handle_inbound_normalized_message(dto)
    return {"status": "ok"}


class WebchatPollItem(BaseModel):
    message_id: UUID
    content: str
    created_at: str
    actor_type: str


class WebchatPollResponse(BaseModel):
    items: list[WebchatPollItem]


@router.get("/webchat/poll", response_model=WebchatPollResponse)
async def webchat_poll(
    anonymous_id: str = Query(..., min_length=1, description="Widget anonymous_id"),
    timeout: float = Query(25.0, ge=1.0, le=60.0, description="Long-poll wait seconds"),
    db: AsyncSession = Depends(get_db),
) -> WebchatPollResponse:
    """Long-poll for new outbound messages in webchat. Widget calls this to receive replies without polling DB.

    Waits up to `timeout` seconds for new messages; returns immediately if any arrive.
    """
    business_account_id = await _get_default_business_account_id(db)
    chat_service = OmnichannelChatService(db)
    chat = await chat_service.get_chat_by_webchat_anonymous_id(
        business_account_id=business_account_id,
        anonymous_id=anonymous_id,
    )
    if not chat:
        return WebchatPollResponse(items=[])

    manager = get_webchat_push_manager()
    push_items = await manager.wait_for_new(chat_id=chat.id, timeout_seconds=timeout)
    items = [
        WebchatPollItem(
            message_id=p.message_id,
            content=p.content,
            created_at=to_iso8601_utc(p.created_at) or "",
            actor_type=p.actor_type,
        )
        for p in push_items
    ]
    return WebchatPollResponse(items=items)


@router.post("/integrations/webhooks/whatsapp")
async def whatsapp_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """WhatsApp Business webhook → NormalizedMessageDTO → omnichannel chat/message (MVP).

    For now we assume payload is already a simplified JSON structure compatible with
    IntegrationGatewayService.normalize_whatsapp_message.
    """
    raw = await request.json()
    service = IntegrationGatewayService(
        session=db,
        business_account_id=await _get_default_business_account_id(db),
    )
    dto = service.normalize_whatsapp_message(raw)
    if dto is None:
        return {"status": "ignored"}
    dto.trace_id = getattr(request.state, "trace_id", None)
    await service.handle_inbound_normalized_message(dto)
    return {"status": "ok"}


@router.post("/integrations/webhooks/vk")
async def vk_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """VK Messages webhook → NormalizedMessageDTO → omnichannel chat/message (MVP)."""
    raw = await request.json()
    service = IntegrationGatewayService(
        session=db,
        business_account_id=await _get_default_business_account_id(db),
    )
    dto = service.normalize_vk_message(raw)
    if dto is None:
        return {"status": "ignored"}
    dto.trace_id = getattr(request.state, "trace_id", None)
    await service.handle_inbound_normalized_message(dto)
    return {"status": "ok"}


@router.post("/integrations/webhooks/instagram")
async def instagram_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Instagram Direct webhook → NormalizedMessageDTO → omnichannel chat/message (MVP)."""
    raw = await request.json()
    service = IntegrationGatewayService(
        session=db,
        business_account_id=await _get_default_business_account_id(db),
    )
    dto = service.normalize_instagram_message(raw)
    if dto is None:
        return {"status": "ignored"}
    dto.trace_id = getattr(request.state, "trace_id", None)
    await service.handle_inbound_normalized_message(dto)
    return {"status": "ok"}


@router.post("/integrations/webhooks/email")
async def email_inbound_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Email inbound webhook → NormalizedMessageDTO → omnichannel chat/message (MVP).

    Can be called by an SMTP/IMAP bridge or external provider (SendGrid, etc.).
    """
    raw = await request.json()
    service = IntegrationGatewayService(
        session=db,
        business_account_id=await _get_default_business_account_id(db),
    )
    dto = service.normalize_email_message(raw)
    if dto is None:
        return {"status": "ignored"}
    dto.trace_id = getattr(request.state, "trace_id", None)
    await service.handle_inbound_normalized_message(dto)
    return {"status": "ok"}

