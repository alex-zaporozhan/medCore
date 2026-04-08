"""Create a platform founder (Основатель) user for POST /api/v1/platform/auth/login.

Does not require a clinic row. Password must be at least 8 characters.

Run:
  poetry run python -m src.scripts.create_platform_founder_user --email founder@example.com --password "SecurePass123"

Or with Docker:
  docker compose run --rm backend python -m src.scripts.create_platform_founder_user --email founder@example.com --password "SecurePass123"
"""

import argparse
import asyncio
import sys

from sqlalchemy import select

from src.api.v1.routers.admin_auth import hash_password
from src.domain.entities.platform_founder_user import PlatformFounderUser
from src.infrastructure.database.base import AsyncSessionLocal

MIN_PASSWORD_LENGTH = 8


async def create_platform_founder_user(email: str, password: str) -> None:
    email_norm = email.strip().lower()
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Ошибка: пароль должен быть не менее {MIN_PASSWORD_LENGTH} символов.", file=sys.stderr)
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(PlatformFounderUser).where(PlatformFounderUser.email == email_norm).limit(1)
        )
        if existing.scalar_one_or_none():
            print(f"Ошибка: пользователь платформы с email {email_norm} уже существует.", file=sys.stderr)
            sys.exit(1)

        row = PlatformFounderUser(
            email=email_norm,
            password_hash=hash_password(password),
        )
        session.add(row)
        await session.commit()
        print(f"Создан пользователь платформы: {row.email} (id={row.id})")
        print("Вход: POST /api/v1/platform/auth/login с этим email и паролем (нужен PLATFORM_FOUNDER_JWT_SECRET в prod).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Создать учётную запись Основателя платформы (platform_founder_users)."
    )
    parser.add_argument("--email", required=True, help="Email (логин)")
    parser.add_argument("--password", required=True, help=f"Пароль (не менее {MIN_PASSWORD_LENGTH} символов)")
    args = parser.parse_args()
    asyncio.run(create_platform_founder_user(email=args.email, password=args.password))


if __name__ == "__main__":
    main()
