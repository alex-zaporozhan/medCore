"""§24.3 RAG v1: метасимволы ILIKE в пользовательском запросе не расширяют выдачу."""

from src.application.services.organization_rag_kb_service import escape_ilike_user_fragment


def test_escape_ilike_user_fragment_escapes_percent_underscore_backslash() -> None:
    assert escape_ilike_user_fragment("a%b_c\\d") == "a\\%b\\_c\\\\d"


def test_escape_ilike_user_fragment_empty() -> None:
    assert escape_ilike_user_fragment("") == ""
