"""OutboundPolicy: resolve target channel for admin replies (ARCH §3)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_message import Message as OmniMessage


def channel_type_allows_admin_outbound(channel_type: str | None) -> bool:
    """Same criterion as OmnichannelOutboundDispatcher: real outbound adapters."""
    if not channel_type:
        return False
    t = channel_type.upper()
    return t in ("TELEGRAM_BOT", "WEB_WIDGET", "WEB_APP")


async def get_last_client_inbound_channel_id(
    session: AsyncSession,
    chat_id: UUID,
) -> UUID | None:
    """Last INBOUND + CLIENT message with non-null channel_id, by created_at DESC."""
    stmt = (
        select(OmniMessage.channel_id)
        .where(
            OmniMessage.chat_id == chat_id,
            OmniMessage.direction == "INBOUND",
            OmniMessage.actor_type == "CLIENT",
            OmniMessage.channel_id.isnot(None),
        )
        .order_by(OmniMessage.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    return row


async def resolve_reply_channel_id_for_admin(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    chat: OmniChat,
    reply_channel_id: UUID | None,
) -> UUID:
    """Resolve outbound channel per ARCH §3; raises HTTPException on 400/409."""
    if reply_channel_id is not None:
        ch_result = await session.execute(
            select(OmniChannel).where(OmniChannel.id == reply_channel_id).limit(1)
        )
        channel = ch_result.scalar_one_or_none()
        if channel is None or channel.business_account_id != clinic_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="reply_channel_id is invalid or does not belong to this clinic",
            )
        if not channel_type_allows_admin_outbound(channel.type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This channel type does not support operator outbound replies",
            )
        return reply_channel_id

    default_id = await get_last_client_inbound_channel_id(session, chat.id)
    if default_id is not None:
        return default_id

    if chat.channel_id is not None:
        ch_result = await session.execute(
            select(OmniChannel).where(OmniChannel.id == chat.channel_id).limit(1)
        )
        primary = ch_result.scalar_one_or_none()
        if primary is None or primary.business_account_id != clinic_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "omni_reply_channel_unresolved",
                    "message": "Chat primary channel is missing or invalid; pass reply_channel_id.",
                },
            )
        if not channel_type_allows_admin_outbound(primary.type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chat primary channel does not support operator outbound replies; pass reply_channel_id.",
            )
        return chat.channel_id

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "omni_reply_channel_unresolved",
            "message": (
                "Reply channel could not be determined; configure the chat channel or pass reply_channel_id."
            ),
        },
    )
