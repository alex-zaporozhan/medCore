"""Per-kind ERP vitrine read flags (QA_ARCH A14)."""

from src.core.config import Settings


def test_erp_read_from_aggregate_for_kind_falls_back_to_master() -> None:
    s = Settings.model_construct(
        secret_key="s",
        jwt_secret_key="j",
        database_url="postgresql+asyncpg://localhost/test",
        erp_reports_read_from_aggregate=True,
        erp_payroll_read_from_aggregate=None,
        erp_visit_revenue_read_from_aggregate=None,
        erp_materials_read_from_aggregate=None,
        erp_attribution_read_from_aggregate=None,
    )
    assert s.erp_read_from_aggregate_for_kind("payroll") is True
    assert s.erp_read_from_aggregate_for_kind("visit_revenue") is True


def test_erp_read_from_aggregate_for_kind_override_wins() -> None:
    s = Settings.model_construct(
        secret_key="s",
        jwt_secret_key="j",
        database_url="postgresql+asyncpg://localhost/test",
        erp_reports_read_from_aggregate=True,
        erp_payroll_read_from_aggregate=False,
        erp_visit_revenue_read_from_aggregate=None,
        erp_materials_read_from_aggregate=None,
        erp_attribution_read_from_aggregate=None,
    )
    assert s.erp_read_from_aggregate_for_kind("payroll") is False
    assert s.erp_read_from_aggregate_for_kind("visit_revenue") is True
