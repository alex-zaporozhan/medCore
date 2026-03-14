"""Main FastAPI application entry point."""

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.v1.router import api_router
from src.core.config import settings
from src.core.logging import setup_logging
from src.core.metrics import render_prometheus_metrics
from src.application.events.event_bus import get_event_bus
from src.application.events.lead_event_handlers import register_lead_event_handlers
from src.application.events.erp_event_handlers import register_erp_event_handlers
from src.application.events.loyalty_event_handlers import register_loyalty_event_handlers
from src.application.events.tasks_event_handlers import register_tasks_event_handlers
from src.application.events.marketing_attribution_event_handlers import (
    register_marketing_event_handlers,
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
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Логируем необработанные исключения и возвращаем 500 без раскрытия деталей."""
    logger.exception(
        "Unhandled exception: %s",
        exc,
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Внутренняя ошибка сервера. Проверьте логи бэкенда и применение миграций БД (alembic upgrade head).",
        },
    )

# Include API router
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": settings.app_name}


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint for observability and alerting."""
    payload, content_type = render_prometheus_metrics()
    return Response(content=payload, media_type=content_type)
