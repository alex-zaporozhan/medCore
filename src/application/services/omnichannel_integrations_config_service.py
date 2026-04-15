"""Service to store and read omnichannel integration secrets per channel.

This wraps simple encrypted storage using the existing encryption utils
and writes audit-log entries for all secret mutations.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.encryption import decrypt_ciphertext, encrypt_plaintext
from src.domain.entities.omnichannel_audit_log import AuditLog as OmniAuditLog
from src.domain.entities.omnichannel_channel import Channel
from src.domain.entities.omnichannel_integration_config import (
    OmnichannelIntegrationConfig,
)

logger = logging.getLogger(__name__)


class OmnichannelIntegrationsConfigService:
    """Encapsulates work with omni_integration_configs and audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_config_for_channel(
        self,
        business_account_id: UUID,
        channel_id: UUID,
    ) -> OmnichannelIntegrationConfig | None:
        stmt = select(OmnichannelIntegrationConfig).where(
            OmnichannelIntegrationConfig.business_account_id == business_account_id,
            OmnichannelIntegrationConfig.channel_id == channel_id,
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def store_integration_secret(
        self,
        *,
        business_account_id: UUID,
        channel_id: UUID,
        provider_type: str,
        scopes: str | None,
        raw_secret: str,
        actor_id: UUID | None,
        actor_type: str,
    ) -> OmnichannelIntegrationConfig:
        """Create or update integration config for channel and log to AuditLog."""
        encrypted = encrypt_plaintext(raw_secret)

        cfg = await self.get_config_for_channel(
            business_account_id=business_account_id,
            channel_id=channel_id,
        )
        created = False
        if cfg is None:
            cfg = OmnichannelIntegrationConfig(
                business_account_id=business_account_id,
                channel_id=channel_id,
                provider_type=provider_type,
                scopes=scopes,
                status="PENDING",
                credentials_encrypted=encrypted,
                created_by=actor_id,
                updated_by=actor_id,
            )
            self.session.add(cfg)
            created = True
        else:
            cfg.provider_type = provider_type
            cfg.scopes = scopes
            cfg.credentials_encrypted = encrypted
            cfg.updated_by = actor_id
            # When credentials are updated, reset status to PENDING until health-check passes.
            if cfg.status in ("EXPIRED", "ERROR", "REVOKED"):
                cfg.status = "PENDING"

        await self.session.flush()
        await self.session.refresh(cfg)

        # Use action_type values aligned with ARCH: INTEGRATION_KEY_CREATED / ROTATED / REVOKED.
        action_type = "INTEGRATION_KEY_CREATED" if created else "INTEGRATION_KEY_ROTATED"
        audit = OmniAuditLog(
            business_account_id=business_account_id,
            actor_id=actor_id,
            actor_type=actor_type,
            action_type=action_type,
            target_type="INTEGRATION",
            target_id=cfg.id,
            meta={
                "channel_id": str(channel_id),
                "provider_type": provider_type,
                "scopes": scopes,
            },
        )
        self.session.add(audit)
        await self.session.flush()

        logger.info(
            "Omnichannel integration secret stored",
            extra={
                "business_account_id": str(business_account_id),
                "channel_id": str(channel_id),
                "config_id": str(cfg.id),
                "action_type": action_type,
            },
        )
        return cfg

    async def get_integration_secret(
        self,
        *,
        channel_id: UUID,
    ) -> str | None:
        """Return decrypted secret for system/background processes."""
        stmt = select(OmnichannelIntegrationConfig).where(
            OmnichannelIntegrationConfig.channel_id == channel_id,
        )
        result = await self.session.execute(stmt)
        cfg = result.scalars().first()
        if not cfg or not cfg.credentials_encrypted:
            return None
        return decrypt_ciphertext(cfg.credentials_encrypted)

    async def get_telegram_admin_chat_id_for_clinic(self, clinic_id: UUID) -> str | None:
        """
        Admin chat ID for Telegram notifications for this clinic.
        Reads TELEGRAM_BOT channel credentials (admin_chat_id); fallback to settings.telegram_admin_chat_id.
        Used by omni orchestrator and by booking/notification tasks to notify admin.
        """
        try:
            stmt = (
                select(Channel)
                .where(
                    Channel.business_account_id == clinic_id,
                    Channel.type == "TELEGRAM_BOT",
                )
                .order_by(Channel.created_at.desc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            channel = result.scalar_one_or_none()
            if not channel:
                return (settings.telegram_admin_chat_id or "").strip() or None
            raw = await self.get_integration_secret(channel_id=channel.id)
            if not raw:
                return (settings.telegram_admin_chat_id or "").strip() or None
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get("admin_chat_id"):
                val = (parsed["admin_chat_id"] or "").strip() or None
                if val:
                    return val
        except (TypeError, ValueError, Exception):  # noqa: BLE001
            logger.debug(
                "get_telegram_admin_chat_id_for_clinic: parse or load failed",
                extra={"clinic_id": str(clinic_id)},
            )
        return (settings.telegram_admin_chat_id or "").strip() or None

    async def update_status(
        self,
        *,
        config_id: UUID,
        status: str,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Update status (OK/EXPIRED/ERROR/REVOKED) for monitoring/health-checks."""
        stmt = select(OmnichannelIntegrationConfig).where(
            OmnichannelIntegrationConfig.id == config_id,
        )
        result = await self.session.execute(stmt)
        cfg = result.scalars().first()
        if not cfg:
            return
        cfg.status = status
        await self.session.flush()

        action_type = "INTEGRATION_KEY_REVOKED" if status == "REVOKED" else "INTEGRATION_STATUS_CHANGED"
        audit = OmniAuditLog(
            business_account_id=cfg.business_account_id,
            actor_id=None,
            actor_type="SYSTEM",
            action_type=action_type,
            target_type="INTEGRATION",
            target_id=cfg.id,
            meta=meta or {"status": status},
        )
        self.session.add(audit)
        await self.session.flush()

