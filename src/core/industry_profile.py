"""Organization vertical profile (SAAS_STRENGTHENING_MASTER_PLAN §14, arch_plan Phase 3+)."""

from __future__ import annotations

from typing import Final

# Canonical values stored in organizations.industry_profile
INDUSTRY_PROFILE_DENTAL: Final[str] = "industry_dental"
INDUSTRY_PROFILE_GENERIC: Final[str] = "industry_generic"

ALLOWED_INDUSTRY_PROFILES: Final[frozenset[str]] = frozenset(
    {INDUSTRY_PROFILE_DENTAL, INDUSTRY_PROFILE_GENERIC}
)


def normalize_industry_profile(value: str) -> str:
    v = (value or "").strip()
    if v not in ALLOWED_INDUSTRY_PROFILES:
        raise ValueError(
            f"industry_profile must be one of {sorted(ALLOWED_INDUSTRY_PROFILES)}, got {value!r}"
        )
    return v


def is_dental_clinical_vertical(profile: str | None) -> bool:
    """Legacy clinics (no org / unknown profile) keep dental-specific modules enabled."""
    if profile is None:
        return True
    return profile == INDUSTRY_PROFILE_DENTAL
