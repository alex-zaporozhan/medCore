"""Smoke test: POST /api/v1/payments/webhook."""

import pytest
from httpx import AsyncClient


@pytest.mark.regression_payments
@pytest.mark.asyncio
async def test_payments_webhook(client: AsyncClient):
    """POST /api/v1/payments/webhook with mock YooKassa payload returns 200 and status ok."""
    payload = {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": "test-payment-unknown-id"},
    }
    response = await client.post(
        "/api/v1/payments/webhook",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "ok"
