"""Omni admin SSE: Redis publish failures increment Prometheus counter."""

import uuid

import pytest
from prometheus_client import REGISTRY

from src.infrastructure.realtime import omni_pubsub


@pytest.mark.asyncio
async def test_publish_omni_message_created_increments_metric_when_redis_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom() -> None:
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(omni_pubsub, "get_redis", _boom)
    before = REGISTRY.get_sample_value(
        "omni_realtime_publish_failed_total", {"event": "message_created"}
    )
    if before is None:
        before = 0.0
    await omni_pubsub.publish_omni_message_created(
        clinic_id=uuid.uuid4(),
        chat_id=uuid.uuid4(),
        message_id=uuid.uuid4(),
    )
    after = REGISTRY.get_sample_value(
        "omni_realtime_publish_failed_total", {"event": "message_created"}
    )
    assert after is not None and after == before + 1.0


@pytest.mark.asyncio
async def test_publish_omni_chat_updated_increments_metric_when_redis_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _boom() -> None:
        raise OSError("broken pipe")

    monkeypatch.setattr(omni_pubsub, "get_redis", _boom)
    before = REGISTRY.get_sample_value(
        "omni_realtime_publish_failed_total", {"event": "chat_updated"}
    )
    if before is None:
        before = 0.0
    await omni_pubsub.publish_omni_chat_updated(
        clinic_id=uuid.uuid4(),
        chat_id=uuid.uuid4(),
        reason="test",
    )
    after = REGISTRY.get_sample_value(
        "omni_realtime_publish_failed_total", {"event": "chat_updated"}
    )
    assert after is not None and after == before + 1.0
