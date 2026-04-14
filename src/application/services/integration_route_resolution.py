"""LEAD B1: resolve clinic (business_account_id) for omnichannel integration webhooks.

Legacy MVP used the first clinic row; multi-tenant setups must use an explicit ``omni_channels`` row
(channel id in URL or body).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.metrics import integration_route_resolution_total
from src.domain.entities.clinic import Clinic
from src.domain.entities.omnichannel_channel import Channel

logger = logging.getLogger(__name__)

# Gateway name -> omni_channels.type (see OmnichannelChatService.get_or_create_channel_for_provider).
EXPECTED_OMNI_CHANNEL_TYPE: dict[str, str] = {
    "telegram": "TELEGRAM_BOT",
    "webchat": "WEB_WIDGET",
    "whatsapp": "WHATSAPP_BUSINESS",
    "vk": "VK_BOT",
    "instagram": "INSTAGRAM_DM",
    "email": "EMAIL_INBOX",
}


async def _first_clinic_id(session: AsyncSession) -> UUID:
    """Deterministic pick when legacy fallback is enabled (lowest ``clinics.id``)."""
    result = await session.execute(select(Clinic.id).order_by(Clinic.id).limit(1))
    row = result.scalar_one_or_none()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No clinics found to bind omnichannel assistant",
        )
    return row


async def resolve_business_account_for_integration_webhook(
    session: AsyncSession,
    *,
    gateway: str,
    channel_id: UUID | None,
) -> UUID:
    """
    Return clinic id for IntegrationGatewayService.

    When ``channel_id`` is set, resolve via ``omni_channels`` and validate channel type for gateway.
    When unset, use single-clinic shortcut, or legacy first-clinic if enabled and multiple clinics exist.
    """
    expected_type = EXPECTED_OMNI_CHANNEL_TYPE.get(gateway)
    if not expected_type:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unknown integration gateway: {gateway}",
        )

    if channel_id is not None:
        result = await session.execute(select(Channel).where(Channel.id == channel_id))
        ch = result.scalar_one_or_none()
        if not ch:
            integration_route_resolution_total.labels(result="not_found").inc()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "omni_channel_not_found",
                    "message": "Unknown integration channel id",
                },
            )
        if ch.type != expected_type:
            integration_route_resolution_total.labels(result="type_mismatch").inc()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "omni_channel_type_mismatch",
                    "message": f"Channel type {ch.type!r} does not match gateway {gateway!r}",
                },
            )
        integration_route_resolution_total.labels(result="matched").inc()
        return ch.business_account_id

    cnt = await session.scalar(select(func.count()).select_from(Clinic))
    if cnt == 0:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No clinics found to bind omnichannel assistant",
        )
    if cnt == 1:
        cid = await session.scalar(select(Clinic.id).order_by(Clinic.id).limit(1))
        assert cid is not None
        integration_route_resolution_total.labels(result="singleton").inc()
        return cid

    if settings.integration_gateway_legacy_first_clinic_fallback:
        bid = await _first_clinic_id(session)
        integration_route_resolution_total.labels(result="legacy_fallback").inc()
        logger.warning(
            "integration gateway: legacy first-clinic routing (multi-tenant); set channel-scoped URL or disable fallback",
            extra={"gateway": gateway, "clinic_id": str(bid), "component": "integration_route_resolution"},
        )
        return bid

    integration_route_resolution_total.labels(result="ambiguous").inc()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "code": "integration_route_required",
            "message": (
                "Multiple clinics: specify integration channel id "
                "(e.g. POST .../integrations/webhooks/telegram/channels/{channel_id} "
                "or webchat body integration_channel_id)."
            ),
        },
    )
