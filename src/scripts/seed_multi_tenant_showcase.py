"""Multi-tenant showcase: several organizations, SaaS intents, staff RBAC, clinical demo data.

Fills the **platform founder** dashboard (`compute_platform_founder_dashboard_summary`):
active organizations with non-revoked ``platform_signup_intents`` and catalog-backed MRR.

Also seeds per clinic: owner (RBAC owner), 2× admin, 2× manager, 1× doctor-role staff,
doctors, patients, dense calendar (3 months via extras), a denser English ±14-day window,
and English names / staff / omni via ``showcase_en_video_layer`` + ``showcase_en_demo_window``.

**Not** an Alembic migration: schema stays in Alembic only; run ``alembic upgrade head`` first.

Idempotent: if any ``platform_signup_intents.notes == SEED_MARKER``, the script still applies
SaaS extras (safe after EN titles) and the English video layer, then exits.

Usage:
  poetry run python -m src.scripts.seed_multi_tenant_showcase
  poetry run python -m src.scripts.seed_multi_tenant_showcase --list-credentials

Credentials (local demo only): see ``documentation/DEMO_CREDENTIALS.md``.
"""

from __future__ import annotations

import argparse
import asyncio
import uuid
from datetime import date, datetime, time, timedelta, timezone
from passlib.hash import pbkdf2_sha256
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.omnichannel_dto import NormalizedMessageDTO
from src.application.services.integration_gateway_service import IntegrationGatewayService
from src.application.services.platform_billing_service import resolve_entitlement_keys_for_intent
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic
from src.domain.entities.doctor import Doctor
from src.domain.entities.doctor_working_hours import DoctorWorkingHours
from src.domain.entities.organization import Organization
from src.domain.entities.organization_entitlement import OrganizationEntitlement
from src.domain.entities.patient import Patient
from src.domain.entities.platform_signup_intent import PlatformSignupIntent
from src.domain.entities.service import Service
from src.domain.entities.service_doctor import ServiceDoctor
from src.infrastructure.database.base import AsyncSessionLocal
from src.scripts.seed_rbac_baseline import (
    ensure_role_permissions,
    ensure_user_owner_role,
    ensure_user_role_by_code,
)
from src.scripts.showcase_en_catalog import (
    DOCTORS_TEMPLATE,
    ORG_SPECS,
    PATIENT_NAMES,
    SERVICES_TEMPLATE,
    SHOWCASE_PASSWORD,
    patient_phone,
)
from src.scripts.showcase_en_demo_window import apply_showcase_en_demo_window
from src.scripts.showcase_en_video_layer import apply_showcase_en_video_layer, relabel_platform_catalog_en
from src.scripts.showcase_saas_extras import (
    apply_showcase_saas_extras,
    clear_schedule_cache_best_effort,
    list_showcase_clinic_ids,
)

SEED_MARKER = "seed:multi_tenant_showcase_v1"


def _tariff_snapshot(plan_slug: str) -> dict[str, object]:
    return {
        "plan_slug": plan_slug,
        "billing_period": "monthly",
        "extra_entitlement_keys": [],
    }


async def _replace_org_entitlements(
    session: AsyncSession,
    organization_id: uuid.UUID,
    tariff_snapshot: dict[str, object],
) -> None:
    keys = await resolve_entitlement_keys_for_intent(session, tariff_snapshot)
    await session.execute(
        delete(OrganizationEntitlement).where(
            OrganizationEntitlement.organization_id == organization_id,
        )
    )
    for key in keys:
        session.add(
            OrganizationEntitlement(
                id=uuid.uuid4(),
                organization_id=organization_id,
                entitlement_key=key[:128],
                source="tariff_snapshot",
            )
        )
    await session.flush()


