"""Smoke: Grafana dashboards in repo are valid JSON with expected shape (QA_ARCH §27–§28)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_DASHBOARDS_DIR = Path(__file__).resolve().parents[2] / "deploy" / "grafana" / "dashboards"


@pytest.mark.parametrize(
    "name",
    [
        "dental_booking_security_soc_w10.json",
        "dental_booking_observability_w1_w2.json",
    ],
)
def test_grafana_dashboard_is_valid_json(name: str) -> None:
    path = _DASHBOARDS_DIR / name
    assert path.is_file(), f"missing {path}"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("schemaVersion"), "schemaVersion required"
    assert isinstance(data.get("panels"), list)
    if name == "dental_booking_security_soc_w10.json":
        titles = [p.get("title") for p in data["panels"] if isinstance(p, dict)]
        assert any("spam_blocked" in str(t).lower() for t in titles)
