"""Показать код входа пациента из Redis (для разработки, без SMS).

Код кладётся в Redis при запросе «Получить код» на странице /login.
Ключ: auth:code:{clinic_id}:{phone}

Запуск:
  poetry run python -m src.scripts.get_auth_code +79001234567
  poetry run python -m src.scripts.get_auth_code "8 900 123 45 67"

Сначала на странице /login введите телефон и нажмите «Получить код»,
затем выполните эту команду с тем же номером.
"""

import asyncio
import re
import sys

from sqlalchemy import select

from src.domain.entities.clinic import Clinic
from src.infrastructure.database.base import AsyncSessionLocal
from src.infrastructure.database.redis_client import get_redis


def normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    return f"+{digits}" if digits else phone


async def main(phone: str) -> None:
    normalized = normalize_phone(phone)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Clinic).limit(1))
        clinic = result.scalar_one_or_none()
        if not clinic:
            print("Ошибка: в БД нет ни одной клиники.", file=sys.stderr)
            sys.exit(1)
        key = f"auth:code:{clinic.id}:{normalized}"
    redis = await get_redis()
    code = await redis.get(key)
    if code:
        print(code)
    else:
        print("Код не найден или истёк. Сначала на /login нажмите «Получить код» для этого номера.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python -m src.scripts.get_auth_code <телефон>", file=sys.stderr)
        print("Пример: python -m src.scripts.get_auth_code +79001234567", file=sys.stderr)
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
