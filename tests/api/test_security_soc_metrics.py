"""Integration: §27–§28 SOC counters on real responses (middleware in main)."""

import pytest
from prometheus_client import REGISTRY


def _counter_total(metric_name: str, labels: dict[str, str]) -> float:
    """Counter metrics use family.name without ``_total`` (prometheus_client convention)."""
    base = metric_name[: -len("_total")] if metric_name.endswith("_total") else metric_name
    total = 0.0
    for family in REGISTRY.collect():
        if family.name != base:
            continue
        for sample in family.samples:
            if not sample.name.endswith("_total"):
                continue
            if all(sample.labels.get(k) == v for k, v in labels.items()):
                total += sample.value
    return total


@pytest.mark.asyncio
async def test_security_auth_failure_total_on_admin_session_without_auth(client):
    key = {"reason": "forbidden_privileged"}
    before = _counter_total("security_auth_failure_total", key)
    r = await client.get("/api/v1/admin/auth/session")
    assert r.status_code == 403
    after = _counter_total("security_auth_failure_total", key)
    assert after == before + 1


@pytest.mark.asyncio
async def test_security_auth_failure_total_on_patient_without_auth(client):
    key = {"reason": "public_unauthorized"}
    before = _counter_total("security_auth_failure_total", key)
    r = await client.get("/api/v1/patient/notification-settings")
    assert r.status_code == 401
    after = _counter_total("security_auth_failure_total", key)
    assert after == before + 1


@pytest.mark.asyncio
async def test_security_suspicious_request_total_on_probe_path(client):
    key = {"path_class": "admin_api", "reason": "known_probe_path"}
    before = _counter_total("security_suspicious_request_total", key)
    r = await client.get("/api/v1/admin/static/.git/config")
    assert r.status_code in (404, 405)
    after = _counter_total("security_suspicious_request_total", key)
    assert after == before + 1
