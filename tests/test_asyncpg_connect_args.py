"""Regression: Windows + Docker Postgres RST on asyncpg SSL upgrade (WinError 10054)."""

from src.infrastructure.database.base import (
    _asyncpg_connect_args,
    _is_transient_connect_error,
)


def test_asyncpg_skips_ssl_probe_for_local_hosts() -> None:
    for dsn in (
        "postgresql+asyncpg://u:p@localhost:5442/db",
        "postgresql+asyncpg://u:p@127.0.0.1:5442/db",
        "postgresql+asyncpg://u:p@db:5432/db",
    ):
        args = _asyncpg_connect_args(dsn)
        assert args["ssl"] is False, dsn
        assert args["timeout"] == 30
        assert args["command_timeout"] == 120
        assert args["statement_cache_size"] == 0


def test_asyncpg_honors_sslmode_require() -> None:
    args = _asyncpg_connect_args(
        "postgresql+asyncpg://u:p@localhost:5442/db?sslmode=require"
    )
    assert args["ssl"] is True


def test_transient_connect_error_detects_windows_rst() -> None:
    assert _is_transient_connect_error(ConnectionResetError(10054, "RST"))
    assert _is_transient_connect_error(ConnectionRefusedError())
    assert not _is_transient_connect_error(ValueError("bad dsn"))
