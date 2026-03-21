"""Celery application configuration."""

from __future__ import annotations

from typing import Any, Callable

try:
    from celery.schedules import crontab
    from celery import Celery
except ModuleNotFoundError:  # pragma: no cover
    # Optional dependency for test/local environments.
    # We provide a minimal stub so that importing API modules does not fail when
    # Celery is not installed (e.g. in CI/unit-test runs focused on HTTP layer).
    crontab = None  # type: ignore[assignment]

    class _CeleryStub:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            return None

        def task(self, *args: Any, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
                return fn

            return decorator

        @property
        def conf(self) -> Any:
            class _Conf:
                def update(self, *args: Any, **kwargs: Any) -> None:
                    return None

            return _Conf()

    Celery = _CeleryStub  # type: ignore[assignment]

from src.core.config import settings

celery_app = Celery(
    "dental_booking",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "src.infrastructure.messaging.tasks.notifications",
        "src.infrastructure.messaging.tasks.ai_tasks",
        "src.infrastructure.messaging.tasks.loyalty_tasks",
        "src.infrastructure.messaging.tasks.owner_integrations",
        "src.infrastructure.messaging.tasks.export_tasks",
        "src.infrastructure.messaging.tasks.backup_tasks",
        "src.infrastructure.messaging.tasks.erp_tasks",
        "src.infrastructure.messaging.tasks.crm_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "run-reminders-every-15min": {
            "task": "notifications.run_reminders",
            "schedule": 900.0,  # 15 minutes in seconds
        },
        "run-ai-task-generator-daily": {
            "task": "ai_tasks.run_ai_task_generator",
            "schedule": 86400.0,  # once per day
        },
        "run-ai-task-manager-hourly": {
            "task": "ai_tasks.run_ai_task_manager_all_clinics",
            "schedule": 3600.0,  # once per hour
        },
        "check-expiring-packages-daily": {
            "task": "loyalty_tasks.check_expiring_packages",
            "schedule": 86400.0,  # B6.3: once per day
        },
        "run-loyalty-campaign-engine-daily": {
            "task": "loyalty_tasks.run_loyalty_campaign_engine_all_clinics",
            "schedule": 86400.0,  # LOY_AI_014: Tasks from campaign rules
        },
        "owner-morning-brief": {
            "task": "owner_integrations.send_all_morning_briefs",
            "schedule": crontab(hour=9, minute=0) if crontab else 9 * 3600,  # 09:00 UTC
        },
        "ai-supervisor-summary": {
            "task": "owner_integrations.send_all_ai_supervisor_summaries",
            "schedule": crontab(hour=20, minute=0) if crontab else 20 * 3600,  # 20:00 UTC
        },
        "cleanup-old-exports-and-backups": {
            "task": "export_tasks.cleanup_old_exports_and_backups",
            "schedule": crontab(hour=4, minute=0) if crontab else 4 * 3600,  # 04:00 UTC daily
        },
        "run-erp-aggregates-nightly": {
            "task": "erp_tasks.refresh_erp_aggregates_nightly",
            "schedule": crontab(hour=3, minute=30) if crontab else 3 * 3600 + 30 * 60,  # 03:30 UTC
        },
        "run-erp-visit-revenue-parity-sample-daily": {
            "task": "erp_tasks.run_daily_visit_revenue_parity_sample",
            "schedule": crontab(hour=5, minute=15) if crontab else 5 * 3600 + 15 * 60,  # 05:15 UTC after nightly
        },
    },
)
