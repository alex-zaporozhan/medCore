"""Settings: Celery soft/hard time limits must be consistent."""

import pytest

from src.core.config import Settings


def _minimal_settings(**kwargs: object) -> Settings:
    base: dict[str, object] = {
        "secret_key": "x" * 32,
        "jwt_secret_key": "y" * 32,
        "database_url": "postgresql+asyncpg://u:p@127.0.0.1:5432/db",
    }
    base.update(kwargs)
    return Settings(**base)


def test_celery_soft_below_hard_ok() -> None:
    s = _minimal_settings(
        celery_task_time_limit_seconds=3600,
        celery_task_soft_time_limit_seconds=3300,
    )
    assert s.celery_task_soft_time_limit_seconds < s.celery_task_time_limit_seconds


def test_celery_soft_equal_hard_rejected() -> None:
    with pytest.raises(ValueError, match="CELERY_TASK_SOFT_TIME_LIMIT"):
        _minimal_settings(
            celery_task_time_limit_seconds=100,
            celery_task_soft_time_limit_seconds=100,
        )


def test_celery_zero_limits_skip_pair_check() -> None:
    """0 means unset / Celery no-limit semantics for operators who override."""
    s = _minimal_settings(
        celery_task_time_limit_seconds=0,
        celery_task_soft_time_limit_seconds=0,
    )
    assert s.celery_task_time_limit_seconds == 0
