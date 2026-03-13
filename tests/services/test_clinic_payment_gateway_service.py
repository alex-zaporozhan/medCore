"""Tests for ClinicPaymentGatewayService."""

import uuid

import pytest
from sqlalchemy import select

from src.application.services.clinic_payment_gateway_service import (
    ClinicPaymentGatewayService,
)
from src.domain.entities.clinic_payment_gateway import ClinicPaymentGateway
from src.infrastructure.database import base as db_base


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_upsert_credentials_creates_and_updates_row(init_db, seed_data):
  """upsert_credentials creates row for (clinic, gateway) and updates on second call; get_credentials decrypts payload."""
  clinic_id = seed_data["clinic_id"]
  actor_id = uuid.uuid4()

  async with db_base.AsyncSessionLocal() as session:
      service = ClinicPaymentGatewayService(session)

      created = await service.upsert_credentials(
          clinic_id=clinic_id,
          gateway="tinkoff",
          raw_payload='{"terminal_key":"T-1","password":"P-1"}',
          actor_id=actor_id,
      )
      await session.commit()

      assert created.id is not None
      assert created.clinic_id == clinic_id
      assert created.gateway == "tinkoff"
      assert created.credentials_encrypted is not None
      assert '{"terminal_key"' not in (created.credentials_encrypted or "")
      assert created.status == "PENDING"

      # get_credentials returns decrypted JSON string
      raw = await service.get_credentials(clinic_id=clinic_id, gateway="tinkoff")
      assert raw == '{"terminal_key":"T-1","password":"P-1"}'

      # Second upsert updates same row and keeps status=PENDING
      updated = await service.upsert_credentials(
          clinic_id=clinic_id,
          gateway="tinkoff",
          raw_payload='{"terminal_key":"T-2","password":"P-2"}',
          actor_id=actor_id,
      )
      await session.commit()

      assert updated.id == created.id
      assert updated.status == "PENDING"

      result = await session.execute(
          select(ClinicPaymentGateway).where(
              ClinicPaymentGateway.clinic_id == clinic_id,
              ClinicPaymentGateway.gateway == "tinkoff",
          )
      )
      row = result.scalar_one_or_none()
      assert row is not None
      assert row.credentials_encrypted is not None
      assert '{"terminal_key":"T-2"' not in (row.credentials_encrypted or "")

