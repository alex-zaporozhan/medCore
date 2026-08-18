"""
Pytest fixtures for Dental Booking API tests.

Run from project root: poetry run pytest tests/

Пошаговая настройка тестовой БД (ошибка database "dental_booking_test" does not exist):
  docs/RUN_SERVICES (repository docs folder)

Пароль и тестовая БД:
  Ошибка "password authentication failed for user postgres" значит: к Postgres подключаются с тем паролем,
  который указан в DATABASE_URL (или DATABASE_URL_TEST). Если пароль в .env другой — задайте точный URL для тестов.

  Вариант 1: задать ``DATABASE_URL_TEST`` (тот же пароль/хост, что у Docker Postgres, БД ``dental_booking_test``).
  Вариант 2: задать только ``DATABASE_URL`` — pytest **перепишет имя БД** на ``dental_booking_test`` (тот же хост/пользователь/пароль), см. ``_resolve_database_url_test``.
  Имя ``dental_booking_test`` — принятое соглашение; для ``TRUNCATE`` достаточно, чтобы в имени БД (path URL) была подстрока ``test`` (см. ``_test_db_name_ok``).

  Создайте тестовую БД один раз (имя контейнера из docker-compose: dental_booking_postgres;
  в PowerShell не используйте плейсхолдер в угловых скобках — только реальное имя контейнера):
    docker exec dental_booking_postgres psql -U postgres -c "CREATE DATABASE dental_booking_test;"

  Схема: при прогоне pytest `init_db` выполняет `alembic upgrade head` (тот же путь, что `scripts/upgrade_test_db.py`).
  Вручную один раз: `python scripts/upgrade_test_db.py`.
  Если таблицы уже есть, но alembic_version пуста или рассинхронизирована — согласуйте stamp/upgrade с командой (опасные шаги не документируются здесь).

- If connection to the test DB fails, tests are SKIPPED with a hint.
- При ``TESTING=1`` движок БД не создаётся при импорте: ``init_engine_for_testing()`` вызывается из session-фикстуры ``init_db`` (или из тестов с ``client`` / ``seed_data``, которые от неё зависят). Любой тест, который вызывает ``AsyncSessionLocal()`` напрямую без ``client``, должен явно запросить ``init_db`` (или другую фикстуру, тянущую ``init_db``), иначе в изолированном прогоне будет ``TypeError: 'NoneType' object is not callable``.
- TRUNCATE runs only when the DB name contains "test". Never point at production.
- Before TRUNCATE, other ``client backend`` sessions on the same database are terminated so
  ``TRUNCATE`` is not blocked by stray uvicorn/psql/pytest (set ``PYTEST_DISABLE_TEST_DB_SESSION_KILL=1`` to skip).
- If Postgres returns ``too many clients already``, the server hit ``max_connections`` (often shared with a running
  uvicorn using a large pool). Stop the API or raise Postgres limits (``docker-compose`` ``db`` sets ``max_connections=200``).
"""
import logging
import os
import asyncio
import subprocess
import sys
import uuid
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest
from httpx import ASGITransport, AsyncClient

logger = logging.getLogger(__name__)

# Bootstrap TESTING + .env before choosing the Windows event-loop policy (policy must be set
# before the first asyncio loop exists). FRONTEND_E2E_URL in .env must not force Proactor for a
# full backend suite — Proactor + redis + repeated httpx ASGI lifecycles flakes ("Event loop is closed").
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "test-jwt-secret-key")
os.environ.setdefault(
    "PLATFORM_BILLING_WEBHOOK_SECRET",
    "test-platform-billing-webhook-secret",
)
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-telegram-token-ci")
os.environ.setdefault("PATIENT_PAYMENT_WEBHOOK_SECRET", "")
os.environ["TESTING"] = "1"
os.environ.setdefault("RUN_REDIS_INTEGRATION_TESTS", "1")
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

