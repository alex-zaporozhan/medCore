## Tech Stack (inferred from code)

### High-level Overview

This document describes the **technical stack** of the `dental-booking` project as inferred **only from executable code and config**, without using any architecture or business documentation. It reflects the current state of the codebase, not a long-term vision or roadmap.

The system is a **full‑stack web application** with:
- An **async FastAPI backend** in Python 3.11.
- A **React + TypeScript SPA frontend** built with Vite.
- **PostgreSQL** as the primary database and **Redis** for caching, rate limiting, and background jobs.
- **Celery** workers for notifications, reminders, and other background tasks.
- Multiple external integrations (payments, SMS, messaging, OAuth, AI).

---

### Backend Stack

- **Language & Runtime**
  - Python `^3.11` (per `pyproject.toml`).
  - Async/await used across the data and API layers.

- **Web Framework**
  - **FastAPI**
    - Main application assembled in `src/main.py`.
    - Routers grouped under `src/api/v1/routers/*`.
    - Dependency injection used for DB sessions, auth, and current user/clinic context.
    - Health and metrics endpoints (`/health`, `/metrics`) exposed for monitoring.
  - **Uvicorn**
    - ASGI server used in Docker entrypoint to run the FastAPI app.

- **Persistence & Data Access**
  - **SQLAlchemy 2.x (async)**
    - Async engine and `AsyncSessionLocal` defined in `src/infrastructure/database/base.py`.
    - Declarative ORM models (entities) live under `src/domain/entities/*`.
    - Repository interfaces in `src/domain/interfaces/repositories/*` with implementations in `src/infrastructure/database/*`.
  - **PostgreSQL**
    - Implied by the use of `asyncpg` and typical connection strings in settings.
  - **Alembic**
    - Migration scripts under `alembic/versions/*`.
    - Used to evolve the relational schema (clinics, doctors, services, bookings, payments, notifications, omnichannel entities, etc.).

- **Schema & Configuration**
  - **Pydantic v2**
    - Request/response DTOs live in `src/application/dto/*`.
    - Used to validate and serialize API payloads and internal transfer objects.
  - **pydantic-settings**
    - Typed settings class in `src/core/config.py` for DB, Redis, JWT, OAuth, payments, AI, CORS, and rate limits.

- **Caching & Messaging Infrastructure**
  - **Redis**
    - Connection parameters and URL defined in `Settings`.
    - Used as Celery broker and result backend.
    - Also suitable for rate limiting and possibly other caching scenarios.
  - **Celery**
    - Celery app and beat schedule defined in `src/infrastructure/messaging/celery_app.py`.
    - Tasks implemented in `src/infrastructure/messaging/tasks/*`, especially `notifications.py`.
    - Handles:
      - Booking created/cancelled notifications.
      - 24h and 2h reminders before appointments.
      - Periodic scanning for upcoming bookings (`run_reminders_task`).

- **Auth & Security**
  - **JWT**
    - Implemented with `python-jose[cryptography]`.
    - Access tokens used for patients and admins with different TTLs.
  - **Password Hashing**
    - `passlib[bcrypt]` for password hashing and verification of admin credentials.
  - **Rate Limiting (config level)**
    - Rate limits for:
      - Auth send-code per phone/IP.
      - Admin login attempts.
      - AI calls per clinic (standard and “heavy” requests).
  - **XSS & Data Sanitization**
    - Backed by explicit tests on frontend rendering of untrusted text.
    - AI sanitization helpers in `src/core/ai_sanitizer.py`.

- **External Integrations**
  - **Payments**
    - **YooKassa** integration configured via `yookassa_*` settings in `src/core/config.py`.
    - Payment and prepayment logic implemented in `src/application/services/payment_service.py` and related entities/routers.
  - **SMS**
    - SMS provider integration (SMSC) implemented in `src/infrastructure/external_apis/sms_client.py`.
  - **Telegram Bot**
    - Config and token handled via `Settings`, implementation via `python-telegram-bot`.
  - **OAuth Providers**
    - VK and Yandex OAuth flows configured in `src/core/config.py` and used by `oauth_auth_service.py`.
  - **Omnichannel Integrations**
    - Own gateway (`integrations_gateway`) plus omnichannel integration settings/entities:
      - Channels (e.g. WhatsApp or similar).
      - Integration configs stored per clinic.
      - Dispatch layer in `omnichannel_outbound_dispatcher.py`.
  - **AI Provider**
    - Base URL, model name, and timeouts configured in `Settings`.
    - Used in AI‑related services (`chat_ai_service.py`, `omnichannel_ai_orchestrator.py`, `conversation_analysis_service.py`, `report_service.py`).

