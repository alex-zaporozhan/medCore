"""
DEV ONLY: Staff (admins, roles), tasks, task comments, extra cashbox activity.

- Ensures permissions and clinic roles exist; creates extra admins (manager, executors, reception).
- Links admins to roles (UserRole).
- Creates many tasks (open, in_progress, done, cancelled) with assignees and optional links to bookings/patients/leads.
- Adds task comments.
- Adds extra financial_transactions (income/expense/transfer) so cashbox and reports look busy.

Requires: seed_demo_data, seed_dev_full_demo, seed_dev_leads_notes_recall (for leads/bookings).

Run:
  poetry run python -m src.scripts.dev.seed_dev_staff_tasks_cash
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import date, datetime, timedelta, time
from decimal import Decimal

from sqlalchemy import select
from passlib.hash import pbkdf2_sha256

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.clinic import Clinic
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.role import Role
from src.domain.entities.permission import Permission
from src.domain.entities.role_permission import RolePermission
from src.domain.entities.user_role import UserRole
from src.domain.entities.task import Task
from src.domain.entities.task_comment import TaskComment
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.booking import Booking
from src.domain.entities.payment import Payment  # FK financial_transactions.payment_id
from src.domain.entities.patient import Patient
from src.domain.entities.lead_card import LeadCard
from src.domain.entities.product import Product  # FK tasks.inventory_product_id
from src.application.rbac_matrix import PERMISSIONS, ROLE_PERMISSIONS

DEMO_PASSWORD_HASH = pbkdf2_sha256.hash("admin12345")

EXTRA_ADMINS = [
    ("manager@example.com", "Manager Demo"),
    ("executor1@example.com", "Executor One"),
    ("executor2@example.com", "Executor Two"),
    ("reception@example.com", "Reception Demo"),
]

TASK_TITLES = [
    "Confirm tomorrow's appointments",
    "Call back lead from site",
    "Prepare room for implant surgery",
    "Order consumables",
    "Send reminder to patient",
    "Update price list in CRM",
    "Check cashbox balance",
    "Prepare report for owner",
    "Follow up: no-show patient",
    "Schedule hygiene reminder",
    "Verify insurance for visit",
    "Prepare documents for new patient",
    "Review recall campaign stats",
    "Close completed lead",
    "Refund processing",
]

TASK_DESCRIPTIONS = [
    "Call each patient to confirm attendance.",
    "Lead asked for a quote on whitening.",
    "Sterilize and set up instruments.",
    "Gloves, masks, napkins - check warehouse.",
    "Patient requested SMS reminder.",
    None,
    "Reconcile with bank statement.",
    "Weekly summary for management.",
    "Patient did not show up last week.",
    "Send recall message for hygiene segment.",
    "Policy number and coverage.",
    "Contract, consent, PD agreement.",
    "Open/click rates from last campaign.",
    "Move to Success stage, add note.",
    "Patient requested refund for cancelled visit.",
]

FIN_EXPENSE_DESCRIPTIONS = [
    "Consumables (gloves, masks)",
    "Rent (monthly)",
    "Utilities",
    "Disinfection supplies",
    "Lab work (outsource)",
    "Equipment maintenance",
    "Marketing (Yandex)",
]

FIN_INCOME_DESCRIPTIONS = [
    "Miscellaneous income",
    "Gift certificate sale",
    "Late cancellation fee",
]


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1)
        )
        clinic = res.scalar_one_or_none()
        if not clinic:
            print("Error: no clinic. Run seed_demo_data first.")
            return

        clinic_id = clinic.id
        today = date.today()

        # --- 1) Permissions (global): ensure all from rbac_matrix exist ---
        for p in PERMISSIONS:
            r = await session.execute(
                select(Permission).where(Permission.code == p.code).limit(1)
            )
            if r.scalar_one_or_none() is None:
                session.add(
                    Permission(id=uuid.uuid4(), code=p.code, description=p.description)
                )
        await session.flush()

        # --- 2) Roles (global, clinic_id=None): owner, manager, admin, doctor ---
        role_codes = ["owner", "manager", "admin", "doctor"]
        roles_by_code: dict[str, Role] = {}
        for code in role_codes:
            r = await session.execute(
                select(Role).where(
                    Role.code == code,
                    Role.clinic_id.is_(None),
                ).limit(1)
            )
            role = r.scalar_one_or_none()
            if role is None:
                role = Role(
                    id=uuid.uuid4(),
                    clinic_id=None,
                    code=code,
                    name=code.capitalize(),
                    description=f"Base role {code}",
                )
                session.add(role)
                await session.flush()
            roles_by_code[code] = role

        # --- 3) RolePermission: link roles to permissions ---
        perm_by_code: dict[str, uuid.UUID] = {}
        res = await session.execute(select(Permission))
        for p in res.scalars().all():
            perm_by_code[p.code] = p.id

        for role_code, perm_codes in ROLE_PERMISSIONS.items():
            role = roles_by_code.get(role_code)
            if not role:
                continue
            for pcode in perm_codes:
                perm_id = perm_by_code.get(pcode)
                if not perm_id:
                    continue
                existing = await session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm_id,
                    ).limit(1)
                )
                if existing.scalar_one_or_none() is None:
                    session.add(
                        RolePermission(
                            id=uuid.uuid4(),
                            role_id=role.id,
                            permission_id=perm_id,
                        )
                    )
        await session.flush()

        # --- 4) Admins: ensure main admin + extra staff ---
        res = await session.execute(
            select(AdminUser).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
            ).order_by(AdminUser.email)
        )
        existing_admins = list(res.scalars().all())
        existing_emails = {a.email for a in existing_admins}

        for email, full_name in EXTRA_ADMINS:
            if email in existing_emails:
                continue
            session.add(
                AdminUser(
                    clinic_id=clinic_id,
                    email=email,
                    password_hash=DEMO_PASSWORD_HASH,
                    full_name=full_name,
                )
            )
        await session.flush()

        # Reload all admins for this clinic
        res = await session.execute(
            select(AdminUser).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
            ).order_by(AdminUser.email)
        )
        all_admins = list(res.scalars().all())
        if not all_admins:
            print("Error: no admins. Run seed_demo_data.")
            return

        # --- 5) UserRole: first admin -> owner, second -> manager, rest -> admin ---
        owner_role = roles_by_code["owner"]
        manager_role = roles_by_code["manager"]
        admin_role = roles_by_code["admin"]

        for i, admin in enumerate(all_admins):
            if i == 0:
                role_to_assign = owner_role
            elif i == 1:
                role_to_assign = manager_role
            else:
                role_to_assign = admin_role
            ex = await session.execute(
                select(UserRole).where(
                    UserRole.user_id == admin.id,
                    UserRole.role_id == role_to_assign.id,
                    UserRole.clinic_id == clinic_id,
                ).limit(1)
            )
            if ex.scalar_one_or_none() is None:
                session.add(
                    UserRole(
                        id=uuid.uuid4(),
                        user_id=admin.id,
                        role_id=role_to_assign.id,
                        clinic_id=clinic_id,
                    )
                )
        await session.flush()

        # --- 6) Tasks: need bookings, patients, leads (optional) ---
        res = await session.execute(
            select(Booking).where(
                Booking.clinic_id == clinic_id,
                Booking.deleted_at.is_(None),
            ).order_by(Booking.appointment_date.desc()).limit(80)
        )
        bookings = list(res.scalars().all())
        res = await session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
            ).limit(20)
        )
        patients = list(res.scalars().all())
        res = await session.execute(
            select(LeadCard).where(LeadCard.clinic_id == clinic_id).limit(15)
        )
        leads = list(res.scalars().all())

        res = await session.execute(
            select(Task).where(Task.clinic_id == clinic_id).limit(1)
        )
        has_tasks = res.scalar_one_or_none() is not None

        statuses = ["open", "open", "in_progress", "in_progress", "done", "done", "done", "cancelled"]
        priorities = ["low", "medium", "medium", "high", "urgent"]

        if not has_tasks and all_admins:
            creator = all_admins[0]
            assignees = all_admins[1:] if len(all_admins) > 1 else all_admins
            for i in range(min(len(TASK_TITLES) * 4, 55)):
                idx = i % len(TASK_TITLES)
                status = statuses[i % len(statuses)]
                due_delta = (i % 31) - 15
                due_date = today + timedelta(days=due_delta)
                due_at = datetime.combine(due_date, time(18, 0))
                completed_at = None
                if status == "done":
                    completed_at = datetime.combine(due_date, time(17, 30))
                assignee = assignees[i % len(assignees)] if assignees else None
                booking_id = bookings[i % len(bookings)].id if bookings else None
                patient_id = patients[i % len(patients)].id if patients else None
                lead_id = leads[i % len(leads)].id if leads else None
                task = Task(
                    clinic_id=clinic_id,
                    title=TASK_TITLES[idx] + (f" #{i+1}" if i >= len(TASK_TITLES) else ""),
                    description=TASK_DESCRIPTIONS[idx % len(TASK_DESCRIPTIONS)] if TASK_DESCRIPTIONS[idx % len(TASK_DESCRIPTIONS)] else None,
                    status=status,
                    priority=priorities[i % len(priorities)],
                    creator_id=creator.id,
                    assignee_id=assignee.id if assignee else None,
                    due_at=due_at,
                    completed_at=completed_at,
                    booking_id=booking_id,
                    patient_id=patient_id,
                    lead_id=lead_id,
                    source="manual",
                )
                session.add(task)
                await session.flush()
                if i % 3 == 0 and assignee and status != "cancelled":
                    session.add(
                        TaskComment(
                            task_id=task.id,
                            author_id=assignee.id,
                            text="Working on it. ETA end of day." if status == "in_progress" else "Done.",
                        )
                    )
                if i % 5 == 1 and creator.id != (assignee.id if assignee else None):
                    session.add(
                        TaskComment(
                            task_id=task.id,
                            author_id=creator.id,
                            text="Please prioritize.",
                        )
                    )
        await session.flush()

        # --- 7) Extra financial_transactions (cashbox activity) ---
        res = await session.execute(
            select(Cashbox).where(Cashbox.clinic_id == clinic_id).order_by(Cashbox.name)
        )
        cashboxes = list(res.scalars().all())
        default_cashbox = next((c for c in cashboxes if c.is_default), cashboxes[0] if cashboxes else None)
        other_cashbox = next((c for c in cashboxes if not c.is_default), default_cashbox)

        res = await session.execute(
            select(FinancialTransaction).where(
                FinancialTransaction.clinic_id == clinic_id,
                FinancialTransaction.source == "manual",
            ).limit(1)
        )
        has_manual_fin = res.scalar_one_or_none() is not None

        if not has_manual_fin and default_cashbox:
            for d in range(-30, 5):
                day = today + timedelta(days=d)
                for j, desc in enumerate(FIN_EXPENSE_DESCRIPTIONS[: 3]):
                    session.add(
                        FinancialTransaction(
                            clinic_id=clinic_id,
                            cashbox_id=default_cashbox.id,
                            type="expense",
                            amount=Decimal("500.00") + Decimal((d + j) * 50),
                            currency="RUB",
                            happened_at=datetime.combine(day, time(9, 30)),
                            description=desc,
                            source="manual",
                        )
                    )
                for desc in FIN_INCOME_DESCRIPTIONS[: 1]:
                    session.add(
                        FinancialTransaction(
                            clinic_id=clinic_id,
                            cashbox_id=default_cashbox.id,
                            type="income",
                            amount=Decimal("1000.00") + Decimal(d * 20),
                            currency="RUB",
                            happened_at=datetime.combine(day, time(10, 0)),
                            description=desc,
                            source="manual",
                        )
                    )
            if other_cashbox and other_cashbox.id != default_cashbox.id:
                for d in range(-7, 2):
                    day = today + timedelta(days=d)
                    session.add(
                        FinancialTransaction(
                            clinic_id=clinic_id,
                            cashbox_id=default_cashbox.id,
                            type="expense",
                            amount=Decimal("5000.00"),
                            currency="RUB",
                            happened_at=datetime.combine(day, time(20, 0)),
                            description="Transfer to card cashbox",
                            source="manual",
                        )
                    )
                    session.add(
                        FinancialTransaction(
                            clinic_id=clinic_id,
                            cashbox_id=other_cashbox.id,
                            type="income",
                            amount=Decimal("5000.00"),
                            currency="RUB",
                            happened_at=datetime.combine(day, time(20, 0)),
                            description="Transfer from main cashbox",
                            source="manual",
                        )
                    )
        await session.flush()

        await session.commit()
        print(
            "Staff/tasks/cash: admins=%s, roles ok, tasks and comments added, extra fin transactions. Done."
            % len(all_admins)
        )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