async def _seed_one_org(
    session: AsyncSession,
    spec: dict[str, object],
    org_index: int,
) -> None:
    org = Organization(
        id=uuid.uuid4(),
        name=str(spec["org_name"]),
    )
    session.add(org)
    await session.flush()

    clinic = Clinic(
        id=uuid.uuid4(),
        organization_id=org.id,
        name=str(spec["clinic_name"]),
        phone=f"+7495{1000000 + org_index * 11111:07d}",
        email=f"info.{spec['key']}@showcase-mt.demo",
        address=str(spec.get("address") or f"Demo address, {spec['key']} branch"),
        business_type="stomatology",
        clinic_slug=str(spec["slug"]),
    )
    session.add(clinic)
    await session.flush()

    owner = AdminUser(
        id=uuid.uuid4(),
        clinic_id=clinic.id,
        organization_id=org.id,
        email=str(spec["owner_email"]).strip().lower(),
        password_hash=pbkdf2_sha256.hash(SHOWCASE_PASSWORD),
        full_name=str(spec["owner_name"]),
    )
    session.add(owner)
    await session.flush()
    await ensure_user_owner_role(session, admin_id=owner.id, clinic_id=clinic.id)

    admins_spec = spec["admins"]
    assert isinstance(admins_spec, list)
    for email, full_name in admins_spec:
        u = AdminUser(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            organization_id=org.id,
            email=str(email).strip().lower(),
            password_hash=pbkdf2_sha256.hash(SHOWCASE_PASSWORD),
            full_name=str(full_name),
        )
        session.add(u)
        await session.flush()
        await ensure_user_role_by_code(
            session, admin_id=u.id, clinic_id=clinic.id, role_code="admin"
        )

    marketers_spec = spec["marketers"]
    assert isinstance(marketers_spec, list)
    for email, full_name in marketers_spec:
        u = AdminUser(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            organization_id=org.id,
            email=str(email).strip().lower(),
            password_hash=pbkdf2_sha256.hash(SHOWCASE_PASSWORD),
            full_name=str(full_name),
        )
        session.add(u)
        await session.flush()
        await ensure_user_role_by_code(
            session, admin_id=u.id, clinic_id=clinic.id, role_code="manager"
        )

    snap = _tariff_snapshot(str(spec["plan_slug"]))
    intent = PlatformSignupIntent(
        id=uuid.uuid4(),
        status="active",
        email=owner.email,
        tariff_snapshot=snap,
        organization_id=org.id,
        provisioned_admin_id=owner.id,
        paid_at=datetime.now(timezone.utc) - timedelta(days=30 - org_index * 3),
        notes=SEED_MARKER,
    )
    session.add(intent)
    await session.flush()

    await _replace_org_entitlements(session, org.id, snap)

    doctors: list[Doctor] = []
    for d in DOCTORS_TEMPLATE:
        doc = Doctor(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            full_name=str(d["full_name"]),
            specialization=str(d["specialization"]),
            experience_years=int(d["experience_years"]),
            specialist_role="doctor",
        )
        session.add(doc)
        doctors.append(doc)
    await session.flush()

    for doc in doctors:
        for weekday in range(0, 7):
            session.add(
                DoctorWorkingHours(
                    doctor_id=doc.id,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(18, 0),
                )
            )
    await session.flush()

    services: list[Service] = []
    for name, cat, desc, price, dur in SERVICES_TEMPLATE:
        svc = Service(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            name=name,
            category=cat,
            description=desc,
            price=price,
            duration_minutes=dur,
        )
        session.add(svc)
        services.append(svc)
    await session.flush()

    for di, doc in enumerate(doctors):
        for si, svc in enumerate(services):
            if (di + si) % 2 == 0:
                session.add(
                    ServiceDoctor(
                        service_id=svc.id,
                        doctor_id=doc.id,
                        is_active=True,
                    )
                )
    await session.flush()

    patients: list[Patient] = []
    for i, pn in enumerate(PATIENT_NAMES):
        local = f"p{org_index}.{i}@showcase-mt.demo"
        patient = Patient(
            id=uuid.uuid4(),
            clinic_id=clinic.id,
            phone=patient_phone(str(spec["key"]), i),
            full_name=pn,
            email=local,
            birth_date=date(1978 + (i % 25), 1 + (i % 11), 1 + (i % 20)),
        )
        session.add(patient)
        patients.append(patient)
    await session.flush()

    gateway = IntegrationGatewayService(session=session, business_account_id=clinic.id)
    ext = f"tg_showcase_{spec['key']}"
    await gateway.handle_inbound_normalized_message(
        NormalizedMessageDTO(
            provider="TELEGRAM",
            external_message_id=f"tg-{clinic.id}-showcase",
            from_id=ext,
            chat_external_id=ext,
            text="Hi — I’d like to confirm the interval between visits after implant surgery.",
            timestamp=datetime.now(timezone.utc) - timedelta(hours=2),
        )
    )

    await apply_showcase_saas_extras(session, clinic=clinic, owner_admin_id=owner.id)
    await apply_showcase_en_video_layer(session, clinic=clinic, owner_admin_id=owner.id)
    await apply_showcase_en_demo_window(session, clinic=clinic, owner_admin_id=owner.id)


