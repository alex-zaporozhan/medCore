"""Agreement settings DTOs (PD text, allow registration without mailing consent)."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AgreementSettingsRead(BaseModel):
    """Agreement settings read (public or admin)."""

    clinic_id: UUID
    pd_agreement_text: str | None = None
    allow_registration_without_mailing_consent: bool = True

    model_config = ConfigDict(from_attributes=True)


class AgreementSettingsUpdate(BaseModel):
    """Agreement settings update (admin)."""

    pd_agreement_text: str | None = Field(None, max_length=50000)
    allow_registration_without_mailing_consent: bool | None = None
