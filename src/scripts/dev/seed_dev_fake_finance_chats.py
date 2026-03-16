"""
DEV ONLY: Fake finances (no real sales/cashbox) and artificial client chats.

- Purely manual financial_transactions (income/expense/transfer) over a wide date range:
  no booking_id, no payment_id — for demo reports/dashboards without real sales.
- Artificial conversations with clients: for every patient without a conversation,
  creates a thread with 8–20 fake messages (client questions, admin replies, reminders).

Requires: seed_demo_data (clinic, patients, admins); cashboxes from seed_dev_full_demo optional.

Run:
  poetry run python -m src.scripts.dev.seed_dev_fake_finance_chats
"""

from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, time
from decimal import Decimal
import random

from sqlalchemy import select

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.clinic import Clinic
from src.domain.entities.patient import Patient
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.cashbox import Cashbox
from src.domain.entities.financial_transaction import FinancialTransaction
from src.domain.entities.conversation import Conversation
from src.domain.entities.chat_message import ChatMessage
from src.domain.entities.payment import Payment  # FK in metadata

# Fake finance: descriptions only (no link to bookings/payments)
FAKE_INCOME = [
    "Prochie postupleniya (demo)",
    "Vozvrat podotchetnih (demo)",
    "Dop. uslugi, demo",
    "Predoplata po zakazu (demo)",
    "Kompensaciya, demo",
]

FAKE_EXPENSE = [
    "Raskhodnye materialy (demo)",
    "Arenda pomescheniya (demo)",
    "Kommunalnye (demo)",
    "Dezinfekciya (demo)",
    "Laba, demo",
    "Remont oborudovaniya (demo)",
    "Reklama Yandex (demo)",
    "Zarplata, demo",
    "Nalogi, demo",
]

# Artificial chat dialogue: [patient msg, admin reply, ...] — repeated/combined
CHAT_PATIENT = [
    "Zdravstvuyte, hochetsya zapisatsya na priyom.",
    "Kogda u vas est svobodnoe okno?",
    "A skolko stoit konsultaciya?",
    "Spasibo, togdа v chetverg podoydem.",
    "Mozhno perenesti na pyatnicu?",
    "Napomnite pozhaluysta za den.",
    "U menya bolela desna, eto seriozno?",
    "Kakoy vrach zanimayetsya implantami?",
    "Hochu otbelivanie, skazhite cenu.",
    "Zapisana na sredu, podtverdite.",
    "Bolshoye spasibo za priyom!",
    "Kogda sleduyushiy vizit nuzhen?",
]

CHAT_ADMIN = [
    "Dobryy den! Na koy den vam udobno?",
    "Est okno v chetverg v 10:00 i v pyatnicu v 14:00.",
    "Konsultaciya 1500 r, polnyy spisok na sayte.",
    "Zapisala na chetverg 10:00. Zhdem.",
    "Da, perenesla na pyatnicu 14:00.",
    "Napominaniye otpravim za 24 chasa.",
    "Luchshe pokazat vrachu. Zapishu na osmotr.",
    "Implantami zanimayetsya dr. Ivanov.",
    "Otbelivanie ot 8000 r. Zapishu na konsultaciyu?",
    "Da, vy zapisany na sredu v 11:00.",
    "Pozhaluysta! Zhdem v sleduyushiy raz.",
    "Cherez 6 mesyatsev na profilaktiku, zapishu?",
]