- **Observability & Ops**
  - **Health & Metrics**
    - `/health` endpoint for liveness checks.
    - `/metrics` endpoint exporting Prometheus metrics via `src/core/metrics.py`.
    - Docker `HEALTHCHECK` using HTTPX to query the health endpoint.
  - **Logging**
    - Structured logging configured in `src/main.py` and infra modules.
    - Additional logging inside Celery tasks and DB initialization.

- **Tooling & Quality**
  - `pytest`, `pytest-asyncio`, `pytest-playwright` for tests.
  - `black`, `ruff`, `mypy` with settings tuned to Python 3.11.

---

### Frontend Stack

- **Language & Framework**
  - **TypeScript**.
  - **React 18** with functional components and hooks.
  - **React Router v6** for SPA routing between:
    - Patient app (`/app`).
    - Admin app (`/admin`).
    - Auth and booking success routes.

- **Build & Tooling**
  - **Vite** as bundler/dev server (`frontend/package.json` and `vite.config`).
  - **Vitest** and **@testing-library/react** for unit/UI tests.

- **UI & State Management**
  - **Mantine**
    - Component library for layout and theming.
    - Global theme configured and provided in `frontend/src/main.tsx`.
  - **React Query (@tanstack/react-query)**
    - Data fetching and caching layer via hooks in `frontend/src/hooks/*`.
    - Query client wired at the root of the application.

- **PWA & UX Enhancements**
  - **Vite PWA plugin**
    - Service worker registration and PWA setup in `frontend/src/pwa/registerPwa.ts`.
  - Additional UX libs:
    - **dnd-kit** for drag-and-drop interactions.
    - **emoji-mart** for emoji pickers in chat or messaging UIs.
    - **dayjs** for date/time operations on the client.

- **Frontend Architecture**
  - **App structure**
    - `App.tsx` defines root router and layouts for admin vs patient apps.
    - `AdminLayout` and `AppLayout` implement separate shells and navigation.
  - **Feature Modules**
    - `admin/pages/*` for admin features (bookings, doctors, clinics, schedule, marketing, omni-chat, AI, reports, settings, integrations).
    - `app/pages/*` for patient features (home, feed, booking wizard, history, chat, login, OAuth).
  - **Data Access**
    - `frontend/src/api/client.ts` provides an HTTP client abstraction.
    - `frontend/src/hooks/*` implement feature-specific hooks that map closely to backend API routes.
  - **Shared Components**
    - Loading skeletons, empty states, error boundaries, reusable modals, and other shared UI patterns in `frontend/src/shared/*`.

---

### Infrastructure & Deployment

- **Containerization**
  - Dockerfile builds and runs the FastAPI app with Uvicorn.
  - Exposes port 8000 and integrates health/metrics endpoints.

- **Datastores & Messaging**
  - PostgreSQL as the main transactional datastore (via SQLAlchemy/asyncpg).
  - Redis as:
    - Celery broker/result backend.
    - Basis for rate limiting and possibly other transient storage.

- **Background Processing**
  - Celery + Redis used to:
    - Send SMS/email/Telegram notifications.
    - Issue automated appointment reminders.
    - Run periodic maintenance tasks (e.g., scanning for bookings requiring reminders).

---

### Summary

From the perspective of the codebase, `dental-booking` is a modern, production‑grade SaaS‑style system built with:
- Python 3.11, FastAPI, async SQLAlchemy, Celery, PostgreSQL, and Redis on the backend.
- React 18, TypeScript, Vite, React Query, and Mantine on the frontend.
- A strong emphasis on observability, background jobs, and integrations (payments, messaging, OAuth, AI).

This document should be treated as a **snapshot of the current tech stack** based solely on code and configuration.
