"""Unit tests for Prometheus path normalization (PERF observability)."""

from src.core.metrics import metrics_path_for_request, normalize_metrics_path


def test_normalize_metrics_path_replaces_uuid() -> None:
    u = "550e8400-e29b-41d4-a716-446655440000"
    assert normalize_metrics_path(f"/api/v1/admin/crm/leads/{u}/stage") == (
        "/api/v1/admin/crm/leads/{id}/stage"
    )


def test_normalize_metrics_path_multiple() -> None:
    a = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    b = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
    assert normalize_metrics_path(f"/x/{a}/y/{b}") == "/x/{id}/y/{id}"


def test_normalize_metrics_path_numeric_segment() -> None:
    assert normalize_metrics_path("/api/v1/items/42/details") == "/api/v1/items/{id}/details"


def test_normalize_metrics_path_uuid_before_numeric() -> None:
    """UUID substitution runs first; remaining numeric segments still collapse."""
    u = "550e8400-e29b-41d4-a716-446655440000"
    assert normalize_metrics_path(f"/x/{u}/999") == "/x/{id}/{id}"


def test_metrics_path_prefers_route_template() -> None:
    class Route:
        path = "/api/v1/admin/crm/leads/{lead_id}"

    class Url:
        path = "/api/v1/admin/crm/leads/550e8400-e29b-41d4-a716-446655440000"

    class Req:
        scope: dict
        url = Url()

        def __init__(self) -> None:
            self.scope = {"route": Route()}

    assert metrics_path_for_request(Req()) == "/api/v1/admin/crm/leads/{lead_id}"


def test_metrics_path_fallback_without_route() -> None:
    class Url:
        path = "/api/v1/foo/550e8400-e29b-41d4-a716-446655440000"

    class Req:
        scope: dict = {}
        url = Url()

    assert metrics_path_for_request(Req()) == "/api/v1/foo/{id}"
