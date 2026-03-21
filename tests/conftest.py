"""
Pytest fixtures for Dental Booking API tests.

Run from project root: poetry run pytest tests/

Пароль и тестовая БД:
  Ошибка "password authentication failed for user postgres" значит: к Postgres подключаются с тем паролем,
  который указан в DATABASE_URL (или DATABASE_URL_TEST). Если пароль в .env другой — задайте точный URL для тестов.

  Вариант 1 (рекомендуется): в .env добавьте строку с тем же паролем, что и в DATABASE_URL:
    DATABASE_URL_TEST=postgresql+asyncpg://postgres:ВАШ_ПАРОЛЬ@localhost:5432/dental_booking_test
  Вариант 2: не задавать DATABASE_URL_TEST — тогда подставится DATABASE_URL из .env с заменой БД на dental_booking_test
    (пароль берётся из DATABASE_URL; .env должен быть в корне проекта и загружается при запуске pytest).

  Создайте тестовую БД один раз (имя контейнера из docker-compose: dental_booking_postgres;
  в PowerShell не используйте плейсхолдер в угловых скобках — только реальное имя контейнера):
    docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"

  Схема должна совпадать с Alembic head (иначе ORM запросы падают с UndefinedColumnError):
    python scripts/upgrade_test_db.py
  Скрипт подставляет DATABASE_URL_TEST в DATABASE_URL и выполняет `alembic upgrade head`.
  Если таблицы уже есть, но alembic_version пуста или рассинхронизирована — см. docs/MIGRATION_UPGRADE.md (stamp/upgrade).

- If connection to the test DB fails, tests are SKIPPED with a hint.
- TRUNCATE runs only when the DB name contains "test". Never point at production.
"""
import os
import uuid
from datetime import date, time
from urllib.parse import urlparse

import pytest
from httpx import ASGITransport, AsyncClient

# Minimal built-in async support for environments where pytest-asyncio plugin
# is not installed (e.g. system Python runs).
try:
    import pytest_asyncio  # noqa: F401

    pytest_plugins = []
except Exception:
    pytest_plugins = ["tests.pytest_asyncio_compat"]

# Set test env before any src import so app uses test DB/Redis
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ["TESTING"] = "1"

