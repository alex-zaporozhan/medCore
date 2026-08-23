"""OpenAPI / request bodies for platform billing (contour B)."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class PlatformBillingWebhookOkResponse(BaseModel):
    """YooKassa notification accepted and processed (2xx)."""

    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok", description="Acknowledgement for the payment provider")


class PlatformBillingWebhookErrorDetail(BaseModel):
    model_config = ConfigDict(extra="allow")

    code: str
    message: str
    trace_id: str | None = None


class PlatformOwnerInviteAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., min_length=8, max_length=512, description="One-time invite token from email/link")
    password: str = Field(..., min_length=8, max_length=200, description="New password for the owner admin account")


class PlatformOwnerInviteAcceptResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(default="ok")
    admin_id: str = Field(description="Provisioned AdminUser id")


class PlatformProvisionQueueItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent_id: str
    status: str
    email: str | None = None
    organization_id: str | None = None
    provision_retry_count: int
    provision_next_attempt_at: str | None = None
    provision_last_error: str | None = None
    provision_dead_letter: bool
    paid_at: str | None = None
    billing_revoked_at: str | None = None


class PlatformCatalogPlanPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str
    display_name: str
    description: str | None = None
    option_keys: list[str] = Field(default_factory=list)
    price_monthly_rub: str | None = Field(
        default=None,
        description="Subscription list price per month (USD-denominated catalog amount)",
    )
    price_annual_rub: str | None = Field(
        default=None,
        description="Subscription list price per year (USD-denominated catalog amount)",
    )
    currency: str = Field(default="USD", description="ISO currency for catalog list prices")


class PlatformCatalogPlanInternal(BaseModel):
    """Full plan row for platform founder (contour B internal)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    slug: str
    display_name: str
    description: str | None = None
    option_keys: list[str] = Field(default_factory=list)
    price_monthly_rub: str | None = None
    price_annual_rub: str | None = None
    is_active: bool
    sort_order: int
    currency: str = Field(default="USD", description="ISO currency for catalog list prices")


class PlatformCatalogPlanUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10_000)
    option_keys: list[str] = Field(default_factory=list)
    is_active: bool = True
    sort_order: int = 0
    price_monthly_rub: Decimal | None = Field(default=None, ge=0)
    price_annual_rub: Decimal | None = Field(default=None, ge=0)


class PlatformCatalogOptionPublic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    entitlement_key: str
    display_name: str
    description: str | None = None
    list_price_rub: str | None = None
    currency: str = Field(default="USD", description="ISO currency for catalog list prices")


class PlatformSignupCheckoutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    plan_slug: str = Field(..., min_length=1, max_length=80)
    billing_period: Literal["monthly", "annual"]
    return_url: str | None = Field(default=None, max_length=512)
    #: Обязателен при ``TURNSTILE_ENABLED=true`` (PRC-C1 / §27).
    turnstile_token: str | None = Field(default=None, max_length=4096)
    #: Дополнительные модули из ``GET /public/platform/catalog/options`` (не должны пересекаться с ``option_keys`` плана).
    extra_entitlement_keys: list[str] = Field(default_factory=list, max_length=32)

    @field_validator("extra_entitlement_keys", mode="before")
    @classmethod
    def _normalize_extra_keys(cls, v: object) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, list):
            return []
        seen: set[str] = set()
        out: list[str] = []
        for item in v:
            s = str(item).strip()
            if not s or len(s) > 128:
                continue
            if s in seen:
                continue
            seen.add(s)
            out.append(s)
            if len(out) >= 32:
                break
        return out


class PlatformSignupCheckoutResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signup_intent_id: str
    payment_url: str
    amount_rub: str
    currency: str = Field(
        default="USD",
        description="Catalog list currency of amount_rub (USD-denominated).",
    )
    charge_currency: str = Field(
        default="RUB",
        description="ISO currency posted to the payment provider. Demo YooKassa rail is RUB with the same numeric amount as the USD list price.",
    )
