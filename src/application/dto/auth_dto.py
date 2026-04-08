"""Auth DTOs for patient SMS login."""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

_CLINIC_SLUG_MAX = 120


class SendCodeRequest(BaseModel):
    """Request DTO for sending SMS code."""

    phone: str
    #: Публичный slug клиники (витрина `/c/{slug}/…`); если не задан — legacy «первая клиника в БД».
    clinic_slug: str | None = Field(None, max_length=_CLINIC_SLUG_MAX)
    turnstile_token: str | None = None

    @field_validator("clinic_slug", mode="before")
    @classmethod
    def _normalize_clinic_slug(cls, v: object) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        s = v.strip()
        return s if s else None


class VerifyCodeRequest(BaseModel):
    """Request DTO for verifying SMS code (with optional marketing attribution context)."""

    phone: str
    code: str
    turnstile_token: str | None = None
    consent_pd: bool = True
    consent_mailing: bool = False
    full_name: str | None = None
    birth_date: str | None = None  # ISO date YYYY-MM-DD

    # Optional attribution context from landing/PWA session
    session_id: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_content: str | None = None
    utm_term: str | None = None
    landing_page: str | None = None
    anchor: str | None = None
    clinic_slug: str | None = Field(None, max_length=_CLINIC_SLUG_MAX)

    @field_validator("clinic_slug", mode="before")
    @classmethod
    def _normalize_clinic_slug_verify(cls, v: object) -> str | None:
        if v is None:
            return None
        if not isinstance(v, str):
            return None
        s = v.strip()
        return s if s else None


class AuthTokenResponse(BaseModel):
    """Response DTO with access token."""

    access_token: str
    token_type: str = "bearer"
    patient_id: UUID | None = None

