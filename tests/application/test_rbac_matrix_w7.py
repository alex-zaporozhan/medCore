"""SR9: regression tests for rbac_matrix role × permission expectations (W7)."""

from src.application.rbac_matrix import ALL_PERMISSION_CODES, ROLE_PERMISSIONS


def test_owner_has_all_permissions():
    assert set(ROLE_PERMISSIONS["owner"]) == ALL_PERMISSION_CODES


def test_manager_has_erp_and_attribution_reports_sr5():
    m = set(ROLE_PERMISSIONS["manager"])
    assert "erp.owner_reports.read" in m
    assert "attribution.reports.read" in m


def test_manager_lacks_global_finance_mutations():
    m = set(ROLE_PERMISSIONS["manager"])
    assert "manage_finance" not in m
    assert "manage_payroll" not in m
