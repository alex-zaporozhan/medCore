# Политика времени (timezone) в проекте

**Принцип:** везде работаем в UTC; при пересечении с внешними сервисами — явный формат (ISO 8601 с Z).

## 1. Источник времени в коде

- **`src/core/datetime_utils.py`**:
  - `utc_now()` — timezone-aware UTC (для TIMESTAMPTZ и сравнений).
  - `utc_now_naive()` — naive UTC (для колонок `TIMESTAMP WITHOUT TIME ZONE`).
  - `to_iso8601_utc(dt)` — сериализация в API/JSON (всегда суффикс `Z`).

Не использовать `datetime.now()` без timezone и не использовать устаревший `datetime.utcnow()`.

## 2. База данных

- Часть таблиц создана с **TIMESTAMP(timezone=True)** (bookings, payments, notifications, conversations, chat_messages, prepayment, waitlist, часть initial): при записи передавать **aware UTC** (`utc_now()`).
- Часть таблиц с **DateTime()** без timezone (promo_posts, stories, recall_*, discounts, agreement_settings, clinic_plan): при записи передавать **naive UTC** (`utc_now_naive()`), чтобы не зависеть от session timezone в PostgreSQL.

## 3. Внешние сервисы

- **Telegram:** в теле сообщения даты не обязательны; при необходимости передавать строку в UTC (ISO 8601 с Z).
- **ЮKassa:** по контракту API использовать ISO 8601; передавать время в UTC.
- **SMS (SMSC):** текст сообщения; при подстановке времени (напоминания) — формат для человека (локальное время клиники или UTC по договорённости).
- **1C / CSV:** в экспорте/импорте даты — ISO 8601 или `YYYY-MM-DD`, время — `HH:MM` или ISO; явно договориться, в каком поясе (рекомендуется UTC или пояс клиники в названии поля).
- **Email (SMTP):** при подстановке дат в шаблоны — тот же подход: единый формат (UTC с суффиксом Z или локальное с поясом).

## 4. Celery

В `celery_app` задано `timezone="UTC"`, `enable_utc=True`. Задачи получают и отдают время в UTC.

## 5. Фронтенд

Даты с бэкенда приходят в ISO 8601 (с Z или с offset). Отрисовка в локальном времени — на стороне клиента (браузер/Intl).
