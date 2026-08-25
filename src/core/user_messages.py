"""
Canonical user-facing API messages (Law 10).

HTTPException.detail for expected client errors is a dict ``{code, message}``.
``message`` is English (logs, OpenAPI, network tab). The UI maps ``code`` via i18n.
Legacy string details remain only where a router has not been migrated yet.
"""

EMPTY_DB_NO_CLINIC = {
    "code": "empty_db_no_clinic",
    "message": "No clinics in the database. Add a clinic in settings.",
}

# ADR-012: same machine code as provision retry 409 — org platform billing is revoked.
ADMIN_ORG_PLATFORM_BILLING_REVOKED = {
    "code": "billing_revoked",
    "message": "Access paused: the platform subscription for this organization was revoked.",
}

INVALID_CREDENTIALS = {
    "code": "invalid_credentials",
    "message": "Invalid email or password",
}
LOGIN_RATE_LIMITED = {
    "code": "rate_limited",
    "message": "Too many attempts. Try again later.",
}
INVALID_TOTP = {
    "code": "invalid_totp",
    "message": "Invalid two-factor authentication code",
}
INVALID_MFA_TOKEN = {
    "code": "invalid_mfa_token",
    "message": "Invalid or expired MFA token",
}

AUTH_REQUIRED = {
    "code": "unauthorized",
    "message": "Authentication required",
}
TOKEN_INVALID_OR_EXPIRED = {
    "code": "unauthorized",
    "message": "Invalid or expired token",
}
TOKEN_ISS_AUD_INVALID = {
    "code": "unauthorized",
    "message": "Invalid token (issuer/audience)",
}
CLINIC_CONTEXT_REQUIRED = {
    "code": "clinic_context_required",
    "message": "Clinic context is required",
}
PLATFORM_FOUNDER_TOKEN_REQUIRED = {
    "code": "platform_founder_token_required",
    "message": "A platform founder token is required",
}
