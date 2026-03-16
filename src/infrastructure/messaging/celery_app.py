"""Celery application configuration."""

from celery.schedules import crontab

from celery import Celery

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
        "check-expiring-packages-daily": {
            "task": "loyalty_tasks.check_expiring_packages",
            "schedule": 86400.0,  # B6.3: once per day
        },
        "owner-morning-brief": {
            "task": "owner_integrations.send_all_morning_briefs",
            "schedule": crontab(hour=9, minute=0),  # 09:00 UTC
        },
        "ai-supervisor-summary": {
            "task": "owner_integrations.send_all_ai_supervisor_summaries",
            "schedule": crontab(hour=20, minute=0),  # 20:00 UTC
        },
        "cleanup-old-exports-and-backups": {
            "task": "export_tasks.cleanup_old_exports_and_backups",
            "schedule": crontab(hour=4, minute=0),  # 04:00 UTC daily
        },
    },
)
