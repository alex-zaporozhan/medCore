## DENTAL_BOOKING — AI ONE-PAGER (FACTUAL CODE SNAPSHOT)

**Role of this file**: ultra-short technical brief for AI agents.  
**Source of truth**: only code, configs, Docker, env templates in this repo.

---

### 1. Product in one paragraph

Universal **appointments & communications platform for service businesses** (default profile: dental clinic).
- Patient PWA: booking wizard, success page, history/feed, login, chat.
- Admin portal: clinics, doctors/masters, services, schedule & bookings, waitlist, recall campaigns, marketing, discounts, stickers, reports, integrations, notification channels, agreements, styling, chat + AI assistant, attention feed.

---

### 2. Tech stack (infra view)

- **Backend**: Python 3.11, FastAPI, Uvicorn, SQLAlchemy 2 (async), PostgreSQL 15, Redis 7, Celery, Pydantic 2, Alembic.
- **Frontend**: React 18 + TypeScript, React Router, Mantine UI, React Query, Vite, PWA via `vite-plugin-pwa`.
- **Infra/tools**: Docker (multi-stage backend image), `docker-compose` (api + postgres + redis + celery + celery-beat), Poetry, `ruff`, `black`, `mypy`, `pytest`, `pytest-asyncio`, `pytest-playwright`.

---

### 3. Backend architecture (where to look)

- Entry: `src/main.py` (FastAPI app), `src/api/v1/router.py`.
- Layers:
  - `src/domain/entities/` — domain models (clinic, doctor, patient, booking, schedule, payment, prepayment_policy, waitlist, recall_campaign, story, promo_post, discount, client_reference, notification, chat_message, conversation, attention_feed and more).
  - `src/application/services/` — use cases (booking, payments, waitlist, recall, marketing, notifications, chat, chat AI, attention feed, reports, csv import, etc.).
  - `src/infrastructure/database/` — DB engine/session, SQLAlchemy mappings, repositories.
  - `src/infrastructure/messaging/` — Celery app and background tasks (notifications, campaigns).
  - `src/infrastructure/external_apis/` — clients for YooKassa, SMSC.ru, SMTP, Telegram, external AI provider.
  - `src/core/` — config, logging, security (JWT + passlib), datetime utils.
- API surface: `src/api/v1/routers/*.py` (bookings, schedule, services, clinics, doctors, patients, payments, waitlist, recall, marketing, stickers, discounts, client reference, notifications, reports, chat, AI, CSV sync, admin_* variants).

---

### 4. Frontend architecture (where to look)

- Entry: `frontend/src/main.tsx`, `frontend/src/App.tsx`.
- Zones:
  - `frontend/src/app/pages/` — patient flows (home, booking wizard, booking success, login, history/feed, chat).
  - `frontend/src/admin/pages/` — admin dashboard + all management screens (bookings, schedule, clinics, doctors, services, patients, prepayment, payment gateway, waitlist, recall, marketing, stickers, discounts, client references, reports, channels, agreements, styling, chat, AI, attention feed, settings).
  - `frontend/src/admin/components/`, `frontend/src/admin/layouts/` — building blocks of admin UI.
  - `frontend/src/hooks/` — per-feature hooks using React Query (bookings, schedule, waitlist, recall, marketing, payments, reports, chat, AI, etc.).
  - `frontend/src/api/` — HTTP client + TS types.
  - `frontend/src/shared/` — shared UI and utilities.

---

### 5. Universal business support (hidden power)

- Backend DTO `src/application/dto/clinic_dto.py`:
  - `BusinessType = Literal["stomatology", "clinic", "beauty_salon", "barbershop", "nail_salon", "massage_salon", "other"]`.
  - `business_type` and `business_type_custom_name` are part of clinic DTOs.
- Domain `src/domain/entities/clinic.py` and Alembic migration `add_clinics_business_type.py`:
  - real DB columns `business_type` (default `"stomatology"`) and `business_type_custom_name`.
- Service `src/application/services/business_lexicon_service.py`:
  - maps business types to localized roles/lexicon (e.g. `barber`, `pedicure_master` for beauty/barber verticals).
- Frontend:
  - `frontend/src/api/types.ts` — `BUSINESS_TYPE_OPTIONS` and TS `BusinessType`.
  - `frontend/src/admin/pages/AdminClinicsPage.tsx` — admin can select `business_type` and custom name.
- Tests `tests/api/test_stage1_universal_business.py`:
  - assert that clinics API exposes and accepts `business_type` and `business_type_custom_name`.
- **Conclusion from code**: core is a **universal booking engine** for multiple service verticals; dentistry is just the default preset.

---

### 6. Capabilities (checklist)

- Appointments & schedule: booking wizard, slots, doctors/masters, services, clinics.
- Payments & prepayment: YooKassa integration, prepayment policies, clinic plans.
- Multi-channel comms: SMS (SMSC.ru), email (SMTP), Telegram; notification policies and patient preferences.
- Waitlist & queue: waitlist entries, queue policies, automated notifications.
- Recall & marketing: recall campaigns/segments/templates/logs, stories, promo posts, discounts, stickers, client references, public marketing feed.
- Chat & AI: patient–clinic chat, AI assistant, attention feed summarizing important cases.
- Analytics: reports for bookings, revenue and activity.
- CSV import: CSV-based data sync for clinics.

---

### 7. Key ENV / integrations (backbone)

- Core infra: `DATABASE_URL`, `REDIS_URL`.
- Payments: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, `YOOKASSA_TEST_MODE`, `YOOKASSA_RETURN_URL`.
- SMS: `SMSC_LOGIN`, `SMSC_PASSWORD`, `SMSC_SENDER`.
- Email: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_USE_TLS`, `SMTP_FROM_EMAIL`.
- Telegram: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ADMIN_CHAT_ID`.
- AI: `AI_PROVIDER_BASE_URL`, `AI_PROVIDER_MODEL`, `AI_PROVIDER_API_KEY`, `AI_TIMEOUT_SECONDS`.