async def seed_main() -> None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(PlatformSignupIntent).where(PlatformSignupIntent.notes == SEED_MARKER).limit(1)
        )
        if res.scalar_one_or_none() is not None:
            triples = await list_showcase_clinic_ids(session)
            for _org_id, clinic_id, owner_id in triples:
                clinic = await session.get(Clinic, clinic_id)
                if clinic is None:
                    continue
                await apply_showcase_saas_extras(session, clinic=clinic, owner_admin_id=owner_id)
                await apply_showcase_en_video_layer(session, clinic=clinic, owner_admin_id=owner_id)
                await apply_showcase_en_demo_window(session, clinic=clinic, owner_admin_id=owner_id)
            await relabel_platform_catalog_en(session)
            await session.commit()
            await clear_schedule_cache_best_effort()
            print(
                "Multi-tenant showcase already applied (notes marker). "
                f"SaaS extras + English video layer + ±14-day demo window refreshed for {len(triples)} clinic(s)."
            )
            return

        await ensure_role_permissions(session)

        for i, spec in enumerate(ORG_SPECS):
            await _seed_one_org(session, spec, i)

        await relabel_platform_catalog_en(session)
        await session.commit()
        await clear_schedule_cache_best_effort()
        print("Multi-tenant showcase seed OK (5 orgs, EN directory + staff/omni dialogues).")
        print(f"  Shared password: {SHOWCASE_PASSWORD}")
        print("  Human-readable list: documentation/DEMO_CREDENTIALS.md")


def list_credentials() -> None:
    # ASCII-only lines so `python -m ... --list-credentials` works on Windows cp1252 consoles.
    print("# Demo credentials (multi-tenant showcase)\n")
    print(f"Single password for all accounts below: `{SHOWCASE_PASSWORD}`\n")
    print("| Role / site | Email | Display name |")
    print("|---|---|---|")
    for spec in ORG_SPECS:
        key = spec["key"]
        print(f"| Owner — {spec['clinic_name']} (`{key}`) | {spec['owner_email']} | {spec['owner_name']} |")
        admins = spec["admins"]
        assert isinstance(admins, list)
        for email, name in admins:
            print(f"| Admin (`{key}`) | {email} | {name} |")
        marketers = spec["marketers"]
        assert isinstance(marketers, list)
        for email, name in marketers:
            print(f"| Marketer / manager (`{key}`) | {email} | {name} |")
        clinicians = spec.get("clinicians")
        if isinstance(clinicians, list):
            for email, name in clinicians:
                print(f"| Doctor-role staff (`{key}`) | {email} | {name} |")
    print(
        "\nPlatform founder user is not created here; use "
        "`python -m src.scripts.create_platform_founder_user`."
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--list-credentials",
        action="store_true",
        help="Print markdown table to stdout (for docs)",
    )
    args = parser.parse_args()
    if args.list_credentials:
        list_credentials()
        return
    asyncio.run(seed_main())


if __name__ == "__main__":
    main()
