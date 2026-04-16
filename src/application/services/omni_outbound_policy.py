"""OutboundPolicy: resolve target channel for admin replies (ARCH §3)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.omnichannel_channel import Channel as OmniChannel
from src.domain.entities.omnichannel_chat import Chat as OmniChat
from src.domain.entities.omnichannel_message import Message as OmniMessage

_END_USER_INBOUND_ACTORS = ("CLIENT", "CONTACT", "PATIENT")


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
    """Backward-compatible name: last inbound from end-user with outbound-capable channel."""
    return await get_last_inbound_outbound_capable_channel_id(session, chat_id=chat_id, clinic_id=None)


async def get_last_inbound_outbound_capable_channel_id(
    session: AsyncSession,
    *,
    chat_id: UUID,
    clinic_id: UUID | None,
) -> UUID | None:
    """
    Prefer the most recent inbound message from an end-user (CLIENT/CONTACT/PATIENT) whose
    channel supports operator outbound (Telegram / web widget / web app).

    Walks recent history so a newer inbound on an unsupported adapter does not hide an
    older Telegram/WEB reply path.
    """
    stmt = (
        select(OmniMessage.channel_id)
        .where(
            OmniMessage.chat_id == chat_id,
            OmniMessage.direction == "INBOUND",
            OmniMessage.actor_type.in_(_END_USER_INBOUND_ACTORS),
            OmniMessage.channel_id.isnot(None),
        )
        .order_by(OmniMessage.created_at.desc())
        .limit(50)
    )
    result = await session.execute(stmt)
    channel_ids = list(result.scalars().all())
    if not channel_ids:
        return None
    uniq: list[UUID] = []
    for cid in channel_ids:
        if cid not in uniq:
            uniq.append(cid)
    ch_rows = await session.execute(select(OmniChannel).where(OmniChannel.id.in_(uniq)))
    ch_map: dict[UUID, OmniChannel] = {c.id: c for c in ch_rows.scalars().all()}
    for cid in channel_ids:
        ch = ch_map.get(cid)
        if not ch:
            continue
        if clinic_id is not None and ch.business_account_id != clinic_id:
            continue
        if channel_type_allows_admin_outbound(ch.type):
            return cid
    return None


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

    default_id = await get_last_inbound_outbound_capable_channel_id(
        session, chat_id=chat.id, clinic_id=clinic_id
    )
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
