"""Tests for OmnichannelIntegrationsConfigService (Phase 5 Secrets & Integrations Config)."""

import json
import uuid

import pytest
from sqlalchemy import select

from src.application.services.omnichannel_integrations_config_service import (
    OmnichannelIntegrationsConfigService,
)
from src.domain.entities.omnichannel_audit_log import AuditLog as OmniAuditLog
from src.domain.entities.omnichannel_channel import Channel
from src.domain.entities.omnichannel_integration_config import (
    OmnichannelIntegrationConfig,
)
from src.infrastructure.database import base as db_base


@pytest.mark.asyncio
async def test_store_integration_secret_creates_config_and_audit(init_db, seed_data):
    """First call to store_integration_secret creates config row and INTEGRATION_KEY_CREATED audit."""
    business_account_id = seed_data["clinic_id"]
    channel_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelIntegrationsConfigService(session)

        cfg = await service.store_integration_secret(
            business_account_id=business_account_id,
            channel_id=channel_id,
            provider_type="TELEGRAM",
            scopes="messages:read, messages:write",
            raw_secret="super-secret-token",
            actor_id=actor_id,
            actor_type="OWNER",
        )
        await session.commit()

        # Config row exists and does not expose raw secret in plaintext
        assert cfg.id is not None
        assert cfg.business_account_id == business_account_id
        assert cfg.channel_id == channel_id
        assert cfg.credentials_encrypted is not None
        assert "super-secret-token" not in (cfg.credentials_encrypted or "")

        # Audit log entry recorded with correct action_type
        result = await session.execute(
            select(OmniAuditLog).where(
                OmniAuditLog.target_id == cfg.id,
                OmniAuditLog.action_type == "INTEGRATION_KEY_CREATED",
            )
        )
        audit = result.scalar_one_or_none()
        assert audit is not None
        assert audit.business_account_id == business_account_id
        assert audit.actor_id == actor_id
        assert audit.actor_type == "OWNER"
        assert audit.metadata is not None
        assert audit.metadata.get("provider_type") == "TELEGRAM"
        assert audit.metadata.get("scopes") == "messages:read, messages:write"


@pytest.mark.asyncio
async def test_store_integration_secret_updates_config_and_audit_rotated(init_db, seed_data):
    """Second call for same (business, channel) rotates key and writes INTEGRATION_KEY_ROTATED audit."""
    business_account_id = seed_data["clinic_id"]
    channel_id = uuid.uuid4()
    actor_id = uuid.uuid4()

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelIntegrationsConfigService(session)

        # Initial secret
        cfg1 = await service.store_integration_secret(
            business_account_id=business_account_id,
            channel_id=channel_id,
            provider_type="TELEGRAM",
            scopes=None,
            raw_secret="old-secret",
            actor_id=actor_id,
            actor_type="OWNER",
        )
        cfg1_id = cfg1.id

        # Rotate secret
        cfg2 = await service.store_integration_secret(
            business_account_id=business_account_id,
            channel_id=channel_id,
            provider_type="TELEGRAM",
            scopes=None,
            raw_secret="new-secret",
            actor_id=actor_id,
            actor_type="OWNER",
        )
        await session.commit()

        assert cfg2.id == cfg1_id
        assert cfg2.credentials_encrypted is not None
        # Encrypted blob should change after rotation
        assert cfg2.credentials_encrypted != cfg1.credentials_encrypted

        # There must be at least one ROTATED audit entry
        result = await session.execute(
            select(OmniAuditLog).where(
                OmniAuditLog.target_id == cfg2.id,
                OmniAuditLog.action_type == "INTEGRATION_KEY_ROTATED",
            )
        )
        rotated = result.scalar_one_or_none()
        assert rotated is not None
        assert rotated.actor_id == actor_id
        assert rotated.actor_type == "OWNER"