# Load .env from project root so DATABASE_URL/REDIS_URL exist when not set in shell
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.isfile(_env_path):
    with open(_env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and os.environ.get(k) is None:
                    os.environ[k] = v

if os.environ.get("DATABASE_URL_TEST"):
    os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_TEST"]
else:
    # Use same credentials as DATABASE_URL but database=dental_booking_test
    base_url = os.environ.get("DATABASE_URL", "")
    if base_url and "dental_booking_test" not in base_url:
        parsed = urlparse(base_url)
        new_url = f"{parsed.scheme}://{parsed.netloc}/dental_booking_test"
        if parsed.query:
            new_url += "?" + parsed.query
        os.environ["DATABASE_URL"] = new_url
if os.environ.get("REDIS_URL_TEST"):
    os.environ["REDIS_URL"] = os.environ["REDIS_URL_TEST"]

_skip_reason = None
app = None  # Set in init_db (session-scoped) after engine init
try:
    from src.infrastructure.database.base import AsyncSessionLocal, Base, engine
    from src.domain.entities.admin_user import AdminUser
    from src.domain.entities.booking import Booking
    from src.domain.entities.chat_message import ChatMessage
    from src.domain.entities.clinic import Clinic
    from src.domain.entities.conversation import Conversation
    from src.domain.entities.doctor import Doctor
    from src.domain.entities.doctor_working_hours import DoctorWorkingHours
    from src.domain.entities.notification import Notification
    from src.domain.entities.patient import Patient
    from src.domain.entities.payment import Payment
    from src.domain.entities.service import Service
    from src.domain.entities.service_doctor import ServiceDoctor
    from src.domain.entities.csv_import_job import CsvImportJob
    from src.domain.entities.omnichannel_contact import Contact  # noqa: F401
    from src.domain.entities.omnichannel_channel import Channel  # noqa: F401
    from src.domain.entities.omnichannel_chat import Chat  # noqa: F401
    from src.domain.entities.omnichannel_message import Message  # noqa: F401
    from src.domain.entities.omnichannel_ai_settings import AISettings  # noqa: F401
    from src.domain.entities.omnichannel_audit_log import AuditLog  # noqa: F401
    from src.domain.entities.lead_pipeline import LeadPipeline  # noqa: F401
    from src.domain.entities.lead_stage import LeadStage  # noqa: F401
    from src.domain.entities.lead_card import LeadCard  # noqa: F401
    from src.domain.entities.lead_note import LeadNote  # noqa: F401
    from src.domain.entities.visit_attribution import VisitAttribution  # noqa: F401
    from src.domain.entities.family_link import FamilyLink  # noqa: F401
    from src.domain.entities.loyalty_campaign_settings import (  # noqa: F401
        LoyaltyCampaignSettings,
    )
    from src.domain.entities.lead_pipeline import LeadPipeline  # noqa: F401
    from src.domain.entities.lead_stage import LeadStage  # noqa: F401
    from src.domain.entities.lead_card import LeadCard  # noqa: F401
    from src.domain.entities.lead_note import LeadNote  # noqa: F401
except Exception as e:
    _skip_reason = (
        "App/asyncpg not available (try Python 3.11 or 3.12). "
        + str(e).split("\n")[0]
    )

if _skip_reason:
    pytestmark = pytest.mark.skip(reason=_skip_reason)

    @pytest.fixture(scope="session")
    def init_db():
        pytest.skip(_skip_reason)

    @pytest.fixture(scope="session")
    def seed_data():
        pytest.skip(_skip_reason)

    @pytest.fixture
    async def redis_client():
        pytest.skip(_skip_reason)

    @pytest.fixture
    async def client():
        pytest.skip(_skip_reason)

else:

    @pytest.fixture(scope="session")
    async def init_db():
        """Create all tables in test database. Run once per test session.
        Engine and app are inited in the session event loop (asyncio_default_fixture_loop_scope=session).
        """
        from src.infrastructure.database import base as db_base
        if getattr(db_base, "init_engine_for_testing", None):
            db_base.init_engine_for_testing()
        import tests.conftest as this_conftest
        from src.main import app as _app
        this_conftest.app = _app
        try:
            # Keep tests lightweight: use create_all() for fresh DBs.
            # Note: create_all() does not ALTER existing tables; for incremental
            # schema updates in a persistent local test DB we apply a minimal set
            # of idempotent DDL patches required by the suite.
            from sqlalchemy import text

            async with db_base.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

                # Idempotent schema patches for Tasks&Attention migrations.
                await conn.execute(
                    text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS attention_kind VARCHAR(64)")
                )
                await conn.execute(
                    text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS attention_ref_id UUID")
                )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_tasks_clinic_attention_ref "
                        "ON tasks (clinic_id, attention_kind, attention_ref_id)"
                    )
                )
                # Waitlist BKG-4 columns (idempotent for DBs created before migration)
                for col, typ in (
                    ("booking_id", "UUID"),
                    ("preferred_service_id", "UUID"),
                    ("source", "VARCHAR(32)"),
                    ("notes", "TEXT"),
                    ("created_by_id", "UUID"),
                    ("updated_by_id", "UUID"),
                ):
                    await conn.execute(
                        text(
                            f"ALTER TABLE waitlist_entries ADD COLUMN IF NOT EXISTS {col} {typ}"
                        )
                    )
                await conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS ix_waitlist_entries_status "
                        "ON waitlist_entries (status)"
                    )
                )
                # ERP payroll vitrine: NULL period flags + PK (migration n0o1p2q3r4s5; create_all does not ALTER).
                reg = await conn.execute(
                    text("SELECT to_regclass('public.erp_payroll_aggregate')::text")
                )
                if reg.scalar():
                    await conn.execute(
                        text(
                            "ALTER TABLE erp_payroll_aggregate ADD COLUMN IF NOT EXISTS "
                            "period_start_is_null BOOLEAN NOT NULL DEFAULT false"
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE erp_payroll_aggregate ADD COLUMN IF NOT EXISTS "
                            "period_end_is_null BOOLEAN NOT NULL DEFAULT false"
                        )
                    )
                    await conn.execute(
                        text(
                            """
                            UPDATE erp_payroll_aggregate SET
                              period_start_is_null = (period_start_key = DATE '0001-01-01'),
                              period_end_is_null = (period_end_key = DATE '9999-12-31')
                            """
                        )
                    )
                    await conn.execute(
                        text(
                            "ALTER TABLE erp_payroll_aggregate "
                            "DROP CONSTRAINT IF EXISTS erp_payroll_aggregate_pkey"
                        )
                    )
                    try:
                        await conn.execute(
                            text(
                                """
                                ALTER TABLE erp_payroll_aggregate ADD PRIMARY KEY (
                                  clinic_id, doctor_id, booking_bucket_id,
                                  period_start_is_null, period_start_key,
                                  period_end_is_null, period_end_key
                                )
                                """
                            )
                        )
                    except Exception:
                        pass
        except Exception as e:
            if "InvalidPasswordError" in type(e).__name__ or "password" in str(e).lower():
                pytest.skip(
                    "Cannot connect to test DB (invalid password). "
                    "Set DATABASE_URL (or DATABASE_URL_TEST) to your test DB, e.g. same as .env but database=dental_booking_test."
                )
            msg = str(e).lower()
            type_name = type(e).__name__.lower()
            # Windows локализует сообщения (может не содержать "refused"), поэтому
            # дополнительно смотрим на тип исключения.
            if (
                "connection" in msg
                or "refused" in msg
                or "connectionrefusederror" in type_name
                or "cannot connect" in msg
            ):
                pytest.skip(
                    "Cannot connect to test DB (Postgres/Redis not reachable). "
                    "Start: docker compose up -d postgres redis, then create DB: docker exec dental_booking_postgres psql -U postgres -c 'CREATE DATABASE dental_booking_test;'"
                )
            raise
        yield

    def _test_db_name_ok():
        """Ensure we do not TRUNCATE production. Only allow DB name containing 'test'."""
        url = os.environ.get("DATABASE_URL", "")
        if not url:
            return False
        path = urlparse(url).path or ""
        db_name = (path.lstrip("/").split("/")[0] or "").split("?")[0]
        return "test" in db_name.lower()

    @pytest.fixture(scope="session")
    async def truncate_tables(init_db):
        """Truncate all tables so auth tests see a single clinic (avoids stale data from previous runs).
        Runs on the REAL test database; only runs if DB name contains 'test' (e.g. dental_booking_test).
        """
        from sqlalchemy import text
        from src.infrastructure.database import base as db_base
        if not _test_db_name_ok():
            pytest.fail(
                "Refusing to TRUNCATE: DATABASE_URL database name must contain 'test' (e.g. dental_booking_test). "
                "Set DATABASE_URL_TEST=postgresql+asyncpg://user:pass@host:5432/dental_booking_test"
            )
        tables = ",".join(f'"{t}"' for t in Base.metadata.tables)
        async with db_base.engine.begin() as conn:
            await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        yield

    @pytest.fixture(scope="session")
    async def seed_data(init_db, truncate_tables):
        """
        Insert one clinic, one doctor (with working hours for today), one service,
        one patient. Returns dict with clinic_id, doctor_id, service_id, patient_id.
        """
        clinic_id = uuid.uuid4()
        doctor_id = uuid.uuid4()
        service_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        tomorrow = date.today()
        weekday = tomorrow.weekday()

        from src.infrastructure.database import base as db_base
        async with db_base.AsyncSessionLocal() as session:
            clinic = Clinic(
                id=clinic_id,
                name="Test Clinic",
                prepayment_amount=500,
            )
            session.add(clinic)
            doctor = Doctor(
                id=doctor_id,
                clinic_id=clinic_id,
                full_name="Test Doctor",
                specialization="Therapist",
                is_active=True,
            )
            session.add(doctor)
            session.add(
                DoctorWorkingHours(
                    doctor_id=doctor_id,
                    weekday=weekday,
                    start_time=time(9, 0),
                    end_time=time(18, 0),
                )
            )
            session.add(
                Service(
                    id=service_id,
                    clinic_id=clinic_id,
                    name="Test Service",
                    category="therapy",
                    price=1000,
                    duration_minutes=30,
                    is_active=True,
                )
            )
            session.add(
                ServiceDoctor(
                    service_id=service_id,
                    doctor_id=doctor_id,
                    is_active=True,
                )
            )
            session.add(
                Patient(
                    id=patient_id,
                    clinic_id=clinic_id,
                    phone="+79001234567",
                    full_name="Test Patient",
                )
            )
            from src.api.v1.routers.admin_auth import hash_password
            session.add(
                AdminUser(
                    id=admin_id,
                    clinic_id=clinic_id,
                    email="admin@test-clinic.local",
                    password_hash=hash_password("password123"),
                    full_name="Test Admin",
                )
            )
            # RBAC: test admin as clinic owner with all permissions (forms, etc.)
            from sqlalchemy import select

            from src.application.rbac_matrix import PERMISSIONS
            from src.domain.entities.permission import Permission
            from src.domain.entities.role import Role
            from src.domain.entities.role_permission import RolePermission
            from src.domain.entities.user_role import UserRole

            for pd in PERMISSIONS:
                ex = await session.execute(select(Permission).where(Permission.code == pd.code))
                if ex.scalar_one_or_none() is None:
                    session.add(
                        Permission(
                            id=uuid.uuid4(),
                            code=pd.code,
                            description=pd.description,
                        )
                    )
            await session.flush()

            owner_role_id = uuid.uuid4()
            session.add(
                Role(
                    id=owner_role_id,
                    clinic_id=clinic_id,
                    code="owner",
                    name="Owner",
                    description="Test seed owner",
                )
            )
            await session.flush()
            perm_result = await session.execute(select(Permission))
            for perm in perm_result.scalars():
                session.add(
                    RolePermission(
                        role_id=owner_role_id,
                        permission_id=perm.id,
                    )
                )
            session.add(
                UserRole(
                    id=uuid.uuid4(),
                    user_id=admin_id,
                    role_id=owner_role_id,
                    clinic_id=clinic_id,
                )
            )
            await session.commit()

        yield {
            "clinic_id": clinic_id,
            "doctor_id": doctor_id,
            "service_id": service_id,
            "patient_id": patient_id,
            "admin_id": admin_id,
            "date": tomorrow,
        }

    @pytest.fixture
    async def redis_client():
        """Redis client for tests (e.g. to set or read auth code)."""
        from src.infrastructure.database.redis_client import get_redis
        return await get_redis()

    @pytest.fixture
    async def patient_auth(client, seed_data, redis_client):
        """
        Log in as patient: random phone -> send-code -> read code from Redis -> verify-code.
        Returns dict: patient_id (UUID), access_token (str), phone (str).
        """
        import random
        from uuid import UUID
        phone = "+7900" + "".join(random.choices("0123456789", k=7))
        r = await client.post("/api/v1/auth/send-code", json={"phone": phone})
        assert r.status_code == 204, r.text
        clinic_id = seed_data["clinic_id"]
        key = f"auth:code:{clinic_id}:{phone}"
        raw = await redis_client.get(key)
        assert raw, f"Auth code not in Redis for key {key}"
        code = raw.decode() if isinstance(raw, bytes) else raw
        r2 = await client.post(
            "/api/v1/auth/verify-code",
            json={"phone": phone, "code": code},
        )
        assert r2.status_code == 200, r2.text
        data = r2.json()
        return {
            "patient_id": UUID(data["patient_id"]),
            "access_token": data["access_token"],
            "phone": phone,
        }

    @pytest.fixture
    async def admin_auth(client, seed_data):
        """Log in as admin (seed_data admin). Returns dict: access_token, admin_id, clinic_id.
        Kept function-scoped; rate limit for admin login is disabled in TESTING=1 (config) to avoid 429 in full suite."""
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "admin@test-clinic.local", "password": "password123"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        return {
            "access_token": data["access_token"],
            "admin_id": data["admin_id"],
            "clinic_id": data["clinic_id"],
        }

    @pytest.fixture
    async def client(init_db, seed_data):
        """HTTP client for API tests (uses app and seed_data so DB is ready)."""
        from tests.conftest import app as app_ref
        async with AsyncClient(
            transport=ASGITransport(app=app_ref),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest.fixture
    async def db_session(init_db, seed_data):
        """
        Async SQLAlchemy session for service-layer tests.

        Kept function-scoped to avoid state leaks between tests.
        """
        from src.infrastructure.database import base as db_base

        async with db_base.AsyncSessionLocal() as session:
            # Note: do not force rollback in fixture finalizer. On Windows/Proactor loop
            # some environments close the loop before async-generator teardown runs,
            # which makes rollback fail with "Event loop is closed".
            yield session
