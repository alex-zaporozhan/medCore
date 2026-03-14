"""Create one admin user with custom email and password (e.g. for client handover).

Requires at least one clinic in the database (run seed_demo_data first if needed).
Password must be at least 8 characters.

Run:
  poetry run python -m src.scripts.create_admin --email client@company.com --password "SecurePass123"
  poetry run python -m src.scripts.create_admin --email admin@client.ru --password "Пароль123" --full-name "Иван Админов"

Or with Docker (backend container has DB access via env):
  docker compose run --rm backend python -m src.scripts.create_admin --email client@company.com --password "SecurePass123"
"""

import argparse
import asyncio
import sys
from uuid import UUID

from sqlalchemy import select

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.clinic import Clinic
from src.api.v1.routers.admin_auth import hash_password

MIN_PASSWORD_LENGTH = 8


async def create_admin(
    email: str,
    password: str,
    full_name: str | None = None,
    clinic_id: str | None = None,
) -> None:
    email_norm = email.strip().lower()
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Ошибка: пароль должен быть не менее {MIN_PASSWORD_LENGTH} символов.", file=sys.stderr)
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        if clinic_id:
            try:
                clinic_uuid = UUID(clinic_id)
            except ValueError:
                print("Ошибка: неверный формат clinic_id (нужен UUID).", file=sys.stderr)
                sys.exit(1)
            result = await session.execute(
                select(Clinic).where(Clinic.id == clinic_uuid, Clinic.deleted_at.is_(None)).limit(1)
            )
        else:
            result = await session.execute(
                select(Clinic).where(Clinic.deleted_at.is_(None)).limit(1)
            )
        clinic = result.scalar_one_or_none()
        if not clinic:
            print("Ошибка: в БД нет ни одной клиники. Сначала выполните: poetry run python -m src.scripts.seed_demo_data", file=sys.stderr)
            sys.exit(1)

        existing = await session.execute(
            select(AdminUser).where(
                AdminUser.email == email_norm,
                AdminUser.deleted_at.is_(None),
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            print(f"Ошибка: администратор с email {email_norm} уже существует.", file=sys.stderr)
            sys.exit(1)

        admin = AdminUser(
            clinic_id=clinic.id,
            email=email_norm,
            password_hash=hash_password(password),
            full_name=(full_name or "").strip() or None,
        )
        session.add(admin)
        await session.commit()
        print(f"Создан администратор: {admin.email} (clinic_id={admin.clinic_id})")
        print("Вход в админку: используйте этот email и указанный пароль.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Создать администратора с заданным email и паролем (для передачи клиенту и т.п.)."
    )
    parser.add_argument("--email", required=True, help="Email администратора (логин)")
    parser.add_argument("--password", required=True, help="Пароль (не менее 8 символов)")
    parser.add_argument("--full-name", default=None, help="Имя администратора (необязательно)")
    parser.add_argument("--clinic-id", default=None, help="UUID клиники (если не указан — берётся первая)")
    args = parser.parse_args()

    asyncio.run(
        create_admin(
            email=args.email,
            password=args.password,
            full_name=args.full_name,
            clinic_id=args.clinic_id,
        )
    )


if __name__ == "__main__":
    main()