@pytest.mark.asyncio
async def test_get_integration_secret_decrypts_for_system_processes(init_db, seed_data):
    """get_integration_secret returns decrypted secret for system/background usage."""
    business_account_id = seed_data["clinic_id"]
    channel_id = uuid.uuid4()

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelIntegrationsConfigService(session)

        await service.store_integration_secret(
            business_account_id=business_account_id,
            channel_id=channel_id,
            provider_type="TELEGRAM",
            scopes=None,
            raw_secret="secret-for-decrypt",
            actor_id=None,
            actor_type="OWNER",
        )
        await session.commit()

        secret = await service.get_integration_secret(channel_id=channel_id)
        assert secret == "secret-for-decrypt"


@pytest.mark.asyncio
async def test_update_status_logs_audit_and_handles_revoked(init_db, seed_data):
    """update_status updates status and logs audit (including REVOKED → INTEGRATION_KEY_REVOKED)."""
    business_account_id = seed_data["clinic_id"]
    channel_id = uuid.uuid4()

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelIntegrationsConfigService(session)

        cfg = await service.store_integration_secret(
            business_account_id=business_account_id,
            channel_id=channel_id,
            provider_type="TELEGRAM",
            scopes=None,
            raw_secret="status-secret",
            actor_id=None,
            actor_type="OWNER",
        )
        await session.flush()

        # Mark OK
        await service.update_status(config_id=cfg.id, status="OK")
        # Mark REVOKED
        await service.update_status(config_id=cfg.id, status="REVOKED")
        await session.commit()

        # Verify latest status
        result_cfg = await session.execute(
            select(OmnichannelIntegrationConfig).where(OmnichannelIntegrationConfig.id == cfg.id)
        )
        cfg_db = result_cfg.scalar_one_or_none()
        assert cfg_db is not None
        assert cfg_db.status == "REVOKED"

        # Check that status changes are logged
        result_logs = await session.execute(
            select(OmniAuditLog).where(OmniAuditLog.target_id == cfg.id)
        )
        logs = list(result_logs.scalars().all())
        action_types = {row.action_type for row in logs}
        assert "INTEGRATION_STATUS_CHANGED" in action_types
        assert "INTEGRATION_KEY_REVOKED" in action_types


@pytest.mark.asyncio
async def test_get_telegram_admin_chat_id_for_clinic_from_credentials(init_db, seed_data):
    """get_telegram_admin_chat_id_for_clinic returns admin_chat_id from TELEGRAM_BOT channel credentials (3.1)."""
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        channel = Channel(
            business_account_id=clinic_id,
            type="TELEGRAM_BOT",
            display_name="TELEGRAM_BOT",
            status="PENDING_SETUP",
        )
        session.add(channel)
        await session.flush()
        credentials_json = json.dumps({
            "bot_token": "dummy-token",
            "admin_chat_id": "-1001234567890",
        })
        service = OmnichannelIntegrationsConfigService(session)
        await service.store_integration_secret(
            business_account_id=clinic_id,
            channel_id=channel.id,
            provider_type="TELEGRAM",
            scopes=None,
            raw_secret=credentials_json,
            actor_id=None,
            actor_type="OWNER",
        )
        await session.commit()

    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelIntegrationsConfigService(session)
        admin_chat_id = await service.get_telegram_admin_chat_id_for_clinic(clinic_id)
        assert admin_chat_id == "-1001234567890"


@pytest.mark.asyncio
async def test_get_telegram_admin_chat_id_for_clinic_no_channel_returns_none_or_settings(init_db, seed_data):
    """When clinic has no TELEGRAM_BOT channel, get_telegram_admin_chat_id_for_clinic returns None or env fallback."""
    clinic_id = seed_data["clinic_id"]
    async with db_base.AsyncSessionLocal() as session:
        service = OmnichannelIntegrationsConfigService(session)
        admin_chat_id = await service.get_telegram_admin_chat_id_for_clinic(clinic_id)
        # In test env TELEGRAM_ADMIN_CHAT_ID is usually unset -> None
        assert admin_chat_id is None or isinstance(admin_chat_id, str)

