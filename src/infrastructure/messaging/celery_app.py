"""Celery application configuration."""

from celery import Celery

from src.core.config import settings

celery_app = Celery(
    "dental_booking",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.infrastructure.messaging.tasks.notifications"],
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
    },
)
