"""Reset password for an existing admin by email.

Use when login fails but the admin exists (e.g. wrong or old password in DB).

Run:
  poetry run python -m src.scripts.reset_admin_password --email admin@example.com --password admin12345
  docker compose run --rm backend python -m src.scripts.reset_admin_password --email admin@example.com --password admin12345
"""

import argparse
import asyncio
import sys

from sqlalchemy import select, update

from src.infrastructure.database.base import AsyncSessionLocal
from src.domain.entities.admin_user import AdminUser
from src.api.v1.routers.admin_auth import hash_password

MIN_PASSWORD_LENGTH = 8


async def reset_password(email: str, password: str) -> None:
    email_norm = email.strip().lower()
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Ошибка: пароль должен быть не менее {MIN_PASSWORD_LENGTH} символов.", file=sys.stderr)
        sys.exit(1)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(AdminUser).where(
                AdminUser.email == email_norm,
                AdminUser.deleted_at.is_(None),
            ).limit(1)
        )
        admin = result.scalar_one_or_none()
        if not admin:
            print(f"Ошибка: администратор с email {email_norm} не найден.", file=sys.stderr)
            sys.exit(1)
        await session.execute(
            update(AdminUser).where(AdminUser.id == admin.id).values(
                password_hash=hash_password(password),
            )
        )
        await session.commit()
        print(f"Пароль для {admin.email} обновлён. Можно входить с указанным паролем.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Сбросить пароль администратора по email.")
    parser.add_argument("--email", required=True, help="Email администратора")
    parser.add_argument("--password", required=True, help="Новый пароль (не менее 8 символов)")
    args = parser.parse_args()
    asyncio.run(reset_password(email=args.email, password=args.password))


if __name__ == "__main__":
    main()
