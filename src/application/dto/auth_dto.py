"""Auth DTOs for patient SMS login."""

from uuid import UUID

from pydantic import BaseModel


class SendCodeRequest(BaseModel):
    """Request DTO for sending SMS code."""

    phone: str


class VerifyCodeRequest(BaseModel):
    """Request DTO for verifying SMS code (with optional marketing attribution context)."""

    phone: str
    code: str
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


class AuthTokenResponse(BaseModel):
    """Response DTO with access token."""

    access_token: str
    token_type: str = "bearer"
    patient_id: UUID | None = None

