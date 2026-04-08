"""Main FastAPI application entry point."""

import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from sqlalchemy import text

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.payment_webhook_governance import (
    assert_distinct_payment_webhook_secrets,
    assert_enforced_patient_payment_webhook_secret_in_production,
    assert_required_security_secrets_in_production,
    log_payment_webhook_governance_on_startup,
)
from src.core.logging import setup_logging
from src.application.services.domain_outbox_service import refresh_domain_outbox_gauges
from src.application.services.platform_billing_service import refresh_platform_billing_provision_gauges
from src.core.metrics import (
    db_replica_lag_observed_seconds,
    http_request_duration_seconds,
    metrics_path_for_request,
    render_prometheus_metrics,
    security_auth_failure_total,
    security_suspicious_request_total,
    spam_blocked_total,
)
from src.core.security_observability import (
    security_auth_failure_reason,
    spam_blocked_channel,
    suspicious_request_signal,
)
from src.application.events.event_bus import get_event_bus
from src.application.events.lead_event_handlers import register_lead_event_handlers
from src.application.events.erp_event_handlers import register_erp_event_handlers
from src.application.events.loyalty_event_handlers import register_loyalty_event_handlers
from src.application.events.tasks_event_handlers import register_tasks_event_handlers
from src.application.events.marketing_attribution_event_handlers import (
    register_marketing_event_handlers,
)
from src.core.http_exception_handler import unified_http_exception_handler
from src.core.openapi_error_schemas import (
    STANDARD_OPENAPI_ERROR_RESPONSES,
    merge_public_error_schemas_into_openapi,
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info(
        "[dental-booking] Application started",
        extra={"component": "main", "env": settings.app_env},
    )
    assert_distinct_payment_webhook_secrets()
    assert_enforced_patient_payment_webhook_secret_in_production()
    assert_required_security_secrets_in_production()
    log_payment_webhook_governance_on_startup()
    # Production: PLATFORM_FOUNDER_JWT_SECRET is required by assert_required_security_secrets_in_production;
    # founder routes 503 only if policy changes — do not duplicate warnings here.

    # Register event handlers for cross-cutting modules (CRM, ERP, Loyalty, Tasks, Marketing Attribution)
    event_bus = get_event_bus()
    register_lead_event_handlers(event_bus)
    register_erp_event_handlers(event_bus)
    register_loyalty_event_handlers(event_bus)
    register_tasks_event_handlers(event_bus)
    register_marketing_event_handlers(event_bus)
    yield
    from src.infrastructure.database.redis_client import close_redis
    await close_redis()
    logger.info("[dental-booking] Application shutdown", extra={"component": "main"})


# Determine docs availability based on environment
if settings.app_env.lower() == "production":
    docs_url = None
    redoc_url = None
else:
    docs_url = "/docs"
    redoc_url = "/redoc"

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    debug=settings.debug,
    docs_url=docs_url,
    redoc_url=redoc_url,
    lifespan=lifespan,
    openapi_tags=[
        {
            "name": "00_error_contract",
            "description": (
                "Unified JSON error bodies (§28 / 1c-Q4 partial): open /openapi.json → "
                "components.schemas → ApiHttpErrorBody, ApiValidationErrorBody, ApiInternalErrorBody. "
                "Registry: docs/architecture/API_PUBLIC_ERROR_CODES.md. "
                "Per-route response links are backlog 10-Q7 / 1c-Q4."
            ),
        },
    ],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def trace_id_middleware(request: Request, call_next):
    """
    Extract or generate X-Trace-Id and attach to request.state.

    The same trace_id is then propagated via RequestContext and can be
    included into structured logs and downstream metrics.
    """
    trace_id = request.headers.get("X-Trace-Id")
    if not trace_id:
        import uuid

        trace_id = str(uuid.uuid4())

    # Attach to request state for later use in dependencies/services
    request.state.trace_id = trace_id

    response: Response = await call_next(request)
    # Optionally expose trace id to caller
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.middleware("http")
async def prometheus_http_duration_middleware(request: Request, call_next):
    """Record request duration for key paths (PERF / OBS); skips health and metrics scrapes."""
    path = request.url.path
    if path in ("/metrics", "/health", "/health/replica"):
        return await call_next(request)
    method = request.method
    t0 = time.perf_counter()
    response: Response | None = None
    status_class = "5xx"
    try:
        response = await call_next(request)
        code = response.status_code
        status_class = f"{code // 100}xx"
        return response
    except Exception:
        status_class = "5xx"
        raise
    finally:
        elapsed = time.perf_counter() - t0
        tpl = metrics_path_for_request(request)
        http_request_duration_seconds.labels(
            method=method,
            path=tpl,
            status_class=status_class,
        ).observe(elapsed)


@app.middleware("http")
async def security_soc_metrics_middleware(request: Request, call_next):
    """§27–§28: low-cardinality counters for 429, 401/403, and trivial probes."""
    path = request.url.path
    q = request.url.query or ""
    sig = suspicious_request_signal(path, q)
    if sig is not None:
        pc, reason = sig
        security_suspicious_request_total.labels(path_class=pc, reason=reason).inc()

    response: Response = await call_next(request)
    code = getattr(response, "status_code", None)
    if code == 429:
        spam_blocked_total.labels(channel=spam_blocked_channel(path)).inc()
    elif code is not None:
        rsn = security_auth_failure_reason(path, int(code))
        if rsn:
            security_auth_failure_total.labels(reason=rsn).inc()
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Логируем необработанные исключения и возвращаем 500 без раскрытия деталей."""
    logger.exception(
        "Unhandled exception: %s",
        exc,
        extra={"path": request.url.path, "method": request.method},
    )
    trace_id = getattr(request.state, "trace_id", None)
    body: dict = {
        "detail": "Внутренняя ошибка сервера. Проверьте логи бэкенда и применение миграций БД (alembic upgrade head).",
        "code": "internal_server_error",
    }
    if trace_id:
        body["trace_id"] = trace_id
    return JSONResponse(status_code=500, content=body)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Delegates to ``unified_http_exception_handler`` (defined outside ``main`` for lightweight tests)."""
    return await unified_http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Normalize FastAPI/Pydantic validation errors to the same envelope."""
    trace_id = getattr(request.state, "trace_id", None)

    # `exc.errors()` may contain non-JSON-serializable objects in `ctx` (e.g. ValueError instances).
    # Keep a stable, JSON-safe shape for clients and logs.
    safe_errors: list[dict] = []
    for e in exc.errors():
        if not isinstance(e, dict):
            safe_errors.append({"message": str(e)})
            continue
        e2 = dict(e)
        e2.pop("ctx", None)
        safe_errors.append(e2)

    body: dict = {
        "detail": "Некорректные данные запроса",
        "code": "validation_error",
        "errors": safe_errors,
    }
    if trace_id:
        body["trace_id"] = trace_id
    return JSONResponse(status_code=422, content=body)

# Include API router (10-Q7 / 1c-Q4: standard error bodies on all v1 operations)
app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
    responses=STANDARD_OPENAPI_ERROR_RESPONSES,
)
if settings.api_v1_prefix != "/api/v1":
    # Compatibility alias: many clients/tests assume /api/v1 regardless of env config.
    app.include_router(
        api_router,
        prefix="/api/v1",
        responses=STANDARD_OPENAPI_ERROR_RESPONSES,
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/health/s3")
async def health_s3():
    """Probe S3-compatible storage (medical files)."""
    from src.infrastructure.storage.s3_storage import MedicalFilesStorage

    storage = MedicalFilesStorage()
    return storage.health_check()


@app.get("/health/replica")
async def health_replica():
    """Probe reporting DSN (replica): lag when standby; updates ``db_replica_lag_observed_seconds`` gauge."""
    if not settings.database_replica_url:
        return {
            "replica_configured": False,
            "detail": "DATABASE_REPLICA_URL unset; reporting uses primary.",
        }
    from src.infrastructure.database import base as db_base

    if db_base.AsyncSessionLocalReporting is None:
        return JSONResponse(
            status_code=503,
            content={"replica_configured": True, "reachable": False, "detail": "database session factory not ready"},
        )

    ms = int(settings.db_reporting_statement_timeout_ms)
    try:
        async with db_base.AsyncSessionLocalReporting() as session:
            if ms > 0:
                await session.execute(text(f"SET LOCAL statement_timeout = {ms}"))
            row = (
                await session.execute(
                    text(
                        """
                        SELECT
                          pg_is_in_recovery() AS in_recovery,
                          CASE
                            WHEN pg_is_in_recovery()
                            THEN EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))
                          END AS lag_seconds
                        """
                    )
                )
            ).one()
            in_recovery = bool(row[0])
            lag_raw = row[1]
            lag_seconds = float(lag_raw) if lag_raw is not None else None
            if in_recovery and lag_seconds is not None:
                db_replica_lag_observed_seconds.set(lag_seconds)
            else:
                db_replica_lag_observed_seconds.set(0.0)

            await session.commit()

            warn = float(settings.db_replica_lag_warn_seconds)
            lag_warning = bool(
                in_recovery and lag_seconds is not None and lag_seconds > warn
            )
            return {
                "replica_configured": True,
                "reachable": True,
                "in_recovery": in_recovery,
                "lag_seconds": lag_seconds,
                "lag_warning": lag_warning,
                "lag_warn_threshold_seconds": warn,
            }
    except Exception as exc:
        logger.warning("health_replica_probe_failed", extra={"error": str(exc)})
        return JSONResponse(
            status_code=503,
            content={
                "replica_configured": True,
                "reachable": False,
                "detail": "reporting DSN probe failed",
                "error": str(exc),
            },
        )


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint for observability and alerting."""
    await refresh_domain_outbox_gauges()
    await refresh_platform_billing_provision_gauges()
    payload, content_type = render_prometheus_metrics()
    return Response(content=payload, media_type=content_type)


def custom_openapi() -> dict:
    """Attach shared error body schemas for OpenAPI/Redoc (1c-Q4 partial)."""
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    merge_public_error_schemas_into_openapi(openapi_schema)
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
