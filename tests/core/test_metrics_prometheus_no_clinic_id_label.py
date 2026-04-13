"""Regression: high-frequency metrics must not use per-tenant clinic_id labels (QA-AUDIT-001)."""

from __future__ import annotations

from pathlib import Path


def test_metrics_module_has_no_clinic_id_string() -> None:
    path = Path(__file__).resolve().parents[2] / "src" / "core" / "metrics.py"
    text = path.read_text(encoding="utf-8")
    assert "clinic_id" not in text, (
        "src/core/metrics.py must not contain 'clinic_id' — use clinic_bucket / "
        "aggregate labels per METRICS_PROTOCOL (see prometheus_labels.py)."
    )