# Windows: default Selector for pytest; opt-in Proactor (Playwright/subprocess): PYTEST_WIN32_USE_PROACTOR=1
if sys.platform == "win32":
    try:
        if os.environ.get("PYTEST_WIN32_USE_PROACTOR", "").strip().lower() in ("1", "true", "yes"):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        else:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except AttributeError:
        pass


def _critical_path_ci() -> bool:
    """LEAD A3: CI sets CRITICAL_PATH_CI=1 so missing infra fails the job instead of skipping."""
    return os.environ.get("CRITICAL_PATH_CI", "").strip().lower() in ("1", "true", "yes")


def _item_path_norm(it) -> str:
    try:
        p = str(it.path)
    except AttributeError:
        p = str(getattr(it, "fspath", ""))
    return p.replace("\\", "/")


def pytest_collection_modifyitems(config, items):
    """Start vite preview when smoke is selected; reorder Playwright last on Windows."""
    smokes = [
        it
        for it in items
        if _item_path_norm(it).endswith("/tests/e2e/test_critical_path_smoke.py")
    ]
    if smokes and not (os.environ.get("FRONTEND_E2E_URL") or "").strip():
        from tests.e2e.vite_preview_server import ensure_vite_preview_for_smoke

        ensure_vite_preview_for_smoke(ci_strict=_critical_path_ci())

    if not (os.environ.get("FRONTEND_E2E_URL") or "").strip():
        return
    e2e_other, e2e_playwright, e2e_critical_smoke, rest = [], [], [], []
    for it in items:
        norm = _item_path_norm(it)
        if "/tests/e2e/" in norm:
            if norm.endswith("/tests/e2e/test_frontend_pages.py"):
                e2e_playwright.append(it)
            elif norm.endswith("/tests/e2e/test_critical_path_smoke.py"):
                e2e_critical_smoke.append(it)
            else:
                e2e_other.append(it)
        else:
            rest.append(it)
    # Keep backend/api tests first; run browser E2E afterwards to avoid event-loop
    # interference in mixed suites on local Windows runners.
    items[:] = rest + e2e_other + e2e_playwright + e2e_critical_smoke


def pytest_sessionfinish(session, exitstatus):
    try:
        from tests.e2e.vite_preview_server import stop_vite_preview_if_started

        stop_vite_preview_if_started()
    except Exception:
        logger.debug("vite preview teardown skipped", exc_info=True)


# Minimal built-in async support for environments where pytest-asyncio plugin
# is not installed (e.g. system Python runs).
try:
    import pytest_asyncio  # noqa: F401

    pytest_plugins = []
except Exception:
    pytest_plugins = ["tests.pytest_asyncio_compat"]

def _resolve_database_url_test() -> str:
    """Prefer DATABASE_URL_TEST; else same host/credentials as DATABASE_URL with DB name dental_booking_test (CI)."""
    explicit = (os.environ.get("DATABASE_URL_TEST") or "").strip()
    if explicit:
        return explicit
    dsn = (os.environ.get("DATABASE_URL") or "").strip()
    if not dsn:
        pytest.fail(
            "Set DATABASE_URL_TEST or DATABASE_URL for pytest. "
            "Example: DATABASE_URL_TEST=postgresql+asyncpg://postgres:postgres@localhost:5442/dental_booking_test "
            "or DATABASE_URL to the same host with any DB name (it will be rewritten to dental_booking_test)."
        )
    u = urlparse(dsn)
    new_path = "/dental_booking_test"
    return urlunparse((u.scheme, u.netloc, new_path, u.params, u.query, u.fragment))


_db_test_url = _resolve_database_url_test()
os.environ["DATABASE_URL_TEST"] = _db_test_url
os.environ["DATABASE_URL"] = _db_test_url
if os.environ.get("REDIS_URL_TEST"):
    os.environ["REDIS_URL"] = os.environ["REDIS_URL_TEST"]

