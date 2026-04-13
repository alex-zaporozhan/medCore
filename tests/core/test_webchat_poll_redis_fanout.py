"""Redis fan-out webchat poll: timeout must not replay DB window (QA_ARCH duplicate-delivery guard)."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import src.application.services.webchat_push_manager as wpm
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_wait_for_webchat_poll_redis_timeout_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(wpm, "settings", SimpleNamespace(webchat_redis_fanout_enabled=True))

    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.close = AsyncMock()
    pubsub.get_message = AsyncMock(return_value=None)

    redis = MagicMock()
    redis.pubsub = MagicMock(return_value=pubsub)

    session = MagicMock(spec=AsyncSession)

    with patch(
        "src.infrastructure.database.redis_client.get_redis",
        new_callable=AsyncMock,
        return_value=redis,
    ):
        out = await wpm.wait_for_webchat_poll_items(
            session=session,  # type: ignore[arg-type]
            chat_id=uuid4(),
            timeout_seconds=0.01,
        )
    assert out == []
    session.execute.assert_not_called()
