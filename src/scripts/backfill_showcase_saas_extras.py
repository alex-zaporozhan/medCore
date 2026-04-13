"""Backfill SaaS demo layer for DB seeded older ``seed_multi_tenant_showcase`` (без extras).

Исправляет ``admins.organization_id``, добавляет Commerce, календарь пациентов (~65% слотов на 3 месяца),
поток ``general`` + доску Kanban и демо-задачи, события **календаря сотрудников**, ленту (2 поста), чат, витрину — идемпотентно.

    poetry run python -m src.scripts.backfill_showcase_saas_extras
"""

from __future__ import annotations

import asyncio

from src.infrastructure.database.base import AsyncSessionLocal
from src.scripts.showcase_saas_extras import (
    apply_showcase_saas_extras,
    clear_schedule_cache_best_effort,
    list_showcase_clinic_ids,
)
from src.domain.entities.clinic import Clinic


async def main() -> None:
    async with AsyncSessionLocal() as session:
        triples = await list_showcase_clinic_ids(session)
        if not triples:
            print("No showcase clinics found (platform_signup_intents.notes marker missing). Nothing to do.")
            return
        for _org_id, clinic_id, owner_id in triples:
            clinic = await session.get(Clinic, clinic_id)
            if clinic is None:
                continue
            await apply_showcase_saas_extras(session, clinic=clinic, owner_admin_id=owner_id)
        await session.commit()
        await clear_schedule_cache_best_effort()
        print(f"Showcase SaaS extras applied for {len(triples)} clinic(s). Re-login admin to refresh session.")


if __name__ == "__main__":
    asyncio.run(main())
