"""Prometheus rule files: valid YAML, Phase 4 guard — owner + runbook_url on every alert (QA_ARCH)."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
RULES_FILE = REPO_ROOT / "deploy" / "prometheus" / "dental_booking_alerts.yml"


def test_dental_booking_alerts_yml_parses_and_has_groups() -> None:
    text = RULES_FILE.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict), "alerts file must be a mapping at root"
    groups = data.get("groups")
    assert isinstance(groups, list) and len(groups) > 0, "expected non-empty groups"
    for g in groups:
        assert "name" in g and "rules" in g
        assert isinstance(g["rules"], list) and len(g["rules"]) > 0


def test_each_alert_has_owner_severity_and_runbook() -> None:
    """04_DEV_EXECUTION_PLAN Phase 4: critical path alerts carry owner + runbook reference."""
    data = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8"))
    groups = data.get("groups") or []
    for g in groups:
        for rule in g.get("rules") or []:
            if "alert" not in rule:
                continue
            labels = rule.get("labels") or {}
            assert "owner" in labels and str(labels["owner"]).strip(), (
                f"rule {rule.get('alert')!r} must set labels.owner"
            )
            assert "severity" in labels, f"rule {rule.get('alert')!r} must set labels.severity"
            ann = rule.get("annotations") or {}
            assert "runbook_url" in ann and str(ann["runbook_url"]).strip(), (
                f"rule {rule.get('alert')!r} must set annotations.runbook_url"
            )