_skip_reason = None
app = None  # Set in init_db (session-scoped) after engine init
try:
    from src.infrastructure.database.base import Base
    from src.domain.entities.admin_user import AdminUser
    from src.domain.entities.clinic import Clinic
    from src.domain.entities.doctor import Doctor
    from src.domain.entities.doctor_working_hours import DoctorWorkingHours
    from src.domain.entities.patient import Patient
    from src.domain.entities.service import Service
    from src.domain.entities.service_doctor import ServiceDoctor
    from src.domain.entities.cashbox import Cashbox
    from src.domain.entities.warehouse import Warehouse
    from src.domain.entities.payroll_policy import PayrollPolicy
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

    @pytest_asyncio.fixture(scope="session", loop_scope="session")
    async def init_db():
        """Apply Alembic migrations to the test DB (single source of truth with prod). Session-scoped."""
        from src.infrastructure.database import base as db_base
        if getattr(db_base, "init_engine_for_testing", None):
            db_base.init_engine_for_testing()
        import tests.conftest as this_conftest
        repo_root = Path(__file__).resolve().parent.parent
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "alembic", "upgrade", "head"],
                cwd=str(repo_root),
                env=os.environ.copy(),
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                raise RuntimeError(proc.stderr or proc.stdout or "alembic upgrade failed")
        except Exception as e:
            err_s = str(e).lower()
            if "invalidpassworderror" in type(e).__name__.lower() or "password" in err_s:
                pytest.skip(
                    "Cannot connect to test DB (invalid password). "
                    "Set DATABASE_URL_TEST to your test DB, e.g. database=dental_booking_test."
                )
            if "does not exist" in err_s and "database" in err_s:
                pytest.skip(
                    "Test database is missing. Create it (see repository README and docs/RUN_SERVICES), then re-run."
                )
            msg = err_s
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
                    "Start: docker compose up -d db redis, then create DB: docker exec dental_booking_postgres psql -U postgres -c 'CREATE DATABASE dental_booking_test;'"
                )
            raise
        from src.main import app as _app

        this_conftest.app = _app
        yield
        try:
            if db_base.engine is not None:
                await db_base.engine.dispose()
        except Exception:
            logger.debug("test engine dispose skipped", exc_info=True)

    def _test_db_name_ok():
        """Ensure we do not TRUNCATE production. Only allow DB name containing 'test'."""
        url = os.environ.get("DATABASE_URL_TEST", "") or os.environ.get("DATABASE_URL", "")
        if not url:
            return False
        path = urlparse(url).path or ""
        db_name = (path.lstrip("/").split("/")[0] or "").split("?")[0]
        return "test" in db_name.lower()

    @pytest_asyncio.fixture(scope="session", loop_scope="session")
    async def truncate_tables(init_db):
        """Truncate all tables so auth tests see a single clinic (avoids stale data from previous runs).
        Runs on the REAL test database; only runs if DB name contains 'test' (e.g. dental_booking_test).
        """
        from sqlalchemy import text
        from src.infrastructure.database import base as db_base
        if not _test_db_name_ok():
                pytest.fail(
                    "Refusing to TRUNCATE: DATABASE_URL_TEST database name must contain 'test' (e.g. dental_booking_test). "
                    "Set DATABASE_URL_TEST=postgresql+asyncpg://user:pass@host:5432/dental_booking_test"
                )
        tables = ",".join(f'"{t}"' for t in Base.metadata.tables)
        async with db_base.engine.begin() as conn:
            # TRUNCATE ... CASCADE takes ACCESS EXCLUSIVE locks on many tables.
            # Stray connections (local API, psql, hung pytest) cause lock_timeout and cascade ERRORs
            # for every test that depends on seed_data. Terminate other client backends on this DB only.
            disable_kill = os.environ.get("PYTEST_DISABLE_TEST_DB_SESSION_KILL", "").lower() in (
                "1",
                "true",
                "yes",
            )
            if not disable_kill:
                r = await conn.execute(
                    text(
                        """
                        SELECT pg_terminate_backend(pid)
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                          AND pid <> pg_backend_pid()
                          AND backend_type = 'client backend'
                        """
                    )
                )
                terminated = sum(1 for row in r.fetchall() if row[0] is True)
                if terminated:
                    logger.warning(
                        "pytest: terminated %s other session(s) on %s before TRUNCATE",
                        terminated,
                        urlparse(
                            os.environ.get("DATABASE_URL_TEST", "")
                            or os.environ.get("DATABASE_URL", "")
                        ).path
                        or "(db)",
                    )
                await asyncio.sleep(0.15)

            await conn.execute(text("SET statement_timeout = '180s'"))
            await conn.execute(text("SET lock_timeout = '30s'"))
            try:
                await conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
            except Exception as e:
                msg = str(e).lower()
                if "lock timeout" in msg or "canceling statement due to lock timeout" in msg:
                    pytest.fail(
                        "Test DB cleanup is blocked by another connection holding locks. "
                        "Stop local services connected to the test DB (uvicorn/celery/psql/other pytest), "
                        "then re-run tests/push."
                    )
                raise
        yield

    @pytest_asyncio.fixture(scope="session", loop_scope="session")
    async def seed_data(init_db, truncate_tables):
        """
        Insert one clinic, one doctor (with working hours for today), one service,
        one patient, plus ERP defaults (default cashbox, warehouse, payroll policy for the doctor).
        Returns dict with clinic_id, doctor_id, service_id, patient_id.
        """
        clinic_id = uuid.uuid4()
        doctor_id = uuid.uuid4()
        service_id = uuid.uuid4()
        patient_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        doctor_admin_id = uuid.uuid4()
        platform_founder_id = uuid.uuid4()
        tomorrow = date.today()
        weekday = tomorrow.weekday()

        from src.infrastructure.database import base as db_base
        async with db_base.AsyncSessionLocal() as session:
            clinic = Clinic(
                id=clinic_id,
                name="Test Clinic",
                prepayment_amount=500,
                clinic_slug=f"test-seed-{clinic_id.hex[:12]}",
            )
            session.add(clinic)
            from src.domain.entities.task_stream import TaskStream

            session.add(
                TaskStream(
                    clinic_id=clinic_id,
                    name="Общее",
                    slug="general",
                    sort_order=0,
                    is_archived=False,
                    theme={},
                )
            )
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
            await session.flush()
            # ERP: same defaults a real clinic needs for visit completion / finance / payroll / inventory.
            session.add(
                Cashbox(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    name="Seed cashbox",
                    type="cash",
                    currency="RUB",
                    is_default=True,
                    is_active=True,
                )
            )
            session.add(
                Warehouse(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    name="Seed warehouse",
                    is_default=True,
                )
            )
            session.add(
                PayrollPolicy(
                    id=uuid.uuid4(),
                    clinic_id=clinic_id,
                    doctor_id=doctor_id,
                    role=None,
                    fixed_per_shift=Decimal("0"),
                    percent_from_services=Decimal("0.20"),
                    percent_from_products=Decimal("0"),
                )
            )
            from src.api.v1.routers.admin_auth import hash_password
            admin_email = f"admin-{uuid.uuid4().hex[:10]}@test-clinic.local"
            session.add(
                AdminUser(
                    id=admin_id,
                    clinic_id=clinic_id,
                    email=admin_email,
                    password_hash=hash_password("password123"),
                    full_name="Test Admin",
                )
            )
            from src.domain.entities.platform_founder_user import PlatformFounderUser

            platform_founder_email = f"pf-{platform_founder_id.hex[:12]}@test.platform.local"
            session.add(
                PlatformFounderUser(
                    id=platform_founder_id,
                    email=platform_founder_email,
                    password_hash=hash_password("password123"),
                )
            )
            # RBAC: test admin as clinic owner with all permissions (forms, etc.)
            from sqlalchemy import select

            from src.application.rbac_matrix import PERMISSIONS, ROLE_PERMISSIONS
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
            doctor_role_id = uuid.uuid4()
            session.add(
                Role(
                    id=doctor_role_id,
                    clinic_id=clinic_id,
                    code="doctor",
                    name="Doctor",
                    description="Test seed doctor (no patients.pii.read)",
                )
            )
            await session.flush()
            for pcode in ROLE_PERMISSIONS["doctor"]:
                pr = await session.execute(select(Permission).where(Permission.code == pcode))
                p = pr.scalar_one_or_none()
                if p:
                    session.add(RolePermission(role_id=doctor_role_id, permission_id=p.id))
            doctor_email = f"doctor-{uuid.uuid4().hex[:10]}@test-clinic.local"
            session.add(
                AdminUser(
                    id=doctor_admin_id,
                    clinic_id=clinic_id,
                    email=doctor_email,
                    password_hash=hash_password("password123"),
                    full_name="Test Doctor",
                )
            )
            session.add(
                UserRole(
                    id=uuid.uuid4(),
                    user_id=doctor_admin_id,
                    role_id=doctor_role_id,
                    clinic_id=clinic_id,
                )
            )

            # TRUNCATE сбрасывает seed из миграций; восстанавливаем глобальный SaaS-каталог для Phase 1b тестов.
            from src.domain.entities.platform_catalog_option import PlatformCatalogOption
            from src.domain.entities.platform_catalog_plan import PlatformCatalogPlan

            catalog_plan_seeds = [
                (
                    uuid.UUID("b0000001-0000-4000-8000-000000000010"),
                    "start",
                    "Start",
                    "База для моно-бизнеса: 1 филиал, до 5 сотрудников.",
                    ["core.base", "crm.pipeline", "tasks.kanban"],
                    Decimal("2900.00"),
                    Decimal("29000.00"),
                    0,
                ),
                (
                    uuid.UUID("b0000001-0000-4000-8000-000000000011"),
                    "growth",
                    "Growth",
                    "До 3 филиалов, до 20 сотрудников. AI в чатах, финансы, лояльность.",
                    [
                        "core.base",
                        "crm.pipeline",
                        "tasks.kanban",
                        "ai.assistant.chat",
                        "marketing.attribution",
                        "retention.bundle",
                    ],
                    Decimal("5900.00"),
                    Decimal("59000.00"),
                    1,
                ),
                (
                    uuid.UUID("b0000001-0000-4000-8000-000000000012"),
                    "business_os",
                    "Business OS",
                    "Сеть до 10 филиалов: RAG, задачи, склад, ROI, зарплаты.",
                    [
                        "core.base",
                        "crm.pipeline",
                        "tasks.kanban",
                        "ai.assistant.chat",
                        "marketing.attribution",
                        "retention.bundle",
                        "omni.embed.bundle",
                        "ai.rag.org_kb",
                    ],
                    Decimal("14900.00"),
                    Decimal("149000.00"),
                    2,
                ),
            ]
            for pid, slug, dname, desc, keys, pm, pa, sort_o in catalog_plan_seeds:
                if (
                    await session.execute(
                        select(PlatformCatalogPlan).where(PlatformCatalogPlan.slug == slug).limit(1)
                    )
                ).scalar_one_or_none() is None:
                    session.add(
                        PlatformCatalogPlan(
                            id=pid,
                            slug=slug,
                            display_name=dname,
                            description=desc,
                            option_keys=keys,
                            price_monthly_rub=pm,
                            price_annual_rub=pa,
                            is_active=True,
                            sort_order=sort_o,
                        )
                    )
            catalog_opts = [
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000001"),
                    "core.base",
                    "Базовый пакет",
                    "Орг, клиника, RBAC, расписание, базовые платежи",
                    None,
                    0,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000002"),
                    "tasks.kanban",
                    "Задачи / канбан",
                    None,
                    Decimal("1500.00"),
                    10,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000003"),
                    "crm.pipeline",
                    "CRM / воронка",
                    None,
                    Decimal("2800.00"),
                    20,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000004"),
                    "marketing.attribution",
                    "Маркетинг / атрибуция",
                    None,
                    Decimal("1200.00"),
                    15,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000005"),
                    "retention.bundle",
                    "Ретеншн / возврат пациентов",
                    None,
                    Decimal("1800.00"),
                    18,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000006"),
                    "omni.embed.bundle",
                    "Embed-виджет + публичный периметр (§24)",
                    "Моно-пакет встраивания; API keys и webhook-инбокс",
                    Decimal("4900.00"),
                    40,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000007"),
                    "ai.assistant.chat",
                    "AI-ассистент в чате (§24.2)",
                    None,
                    Decimal("2900.00"),
                    50,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000008"),
                    "ai.rag.org_kb",
                    "RAG база знаний организации (§24.3)",
                    None,
                    Decimal("3900.00"),
                    60,
                ),
                (
                    uuid.UUID("a0000001-0000-4000-8000-000000000009"),
                    "import.crm_v1",
                    "Импорт CRM v1",
                    "ADR-010 Phase 3+",
                    Decimal("1990.00"),
                    70,
                ),
            ]
            for oid, ekey, dname, desc, price, sort_o in catalog_opts:
                exo = await session.execute(
                    select(PlatformCatalogOption)
                    .where(PlatformCatalogOption.entitlement_key == ekey)
                    .limit(1)
                )
                if exo.scalar_one_or_none() is None:
                    session.add(
                        PlatformCatalogOption(
                            id=oid,
                            entitlement_key=ekey,
                            display_name=dname,
                            description=desc,
                            list_price_rub=price,
                            is_active=True,
                            sort_order=sort_o,
                        )
                    )

            await session.commit()

        yield {
            "clinic_id": clinic_id,
            "clinic_slug": f"test-seed-{clinic_id.hex[:12]}",
            "doctor_id": doctor_id,
            "service_id": service_id,
            "patient_id": patient_id,
            "admin_id": admin_id,
            "doctor_admin_id": doctor_admin_id,
            "admin_email": admin_email,
            "doctor_email": doctor_email,
            "platform_founder_id": platform_founder_id,
            "platform_founder_email": platform_founder_email,
            "platform_founder_password": "password123",
            "date": tomorrow,
        }

    @pytest_asyncio.fixture(scope="function", loop_scope="session")
    async def redis_client():
        """Redis client for tests (e.g. to set or read auth code)."""
        from src.infrastructure.database.redis_client import get_redis
        return await get_redis()

    @pytest_asyncio.fixture(scope="function", loop_scope="session")
    async def patient_auth(client, seed_data):
        """
        Log in as patient: random phone -> send-code -> read code from Redis -> verify-code.
        Returns dict: patient_id (UUID), access_token (str), phone (str).

        Drops the process-wide async Redis pool before send-code: a prior test can leave
        redis.asyncio connections bound to a torn Starlette/anyio task context on Windows
        (next request then fails with "Future attached to a different loop").
        """
        import random
        from uuid import UUID

        from src.infrastructure.database.redis_client import close_redis, get_redis

        await close_redis()
        redis = await get_redis()

        phone = ""
        r = None
        for _ in range(6):
            phone = "+7900" + "".join(random.choices("0123456789", k=7))
            r = await client.post(
                "/api/v1/auth/send-code",
                json={"phone": phone, "clinic_slug": seed_data["clinic_slug"]},
            )
            if r.status_code == 204:
                break
            if r.status_code == 429:
                # Full-suite retries can temporarily hit IP-based auth rate limit.
                # Rotate phone and retry a few times to keep fixture stable.
                await asyncio.sleep(0.2)
                continue
            break
        assert r is not None
        assert r.status_code == 204, r.text
        clinic_id = seed_data["clinic_id"]
        key = f"auth:code:{clinic_id}:{phone}"
        raw = await redis.get(key)
        assert raw, f"Auth code not in Redis for key {key}"
        code = raw.decode() if isinstance(raw, bytes) else raw
        r2 = await client.post(
            "/api/v1/auth/verify-code",
            json={
                "phone": phone,
                "code": code,
                "clinic_slug": seed_data["clinic_slug"],
            },
        )
        assert r2.status_code == 200, r2.text
        data = r2.json()
        return {
            "patient_id": UUID(data["patient_id"]),
            "access_token": data["access_token"],
            "phone": phone,
        }

    @pytest_asyncio.fixture(scope="function", loop_scope="session")
    async def platform_founder_auth(client, seed_data):
        """Login as platform founder (1a-E2 seed user)."""
        r = await client.post(
            "/api/v1/platform/auth/login",
            json={
                "email": seed_data["platform_founder_email"],
                "password": seed_data["platform_founder_password"],
            },
        )
        assert r.status_code == 200, r.text
        data = r.json()
        return {
            "access_token": data["access_token"],
            "founder_id": data["founder_id"],
        }

    @pytest_asyncio.fixture(scope="function", loop_scope="session")
    async def admin_auth(client, seed_data):
        """Log in as admin (seed_data admin). Returns dict: access_token, admin_id, clinic_id.
        Kept function-scoped; rate limit for admin login is disabled in TESTING=1 (config) to avoid 429 in full suite."""
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": seed_data["admin_email"], "password": "password123"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        return {
            "access_token": data["access_token"],
            "admin_id": data["admin_id"],
            "clinic_id": data["clinic_id"],
        }

    @pytest_asyncio.fixture(scope="function", loop_scope="session")
    async def doctor_auth(client, seed_data):
        """Clinic user with role `doctor` (no ``patients.pii.read``)."""
        r = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": seed_data["doctor_email"], "password": "password123"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        return {
            "access_token": data["access_token"],
            "admin_id": data["admin_id"],
            "clinic_id": data["clinic_id"],
        }

    @pytest_asyncio.fixture(scope="function", loop_scope="session")
    async def client(init_db, seed_data):
        """HTTP client for API tests (uses app and seed_data so DB is ready)."""
        from tests.conftest import app as app_ref
        async with AsyncClient(
            transport=ASGITransport(app=app_ref, raise_app_exceptions=False),
            base_url="http://test",
        ) as ac:
            yield ac

    @pytest_asyncio.fixture(scope="function", loop_scope="session")
    async def db_session(init_db, seed_data):
        """
        Async SQLAlchemy session for service-layer tests.

        Keep function scope for isolation and close in the same running loop.
        """
        from src.infrastructure.database import base as db_base

        session = db_base.AsyncSessionLocal()
        try:
            yield session
        finally:
            try:
                await session.rollback()
            except Exception:
                pass
            try:
                await session.close()
            except (RuntimeError, AttributeError):
                # Windows + pytest teardown can close the loop/proactor before asyncpg cleanup.
                # Keep teardown best-effort to avoid false-negative suite failures.
                pass


