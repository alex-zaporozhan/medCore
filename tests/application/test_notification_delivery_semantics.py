"""P1-5: send_with_fallback must distinguish real channel delivery from log-only."""

from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_send_with_fallback_log_only_when_no_senders_configured():
    from src.application.services.notification_service import send_with_fallback

    class _NoSend:
        def is_configured(self) -> bool:
            return False

    nos = _NoSend()
    with patch(
        "src.application.services.notification_service._get_delivery_service",
        return_value=(nos, nos, nos),
    ):
        ok, err, delivery = await send_with_fallback(
            phone="+79001234567",
            message="hello",
            template="test_tpl",
            preferred_channel="sms",
        )
    assert ok is True
    assert err is None
    assert delivery == "log_only"


@pytest.mark.asyncio
async def test_send_with_fallback_channel_when_telegram_succeeds():
    from src.application.services.notification_service import send_with_fallback

    class _SmsOff:
        def is_configured(self) -> bool:
            return False

    class _TgOk:
        def is_configured(self) -> bool:
            return True

        async def send(self, **kwargs: object) -> None:
            return None

    sms = _SmsOff()
    tg = _TgOk()
    with patch(
        "src.application.services.notification_service._get_delivery_service",
        return_value=(tg, sms, _SmsOff()),
    ):
        ok, err, delivery = await send_with_fallback(
            chat_id="111",
            message="hello",
            template="test_tpl",
            preferred_channel="telegram",
        )
    assert ok is True
    assert err is None
    assert delivery == "channel"
