"""Platform SaaS subscription billing (contour B): YooKassa webhook, provisioning, retry/DLQ."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID, uuid4

from passlib.hash import pbkdf2_sha256
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.rbac_user_roles_write import attach_global_role_if_missing
from src.application.webhook_provider_verify import PlatformBillingWebhookProviderVerifyError
from src.core.config import settings
from src.core.metrics import (
    platform_billing_billing_revocation_total,
    platform_billing_gauge_refresh_failures_total,
    platform_billing_payment_lifecycle_total,
    platform_billing_webhook_total,
    platform_provision_attempt_total,
    platform_provision_retry_scheduled_total,
    platform_signup_intent_dead_letter,
    platform_signup_intent_stuck,
    platform_signup_intent_ttl_expired_total,
)
from src.domain.entities.admin_user import EMPLOYMENT_ACTIVE, AdminUser
from src.domain.entities.clinic import Clinic
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.application.services.platform_yookassa_payment import (
    yookassa_payment_payload_indicates_full_refund_revocation,
)
from src.application.services.platform_tariff_payment_gate import (
    BILLING_PERIOD_ANNUAL,
    BILLING_PERIOD_MONTHLY,
    evaluate_platform_payment_against_catalog,
    resolve_platform_checkout_totals,
)
from src.domain.entities.platform_catalog_plan import PlatformCatalogPlan
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.domain.entities.platform_subscription_payment import PlatformSubscriptionPayment
from src.infrastructure.external_apis.yookassa_client import YooKassaClient, YooKassaClientError

logger = logging.getLogger(__name__)

PROVIDER_YOOKASSA = "yookassa"
WEBHOOK_SECRET_HEADER = "X-Platform-Billing-Webhook-Secret"
INVITE_VALID_DAYS = 7
PROVISION_MAX_RETRIES = 8
BILLING_REVOKED_ENTITLEMENT_KEY = "saas.billing_revoked"
ENTITLEMENT_SOURCE_BILLING_REVOCATION = "billing_revocation"

# Не тратить backoff/DLQ на ошибки, которые не «вылечатся» сами (гейт, отсутствие succeeded pay).
PERMANENT_PROVISION_BLOCK_CODES = frozenset(
    {
        "amount_mismatch_catalog",
        "invalid_billing_period",
        "billing_period_requires_plan_slug",
        "unknown_plan_slug",
        "missing_payment_amount",
        "payment_not_succeeded",
        "tariff_snapshot_invalid",
    }
)


class PlatformProvisionRetryNotAllowed(Exception):
    """Founder force-retry denied (wrong lifecycle / payment)."""

    __slots__ = ("code",)

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def provision_backoff_seconds(retry_count: int) -> int:
    return min(3600, 30 * (2 ** min(retry_count, 12)))


async def apply_platform_billing_revocation_after_refund(
    session: AsyncSession,
    intent: PlatformSignupIntent,
) -> None:
    """
    ADR-012: idempotent revoke of tariff_snapshot (and prior revocation marker) entitlements;
    intent → suspended + billing_revoked_at; org row kept for audit.
    """
    if intent.organization_id is None:
        platform_billing_billing_revocation_total.labels(result="skipped_no_org").inc()
        return
    if intent.billing_revoked_at is not None:
        platform_billing_billing_revocation_total.labels(result="skipped_idempotent").inc()
        return

    await session.execute(
        delete(OrganizationEntitlement).where(
            and_(
                OrganizationEntitlement.organization_id == intent.organization_id,
                OrganizationEntitlement.source.in_(
                    ("tariff_snapshot", ENTITLEMENT_SOURCE_BILLING_REVOCATION)
                ),
            )
        )
    )
    session.add(
        OrganizationEntitlement(
            organization_id=intent.organization_id,
            entitlement_key=BILLING_REVOKED_ENTITLEMENT_KEY[:128],
            source=ENTITLEMENT_SOURCE_BILLING_REVOCATION,
        )
    )
    intent.status = "suspended"
    intent.billing_revoked_at = datetime.now(UTC)
    platform_billing_billing_revocation_total.labels(result="applied").inc()
    logger.info(
        "Platform billing: ADR-012 billing revocation applied",
        extra={"intent_id": str(intent.id), "org_id": str(intent.organization_id)},
    )


def verify_platform_billing_webhook_secret(header_value: str | None) -> bool:
    """Constant-time compare (str API, Python 3.11+); False if secret not configured."""
    expected = (settings.platform_billing_webhook_secret or "").strip()
    if not expected or not header_value:
        return False
    return secrets.compare_digest(header_value.strip(), expected)


def _invite_token_sha256_hex(token: str) -> str:
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def entitlement_keys_from_tariff_snapshot(raw: dict[str, Any] | list[Any] | None) -> list[str]:
    """Resolve entitlement keys from JSON tariff_snapshot; always includes core.base (master plan §4)."""
    if raw is None:
        return ["core.base"]
    if isinstance(raw, list):
        out = [str(x).strip() for x in raw if x is not None and str(x).strip()]
        base = out or []
    elif isinstance(raw, dict):
        keys = raw.get("entitlement_keys") or raw.get("keys")
        if isinstance(keys, list):
            base = [str(x).strip() for x in keys if x is not None and str(x).strip()]
        else:
            base = []
    else:
        base = []
    merged = ["core.base", *base] if "core.base" not in base else base
    return list(dict.fromkeys(merged))


async def resolve_entitlement_keys_for_intent(
    session: AsyncSession,
    raw: dict[str, Any] | list[Any] | None,
) -> list[str]:
    """Merge catalog plan slug (DB) with snapshot keys."""
    merged: list[str] = []
    if isinstance(raw, dict) and raw.get("plan_slug"):
        slug = str(raw["plan_slug"]).strip().lower()
        if slug:
            res = await session.execute(
                select(PlatformCatalogPlan).where(
                    PlatformCatalogPlan.slug == slug,
                    PlatformCatalogPlan.is_active.is_(True),
                ).limit(1)
            )
            plan = res.scalar_one_or_none()
            if plan and plan.option_keys:
                merged.extend(str(x).strip() for x in plan.option_keys if x is not None and str(x).strip())
    merged.extend(entitlement_keys_from_tariff_snapshot(raw))
    if isinstance(raw, dict):
        extras = raw.get("extra_entitlement_keys")
        if isinstance(extras, list):
            merged.extend(str(x).strip() for x in extras if x is not None and str(x).strip())
    return list(dict.fromkeys(merged))


async def _replace_org_entitlements(
    session: AsyncSession,
    organization_id: UUID,
    keys: list[str],
) -> None:
    await session.execute(
        delete(OrganizationEntitlement).where(OrganizationEntitlement.organization_id == organization_id)
    )
    uniq = list(dict.fromkeys(keys))
    for key in uniq:
        session.add(
            OrganizationEntitlement(
                organization_id=organization_id,
                entitlement_key=key[:128],
                source="tariff_snapshot",
            )
        )


async def _provision_owner_invite(
    session: AsyncSession,
    intent: PlatformSignupIntent,
    organization_id: UUID,
    clinic_id: UUID,
) -> None:
    """Create first AdminUser with owner role + one-time invite hash (email required)."""
    if intent.provisioned_admin_id is not None:
        return
    email = (intent.email or "").strip().lower()
    if not email:
        logger.info(
            "Platform provision: no email on intent, skip owner admin",
            extra={"intent_id": str(intent.id)},
        )
        return

    existing = await session.execute(
        select(AdminUser).where(AdminUser.email == email, AdminUser.deleted_at.is_(None)).limit(1)
    )
    if existing.scalar_one_or_none() is not None:
        logger.warning(
            "Platform provision: admin email already exists, cannot attach owner",
            extra={"email": email, "intent_id": str(intent.id)},
        )
        raise ValueError("platform_signup_owner_email_already_registered")

    admin = AdminUser(
        clinic_id=clinic_id,
        organization_id=organization_id,
        email=email,
        password_hash=pbkdf2_sha256.hash(secrets.token_urlsafe(48)),
        full_name=None,
        employment_status=EMPLOYMENT_ACTIVE,
    )
    session.add(admin)
    await session.flush()

    await attach_global_role_if_missing(session, user_id=admin.id, clinic_id=clinic_id, role_code="owner")

    raw_token = secrets.token_urlsafe(32)
    intent.provisioned_admin_id = admin.id
    intent.owner_invite_token_hash = _invite_token_sha256_hex(raw_token)
    intent.owner_invite_expires_at = datetime.now(UTC) + timedelta(days=INVITE_VALID_DAYS)
    logger.info(
        "Platform provision: owner invite issued (token not logged; deliver via secure channel)",
        extra={"intent_id": str(intent.id), "admin_id": str(admin.id)},
    )


async def _latest_succeeded_yookassa_payment(
    session: AsyncSession,
    intent_id: UUID,
) -> PlatformSubscriptionPayment | None:
    stmt = (
        select(PlatformSubscriptionPayment)
        .where(
            PlatformSubscriptionPayment.signup_intent_id == intent_id,
            PlatformSubscriptionPayment.provider == PROVIDER_YOOKASSA,
            PlatformSubscriptionPayment.status == "succeeded",
        )
        .order_by(PlatformSubscriptionPayment.updated_at.desc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def execute_platform_provision(session: AsyncSession, intent: PlatformSignupIntent) -> None:
    """
    Create org/clinic/entitlements/owner when payment succeeded.
    Idempotent if already active with organization_id.
    """
    if intent.status == "active" and intent.organization_id is not None:
        return
    if intent.provision_dead_letter or intent.status == "dead_letter":
        logger.warning(
            "execute_platform_provision skipped: dead letter",
            extra={"intent_id": str(intent.id)},
        )
        return
    if intent.billing_revoked_at is not None or intent.status == "suspended":
        logger.warning(
            "execute_platform_provision skipped: billing revoked or suspended",
            extra={"intent_id": str(intent.id)},
        )
        return

    pay_ok = await _latest_succeeded_yookassa_payment(session, intent.id)
    if pay_ok is None:
        raise PlatformProvisionRetryNotAllowed("payment_not_succeeded")

    gate_reason = await evaluate_platform_payment_against_catalog(
        session,
        intent.tariff_snapshot,
        pay_ok.amount,
    )
    if gate_reason:
        raise PlatformProvisionRetryNotAllowed(gate_reason)

    clinic: Clinic | None = None
    if intent.organization_id is None:
        org_name = "New organization"
        if intent.email:
            org_name = f"Org ({intent.email[:80]})"
        org = Organization(name=org_name[:255])
        session.add(org)
        await session.flush()

        slug_base = f"p-{intent.id.hex[:20]}"
        clinic = Clinic(
            name="Main clinic",
            organization_id=org.id,
            clinic_slug=slug_base[:120],
        )
        session.add(clinic)
        await session.flush()
        intent.organization_id = org.id
    else:
        cres = await session.execute(
            select(Clinic).where(Clinic.organization_id == intent.organization_id).limit(1)
        )
        clinic = cres.scalar_one_or_none()

    if intent.organization_id is not None:
        keys = await resolve_entitlement_keys_for_intent(session, intent.tariff_snapshot)
        await _replace_org_entitlements(session, intent.organization_id, keys)
    if clinic is not None and intent.organization_id is not None:
        await _provision_owner_invite(session, intent, intent.organization_id, clinic.id)

    intent.status = "active"
    intent.provision_retry_count = 0
    intent.provision_last_error = None
    intent.provision_next_attempt_at = None
    intent.provision_dead_letter = False
    await session.flush()
    platform_provision_attempt_total.labels(result="success").inc()
    logger.info(
        "Platform billing: provisioned",
        extra={"intent_id": str(intent.id), "org_id": str(intent.organization_id)},
    )


async def record_platform_provision_failure(
    session: AsyncSession,
    intent_id: UUID,
    exc: BaseException,
) -> None:
    intent = await session.get(PlatformSignupIntent, intent_id)
    if intent is None:
        return

    if isinstance(exc, PlatformProvisionRetryNotAllowed) and exc.code in PERMANENT_PROVISION_BLOCK_CODES:
        intent.provision_last_error = f"provision_blocked:{exc.code}"[:2000]
        intent.status = "provision_failed"
        intent.provision_next_attempt_at = None
        platform_provision_attempt_total.labels(result="permanent_block").inc()
        logger.warning(
            "Platform provision blocked permanently (no Celery backoff; fix data or catalog)",
            extra={"intent_id": str(intent_id), "code": exc.code},
        )
        await session.flush()
        return

    intent.provision_retry_count = int(intent.provision_retry_count or 0) + 1
    intent.provision_last_error = f"{type(exc).__name__}: {exc}"[:2000]
    intent.status = "provision_failed"
    if intent.provision_retry_count >= PROVISION_MAX_RETRIES:
        intent.provision_dead_letter = True
        intent.status = "dead_letter"
        intent.provision_next_attempt_at = None
        platform_provision_attempt_total.labels(result="dlq").inc()
        logger.error(
            "Platform provision DLQ",
            extra={"intent_id": str(intent_id), "retries": intent.provision_retry_count},
        )
    else:
        intent.provision_next_attempt_at = datetime.now(UTC) + timedelta(
            seconds=provision_backoff_seconds(intent.provision_retry_count)
        )
        platform_provision_retry_scheduled_total.inc()
        platform_provision_attempt_total.labels(result="failed").inc()
    await session.flush()


async def apply_platform_yookassa_notification(session: AsyncSession, payload: dict[str, Any]) -> UUID | None:
    """
    Verify payment with YooKassa, update payment row (all statuses).
    Returns signup intent id to run provisioning (succeeded & not yet active), else None.
    """
    obj = payload.get("object") or payload
    payment_id = obj.get("id") if isinstance(obj, dict) else None
    if not payment_id:
        logger.warning(
            "Platform billing webhook: missing payment id",
            extra={"payload_keys": list(payload.keys())},
        )
        platform_billing_webhook_total.labels(result="missing_payment_id").inc()
        return None

    stmt = (
        select(PlatformSubscriptionPayment, PlatformSignupIntent)
        .join(
            PlatformSignupIntent,
            PlatformSignupIntent.id == PlatformSubscriptionPayment.signup_intent_id,
        )
        .where(
            PlatformSubscriptionPayment.provider == PROVIDER_YOOKASSA,
            PlatformSubscriptionPayment.provider_payment_id == str(payment_id),
        )
        .limit(1)
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if not row:
        logger.warning(
            "Platform billing webhook: unknown provider_payment_id",
            extra={"provider_payment_id": payment_id},
        )
        platform_billing_webhook_total.labels(result="unknown_payment").inc()
        return None

    pay, intent = row[0], row[1]

    yookassa = YooKassaClient()
    try:
        data = await asyncio.to_thread(yookassa.get_payment, str(payment_id))
    except YooKassaClientError:
        logger.exception(
            "Platform billing webhook: YooKassa get_payment failed",
            extra={"payment_id": payment_id},
        )
        raise PlatformBillingWebhookProviderVerifyError(str(payment_id)) from None

    status = (data.get("status") or "").lower()
    amount_val = data.get("amount")
    if isinstance(amount_val, dict) and amount_val.get("value") is not None:
        try:
            pay.amount = Decimal(str(amount_val["value"]))
        except Exception:
            pass
    pay.currency = str((amount_val or {}).get("currency") or pay.currency or "RUB")
    pay.webhook_payload = data

    # ADR-012 / PRC-B5: refund-like outcomes — см. platform_yookassa_payment (OpenAPI + refunded_amount).
    if yookassa_payment_payload_indicates_full_refund_revocation(data):
        pay.status = "refunded"
        platform_billing_payment_lifecycle_total.labels(event="refunded").inc()
        await apply_platform_billing_revocation_after_refund(session, intent)
        await session.flush()
        platform_billing_webhook_total.labels(result="refund_reconciled").inc()
        return None

    # Happy path: succeeded without full refund (partial refund leaves status succeeded — отдельная политика).
    if status == "succeeded":
        pay.status = "succeeded"
        platform_billing_payment_lifecycle_total.labels(event="succeeded").inc()

        if intent.status == "dead_letter" or intent.provision_dead_letter:
            await session.flush()
            platform_billing_webhook_total.labels(result="skipped_dead_letter").inc()
            return None

        if intent.billing_revoked_at is not None or intent.status == "suspended":
            await session.flush()
            platform_billing_webhook_total.labels(result="skipped_billing_revoked").inc()
            return None

        if intent.status == "active" and intent.organization_id is not None:
            await session.flush()
            platform_billing_webhook_total.labels(result="idempotent_ok").inc()
            return None

        gate_reason = await evaluate_platform_payment_against_catalog(
            session,
            intent.tariff_snapshot,
            pay.amount,
        )
        if gate_reason:
            intent.provision_last_error = f"tariff_gate:{gate_reason}"[:2000]
            await session.flush()
            platform_billing_webhook_total.labels(result=gate_reason).inc()
            return None

        intent.provision_last_error = None

        if intent.paid_at is None:
            intent.paid_at = datetime.now(UTC)
        if intent.status in ("pending_payment", "provision_failed", "expired"):
            intent.status = "paid"
            intent.provision_dead_letter = False
        await session.flush()
        if settings.domain_outbox_platform_billing_provision_enabled:
            from src.application.services.domain_outbox_service import enqueue_platform_signup_provision

            await enqueue_platform_signup_provision(session, intent.id)
        platform_billing_webhook_total.labels(result="success").inc()
        return intent.id

    if status in ("canceled", "cancelled"):
        pay.status = "canceled"
        platform_billing_payment_lifecycle_total.labels(event="canceled").inc()
    elif status == "pending":
        pay.status = "pending"
        platform_billing_payment_lifecycle_total.labels(event="pending").inc()
    elif status == "waiting_for_capture":
        pay.status = "waiting_for_capture"
        platform_billing_payment_lifecycle_total.labels(event="waiting_for_capture").inc()
    else:
        pay.status = (status[:28] + "..") if len(status) > 30 else (status or "unknown")
        platform_billing_payment_lifecycle_total.labels(event="other").inc()

    await session.flush()
    platform_billing_webhook_total.labels(result="ignored_status").inc()
    return None


async def handle_platform_billing_webhook_two_phase(
    session: AsyncSession,
    payload: dict[str, Any],
) -> None:
    """
    Commit payment notification, then provision in a second transaction.
    Provision failures become retry/DLQ without failing the HTTP handler.
    """
    intent_id = await apply_platform_yookassa_notification(session, payload)
    await session.commit()

    if intent_id is None:
        return

    if settings.domain_outbox_platform_billing_provision_enabled:
        from src.application.services.domain_outbox_service import dispatch_domain_outbox_batch

        await dispatch_domain_outbox_batch()
        return

    try:
        intent = await session.get(PlatformSignupIntent, intent_id)
        if intent is None:
            return
        await execute_platform_provision(session, intent)
        await session.commit()
    except PlatformProvisionRetryNotAllowed as exc:
        await session.rollback()
        logger.warning(
            "Platform provision blocked after paid webhook",
            extra={"intent_id": str(intent_id), "code": exc.code},
        )
        try:
            await record_platform_provision_failure(session, intent_id, exc)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Platform provision failure could not be recorded",
                extra={"intent_id": str(intent_id)},
            )
    except Exception as exc:
        await session.rollback()
        logger.exception(
            "Platform provision failed after paid webhook",
            extra={"intent_id": str(intent_id)},
        )
        try:
            await record_platform_provision_failure(session, intent_id, exc)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception(
                "Platform provision failure could not be recorded",
                extra={"intent_id": str(intent_id)},
            )


async def run_due_platform_provisions(session: AsyncSession, *, limit: int = 20) -> int:
    """Celery/OPS: retry paid/failed intents that are due. Returns success count."""
    now = datetime.now(UTC)
    stmt = (
        select(PlatformSignupIntent.id)
        .where(
            PlatformSignupIntent.provision_dead_letter.is_(False),
            PlatformSignupIntent.provision_retry_count < PROVISION_MAX_RETRIES,
            or_(
                PlatformSignupIntent.provision_last_error.is_(None),
                ~PlatformSignupIntent.provision_last_error.like("provision_blocked:%"),
            ),
            or_(
                PlatformSignupIntent.status == "provision_failed",
                and_(
                    PlatformSignupIntent.status == "paid",
                    PlatformSignupIntent.organization_id.is_(None),
                ),
            ),
            or_(
                PlatformSignupIntent.provision_next_attempt_at.is_(None),
                PlatformSignupIntent.provision_next_attempt_at <= now,
            ),
        )
        .order_by(
            PlatformSignupIntent.provision_next_attempt_at.asc().nullsfirst(),
            PlatformSignupIntent.paid_at.asc().nullsfirst(),
        )
        .limit(limit)
    )
    ids = [row[0] for row in (await session.execute(stmt)).all()]
    ok = 0
    for iid in ids:
        try:
            intent_row = await session.get(PlatformSignupIntent, iid)
            if intent_row is None:
                continue
            await execute_platform_provision(session, intent_row)
            await session.commit()
            ok += 1
        except PlatformProvisionRetryNotAllowed as exc:
            await session.rollback()
            logger.warning(
                "Celery platform provision blocked",
                extra={"intent_id": str(iid), "code": exc.code},
            )
            try:
                await record_platform_provision_failure(session, iid, exc)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("record_platform_provision_failure failed", extra={"intent_id": str(iid)})
        except Exception as exc:
            await session.rollback()
            try:
                await record_platform_provision_failure(session, iid, exc)
                await session.commit()
            except Exception:
                await session.rollback()
                logger.exception("record_platform_provision_failure failed", extra={"intent_id": str(iid)})
    if ok:
        logger.info("Celery platform provision batch", extra={"success": ok, "candidates": len(ids)})
    return ok


async def expire_stale_platform_signup_intents(session: AsyncSession, *, limit: int = 500) -> int:
    """
    Mark overdue pending_payment intents as expired (privacy TTL / PRC-C2).

    Skips rows that already have a payment in succeeded or waiting_for_capture so a late
    webhook can still reconcile (see apply_platform_yookassa_notification).
    """
    now = datetime.now(UTC)
    busy_payment = (
        select(PlatformSubscriptionPayment.id)
        .where(
            PlatformSubscriptionPayment.signup_intent_id == PlatformSignupIntent.id,
            PlatformSubscriptionPayment.status.in_(("succeeded", "waiting_for_capture")),
        )
        .exists()
    )
    stmt = (
        select(PlatformSignupIntent)
        .where(
            PlatformSignupIntent.status == "pending_payment",
            PlatformSignupIntent.expires_at.isnot(None),
            PlatformSignupIntent.expires_at < now,
            ~busy_payment,
        )
        .limit(limit)
    )
    rows = list((await session.execute(stmt)).scalars().all())
    n = 0
    for intent in rows:
        intent.status = "expired"
        n += 1
    if n:
        await session.flush()
        platform_signup_intent_ttl_expired_total.inc(n)
        logger.info("Expired stale platform signup intents", extra={"count": n})
    return n


async def create_public_platform_signup_checkout(
    session: AsyncSession,
    *,
    email: str,
    plan_slug: str,
    billing_period: str,
    return_url: str,
    extra_entitlement_keys: list[str] | None = None,
) -> tuple[UUID, str, Decimal]:
    """
    Public self-service: create signup intent + pending YooKassa payment (1b-E1 / 1b-F5).
    Caller must commit the session on success.
    """
    email_norm = (email or "").strip().lower()
    if not email_norm or "@" not in email_norm:
        raise ValueError("invalid_email")

    slug = (plan_slug or "").strip().lower()
    if not slug:
        raise ValueError("invalid_plan_slug")

    bp = (billing_period or "").strip().lower()
    if bp not in (BILLING_PERIOD_MONTHLY, BILLING_PERIOD_ANNUAL):
        raise ValueError("invalid_billing_period")

    extras_in = list(extra_entitlement_keys or [])
    try:
        amount, extras_norm = await resolve_platform_checkout_totals(
            session,
            plan_slug=slug,
            billing_period=bp,
            extra_entitlement_keys=extras_in,
        )
    except ValueError as exc:
        raise ValueError(str(exc)) from None

    ttl_days = max(1, int(settings.platform_signup_intent_payment_ttl_days))
    snapshot: dict[str, Any] = {"plan_slug": slug, "billing_period": bp}
    if extras_norm:
        snapshot["extra_entitlement_keys"] = extras_norm

    intent = PlatformSignupIntent(
        email=email_norm,
        tariff_snapshot=snapshot,
        status="pending_payment",
        expires_at=datetime.now(UTC) + timedelta(days=ttl_days),
    )
    session.add(intent)
    await session.flush()

    yk = YooKassaClient()
    if not yk.is_configured():
        raise ValueError("yookassa_not_configured")

    desc = f"SaaS {slug} ({bp})"[:255]
    pay_row_id = uuid4()
    pay_row = PlatformSubscriptionPayment(
        id=pay_row_id,
        signup_intent_id=intent.id,
        provider=PROVIDER_YOOKASSA,
        provider_payment_id=f"local-pending:{pay_row_id}",
        amount=amount,
        status="pending",
    )
    session.add(pay_row)
    await session.flush()

    try:
        pid, pay_url = await asyncio.to_thread(
            yk.create_platform_subscription_payment,
            amount,
            return_url,
            desc,
            intent.id,
            str(pay_row_id),
        )
    except YooKassaClientError as exc:
        await session.delete(pay_row)
        await session.flush()
        raise ValueError("yookassa_create_failed") from exc

    pay_row.provider_payment_id = str(pid)
    await session.flush()
    return intent.id, pay_url, amount


async def admin_force_retry_platform_provision(session: AsyncSession, intent_id: UUID) -> None:
    intent = await session.get(PlatformSignupIntent, intent_id)
    if intent is None:
        raise LookupError("intent_not_found")

    if intent.billing_revoked_at is not None or intent.status == "suspended":
        raise PlatformProvisionRetryNotAllowed("billing_revoked")

    if intent.status == "active" and intent.organization_id is not None:
        return

    if intent.status not in (
        "paid",
        "provision_failed",
        "dead_letter",
        "active",
        "pending_payment",
        "expired",
    ):
        raise PlatformProvisionRetryNotAllowed("invalid_intent_status_for_retry")

    pay_stmt = (
        select(PlatformSubscriptionPayment)
        .where(
            PlatformSubscriptionPayment.signup_intent_id == intent_id,
            PlatformSubscriptionPayment.provider == PROVIDER_YOOKASSA,
        )
        .order_by(PlatformSubscriptionPayment.updated_at.desc())
        .limit(1)
    )
    pay = (await session.execute(pay_stmt)).scalar_one_or_none()
    if pay is None or str(pay.status or "").lower() != "succeeded":
        raise PlatformProvisionRetryNotAllowed("payment_not_succeeded")

    intent.provision_dead_letter = False
    intent.provision_retry_count = 0
    intent.provision_last_error = None
    intent.provision_next_attempt_at = None
    intent.status = "paid"
    await execute_platform_provision(session, intent)


async def admin_mark_platform_provision_closed(
    session: AsyncSession,
    intent_id: UUID,
    *,
    note: str | None = None,
) -> Literal["applied", "noop"]:
    """
    Founder manual reconcile: close stuck/DLQ intent as terminal without SQL edits.

    Clears ``provision_dead_letter`` so DLQ gauges do not count resolved closures.
    Idempotent: already ``reconcile_closed_manual`` or active+org → ``noop``.
    """
    intent = await session.get(PlatformSignupIntent, intent_id)
    if intent is None:
        raise LookupError("intent_not_found")
    if intent.billing_revoked_at is not None or intent.status == "suspended":
        raise PlatformProvisionRetryNotAllowed("billing_revoked")
    if intent.status == "active" and intent.organization_id is not None:
        return "noop"
    if intent.status == "reconcile_closed_manual":
        return "noop"
    if intent.status not in ("provision_failed", "dead_letter"):
        raise PlatformProvisionRetryNotAllowed("invalid_intent_status_for_manual_close")
    if note:
        note_clean = note.strip()
        if note_clean:
            intent.notes = (intent.notes or "") + (("\n" if intent.notes else "") + note_clean[:1000])
    intent.provision_next_attempt_at = None
    intent.provision_dead_letter = False
    intent.status = "reconcile_closed_manual"
    if not intent.provision_last_error:
        intent.provision_last_error = "manual_reconcile_closed"
    await session.flush()
    return "applied"


async def rotate_platform_owner_invite_token(
    session: AsyncSession,
    intent_id: UUID,
) -> tuple[str, datetime]:
    """
    Mint a new one-time owner invite token (invalidates previous hash).

    Raises LookupError if intent missing or owner admin not provisioned yet.
    """
    intent = await session.get(PlatformSignupIntent, intent_id)
    if intent is None or intent.provisioned_admin_id is None:
        raise LookupError("intent_not_ready")
    raw_token = secrets.token_urlsafe(32)
    intent.owner_invite_token_hash = _invite_token_sha256_hex(raw_token)
    intent.owner_invite_expires_at = datetime.now(UTC) + timedelta(days=INVITE_VALID_DAYS)
    await session.flush()
    return raw_token, intent.owner_invite_expires_at


async def accept_platform_owner_invite(
    session: AsyncSession,
    *,
    token: str,
    password: str,
) -> UUID:
    """
    Set password for provisioned owner admin; clears invite hash.

    Raises ValueError with short code: password_too_short, invalid_or_expired_token.
    """
    if len(password) < 8:
        raise ValueError("password_too_short")
    h = _invite_token_sha256_hex(token)
    res = await session.execute(
        select(PlatformSignupIntent).where(PlatformSignupIntent.owner_invite_token_hash == h).limit(1)
    )
    intent = res.scalar_one_or_none()
    if intent is None:
        raise ValueError("invalid_or_expired_token")
    if intent.owner_invite_expires_at is not None and intent.owner_invite_expires_at < datetime.now(UTC):
        raise ValueError("invalid_or_expired_token")
    if intent.provisioned_admin_id is None:
        raise ValueError("invalid_or_expired_token")

    admin = await session.get(AdminUser, intent.provisioned_admin_id)
    if admin is None or admin.deleted_at is not None:
        raise ValueError("invalid_or_expired_token")

    admin.password_hash = pbkdf2_sha256.hash(password)
    intent.owner_invite_token_hash = None
    intent.owner_invite_expires_at = None
    await session.flush()
    return admin.id


async def list_platform_provision_queue(
    session: AsyncSession,
    *,
    limit: int = 100,
) -> list[PlatformSignupIntent]:
    """Operational queue: reconcile states + tariff_gate stuck on pending_payment (1b-E3b §7)."""
    stmt = (
        select(PlatformSignupIntent)
        .where(
            or_(
                PlatformSignupIntent.status.in_(("paid", "provision_failed", "dead_letter", "suspended")),
                and_(
                    PlatformSignupIntent.status == "pending_payment",
                    PlatformSignupIntent.provision_last_error.isnot(None),
                    PlatformSignupIntent.provision_last_error.like("tariff_gate:%"),
                ),
            ),
        )
        .order_by(PlatformSignupIntent.updated_at.desc())
        .limit(limit)
    )
    return list((await session.scalars(stmt)).all())


def signup_intent_row_matches_dead_letter_gauge(
    *,
    status: str | None,
    provision_dead_letter: bool | None,
) -> bool:
    """Must match DLQ count SQL in ``refresh_platform_billing_provision_gauges`` (unit tests)."""
    st = (status or "").strip()
    if st == "reconcile_closed_manual":
        return False
    if provision_dead_letter:
        return True
    return st == "dead_letter"


_platform_billing_gauge_refresh_ok_at_monotonic: float = 0.0


async def refresh_platform_billing_provision_gauges(*, force: bool = False) -> None:
    """Update stuck / DLQ gauges for Prometheus scrape (1b-E4)."""
    global _platform_billing_gauge_refresh_ok_at_monotonic
    from src.infrastructure.database.base import AsyncSessionLocal

    if AsyncSessionLocal is None:
        return

    interval = settings.platform_billing_metrics_db_refresh_min_interval_seconds
    now_mono = time.monotonic()
    if (
        not force
        and interval > 0
        and _platform_billing_gauge_refresh_ok_at_monotonic > 0
        and (now_mono - _platform_billing_gauge_refresh_ok_at_monotonic) < interval
    ):
        return

    try:
        async with AsyncSessionLocal() as session:
            stuck_where = or_(
                PlatformSignupIntent.status.in_(("paid", "provision_failed")),
                and_(
                    PlatformSignupIntent.status == "pending_payment",
                    PlatformSignupIntent.provision_last_error.isnot(None),
                    PlatformSignupIntent.provision_last_error.like("tariff_gate:%"),
                ),
            )
            stuck_n = int(
                (
                    await session.execute(
                        select(func.count())
                        .select_from(PlatformSignupIntent)
                        .where(
                            PlatformSignupIntent.provision_dead_letter.is_(False),
                            stuck_where,
                        )
                    )
                ).scalar_one()
                or 0
            )
            platform_signup_intent_stuck.set(float(stuck_n))

            dlq_n = int(
                (
                    await session.execute(
                        select(func.count())
                        .select_from(PlatformSignupIntent)
                        .where(
                            and_(
                                or_(
                                    PlatformSignupIntent.provision_dead_letter.is_(True),
                                    PlatformSignupIntent.status == "dead_letter",
                                ),
                                PlatformSignupIntent.status != "reconcile_closed_manual",
                            )
                        )
                    )
                ).scalar_one()
                or 0
            )
            platform_signup_intent_dead_letter.set(float(dlq_n))

        _platform_billing_gauge_refresh_ok_at_monotonic = time.monotonic()
    except Exception:
        platform_billing_gauge_refresh_failures_total.inc()
        logger.warning("refresh_platform_billing_provision_gauges failed", exc_info=True)
