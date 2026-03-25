"""Edition helper (Box vs Enterprise)."""

import pytest

from src.core import edition as edition_mod


def test_is_box_edition_default_enterprise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDITION", raising=False)
    assert edition_mod.is_box_edition() is False


@pytest.mark.parametrize("value", ["box", "BOX", "basic", " Basic "])
def test_is_box_edition_true(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("EDITION", value)
    assert edition_mod.is_box_edition() is True