def _fake_dialogue(n: int) -> list[tuple[str, str]]:
    """Return n (sender_type, body) pairs: patient/admin alternating."""
    out = []
    for i in range(n):
        if i % 2 == 0:
            out.append(("patient", random.choice(CHAT_PATIENT)))
        else:
            out.append(("admin", random.choice(CHAT_ADMIN)))
    return out


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

        # --- 1) Fake finances: only manual transactions, no booking_id / payment_id ---
        res = await session.execute(
            select(Cashbox).where(Cashbox.clinic_id == clinic_id).order_by(Cashbox.name)
        )
        cashboxes = list(res.scalars().all())
        default_cashbox = next((c for c in cashboxes if c.is_default), cashboxes[0] if cashboxes else None)
        other_cashbox = next((c for c in cashboxes if not c.is_default), default_cashbox)

        # Check if we already added our "fake only" batch (no booking_id, source=manual)
        res = await session.execute(
            select(FinancialTransaction).where(
                FinancialTransaction.clinic_id == clinic_id,
                FinancialTransaction.source == "manual",
                FinancialTransaction.booking_id.is_(None),
            ).limit(1)
        )
        has_fake_fin = res.scalar_one_or_none() is not None

        if not has_fake_fin and default_cashbox:
            # 90 days back, 14 forward; several transactions per day
            for d in range(-90, 15):
                day = today + timedelta(days=d)
                for _ in range(2):
                    desc = random.choice(FAKE_EXPENSE)
                    session.add(
                        FinancialTransaction(
                            clinic_id=clinic_id,
                            cashbox_id=default_cashbox.id,
                            type="expense",
                            amount=Decimal(str(round(300 + random.uniform(0, 800), 2))),
                            currency="RUB",
                            happened_at=datetime.combine(day, time(9 + random.randint(0, 8), random.randint(0, 59))),
                            description=desc,
                            booking_id=None,
                            payment_id=None,
                            source="manual",
                        )
                    )
                for _ in range(2):
                    desc = random.choice(FAKE_INCOME)
                    session.add(
                        FinancialTransaction(
                            clinic_id=clinic_id,
                            cashbox_id=default_cashbox.id,
                            type="income",
                            amount=Decimal(str(round(500 + random.uniform(0, 2000), 2))),
                            currency="RUB",
                            happened_at=datetime.combine(day, time(10 + random.randint(0, 6), random.randint(0, 59))),
                            description=desc,
                            booking_id=None,
                            payment_id=None,
                            source="manual",
                        )
                    )
            if other_cashbox and other_cashbox.id != default_cashbox.id:
                for d in range(-30, 5):
                    day = today + timedelta(days=d)
                    session.add(
                        FinancialTransaction(
                            clinic_id=clinic_id,
                            cashbox_id=default_cashbox.id,
                            type="expense",
                            amount=Decimal("5000.00"),
                            currency="RUB",
                            happened_at=datetime.combine(day, time(20, 0)),
                            description="Transfer to card cashbox (demo)",
                            booking_id=None,
                            payment_id=None,
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
                            description="Transfer from main (demo)",
                            booking_id=None,
                            payment_id=None,
                            source="manual",
                        )
                    )
            await session.flush()

        # --- 2) Artificial chats: conversation + messages for every patient without one ---
        res = await session.execute(
            select(Patient).where(
                Patient.clinic_id == clinic_id,
                Patient.deleted_at.is_(None),
            ).order_by(Patient.phone)
        )
        patients = list(res.scalars().all())
        res = await session.execute(
            select(AdminUser).where(
                AdminUser.clinic_id == clinic_id,
                AdminUser.deleted_at.is_(None),
            ).limit(1)
        )
        admin = res.scalar_one_or_none()
        admin_id = admin.id if admin else None

        added_conv = 0
        added_msg = 0
        for patient in patients:
            ex = await session.execute(
                select(Conversation).where(
                    Conversation.clinic_id == clinic_id,
                    Conversation.patient_id == patient.id,
                    Conversation.deleted_at.is_(None),
                ).limit(1)
            )
            if ex.scalar_one_or_none() is not None:
                continue
            conv = Conversation(
                clinic_id=clinic_id,
                patient_id=patient.id,
                assigned_admin_id=admin_id,
                last_message_at=None,
                last_message_sender_type=None,
                unread_by_admin_count=0,
                unread_by_patient_count=0,
            )
            session.add(conv)
            await session.flush()
            added_conv += 1

            n_msgs = 8 + random.randint(0, 12)
            dialogue = _fake_dialogue(n_msgs)
            base_time = datetime.now() - timedelta(days=random.randint(1, 21))
            last_at = base_time
            for sender_type, body in dialogue:
                last_at = last_at + timedelta(minutes=random.randint(2, 25))
                msg = ChatMessage(
                    clinic_id=clinic_id,
                    conversation_id=conv.id,
                    patient_id=patient.id,
                    admin_id=admin_id if sender_type == "admin" else None,
                    sender_type=sender_type,
                    message_type="text",
                    body=body,
                    sticker_key=None,
                    read_by_admin_at=last_at if sender_type == "patient" else None,
                    read_by_patient_at=last_at if sender_type == "admin" else None,
                )
                session.add(msg)
                added_msg += 1
            conv.last_message_at = last_at
            conv.last_message_sender_type = dialogue[-1][0]
            await session.flush()

        await session.commit()
        print(
            "Fake finance + artificial chats: manual fin transactions (no sales), new convs=%s, new messages=%s. Done."
            % (added_conv, added_msg)
        )


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
