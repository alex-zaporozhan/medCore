"""AWS Secrets Manager bootstrap (PRC-A3)."""

import os
from unittest.mock import MagicMock, patch

import pytest

import src.core.runtime_secrets as rs


@pytest.fixture(autouse=True)
def _reset_bootstrap():
    rs.reset_runtime_secrets_bootstrap_for_tests()
    yield
    rs.reset_runtime_secrets_bootstrap_for_tests()


def test_apply_runtime_secrets_skips_when_testing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("AWS_SECRETS_MANAGER_SECRET_ID", "should-not-call")
    with patch("boto3.client") as mock_client:
        rs.apply_runtime_secrets_to_environ()
        mock_client.assert_not_called()


def test_apply_runtime_secrets_skips_without_secret_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AWS_SECRETS_MANAGER_SECRET_ID", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    with patch("boto3.client") as mock_client:
        rs.apply_runtime_secrets_to_environ()
        mock_client.assert_not_called()


def test_apply_runtime_secrets_merges_json(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setenv("AWS_SECRETS_MANAGER_SECRET_ID", "test/secret")
    monkeypatch.delenv("FROM_SECRET", raising=False)

    fake = MagicMock()
    fake.get_secret_value.return_value = {"SecretString": '{"FROM_SECRET": "abc", "KEEP": "new"}'}

    with patch("boto3.client", return_value=fake):
        rs.apply_runtime_secrets_to_environ()

    assert os.environ.get("FROM_SECRET") == "abc"
    monkeypatch.delenv("FROM_SECRET", raising=False)


def test_apply_runtime_secrets_does_not_override_nonempty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setenv("AWS_SECRETS_MANAGER_SECRET_ID", "test/secret")
    monkeypatch.setenv("ALREADY_SET", "original")

    fake = MagicMock()
    fake.get_secret_value.return_value = {"SecretString": '{"ALREADY_SET": "from-aws"}'}

    with patch("boto3.client", return_value=fake):
        rs.apply_runtime_secrets_to_environ()

    assert os.environ.get("ALREADY_SET") == "original"