# redis_integration: skip when Redis is down — RateLimiter fails open on errors, so tests would
# falsely expect RateLimitExceeded while teardown then fails on redis.delete (see 10-Q8).
_redis_sync_ping_result: bool | None = None


def _redis_reachable_for_integration_tests() -> bool:
    global _redis_sync_ping_result
    if _redis_sync_ping_result is not None:
        return _redis_sync_ping_result
    url = (os.environ.get("REDIS_URL") or "redis://localhost:6379/0").strip()
    try:
        import redis as redis_sync

        client = redis_sync.Redis.from_url(
            url,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        client.ping()
        _redis_sync_ping_result = True
    except Exception:
        _redis_sync_ping_result = False
    return _redis_sync_ping_result


def pytest_runtest_setup(item: pytest.Item) -> None:
    if not item.get_closest_marker("redis_integration"):
        return
    flag = os.environ.get("RUN_REDIS_INTEGRATION_TESTS", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        pytest.skip("redis_integration tests skipped (RUN_REDIS_INTEGRATION_TESTS disabled)")
    if not _redis_reachable_for_integration_tests():
        pytest.skip(
            "Redis not reachable for redis_integration tests (check REDIS_URL; e.g. docker compose up -d redis). "
            "Opt out: RUN_REDIS_INTEGRATION_TESTS=0"
        )
