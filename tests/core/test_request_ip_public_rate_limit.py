"""client_ip_for_public_rate_limit (cross-cutting edge / XFF)."""

from unittest.mock import MagicMock

from src.core.request_ip import client_ip_for_public_rate_limit


def test_client_ip_empty_trust_uses_tcp_peer() -> None:
    req = MagicMock()
    req.client.host = "198.51.100.10"
    assert client_ip_for_public_rate_limit(req, trusted_proxy_cidrs="") == "198.51.100.10"


def test_client_ip_trusted_forwarded_for() -> None:
    req = MagicMock()
    req.client.host = "10.0.0.1"
    req.headers = {"x-forwarded-for": "203.0.113.5, 10.0.0.1"}
    assert (
        client_ip_for_public_rate_limit(req, trusted_proxy_cidrs="10.0.0.0/8")
        == "203.0.113.5"
    )
