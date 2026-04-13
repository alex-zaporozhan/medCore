"""Public clinic list scrub (U-011) — storefront fields when vitrine off."""

from datetime import datetime, time
from decimal import Decimal
from uuid import uuid4

from src.application.dto.clinic_dto import ClinicRead, clinic_read_scrub_public_pii


def test_scrub_clears_store_titles_when_vitrine_disabled() -> None:
    cid = uuid4()
    now = datetime(2026, 4, 11, 12, 0, 0)
    read = ClinicRead(
        id=cid,
        name="Clinic",
        workday_start=time(9, 0),
        workday_end=time(18, 0),
        slot_duration_minutes=30,
        prepayment_amount=Decimal("0"),
        patient_store_visible=False,
        patient_store_title="Черновик витрины",
        patient_store_subtitle="Не показывать публично",
        created_at=now,
        updated_at=now,
    )
    out = clinic_read_scrub_public_pii(read)
    assert out.patient_store_visible is False
    assert out.patient_store_title is None
    assert out.patient_store_subtitle is None
    assert out.phone is None


def test_scrub_keeps_store_titles_when_vitrine_enabled() -> None:
    cid = uuid4()
    now = datetime(2026, 4, 11, 12, 0, 0)
    read = ClinicRead(
        id=cid,
        name="Clinic",
        workday_start=time(9, 0),
        workday_end=time(18, 0),
        slot_duration_minutes=30,
        prepayment_amount=Decimal("0"),
        patient_store_visible=True,
        patient_store_title="Публичный заголовок",
        patient_store_subtitle="Подзаголовок",
        created_at=now,
        updated_at=now,
    )
    out = clinic_read_scrub_public_pii(read)
    assert out.patient_store_title == "Публичный заголовок"
    assert out.patient_store_subtitle == "Подзаголовок"
