import pytest
from uuid import uuid4

from src.application.services.ai_config_service import AiConfigService, AiProviderConfig


@pytest.mark.asyncio
async def test_ai_config_service_returns_config():
    svc = AiConfigService()
    cfg = await svc.get_clinic_ai_config(uuid4())

    assert isinstance(cfg, AiProviderConfig)
    # base_url can be empty in tests, but fields must exist
    assert cfg.model
    assert cfg.provider_type in {"external", "ru_compliant", "on_premise"}
    assert cfg.allow_personal_data in {True, False}


@pytest.mark.asyncio
async def test_ai_config_service_policy_allow_personal_data_external():
    """For external provider personal data must never be allowed."""
    svc = AiConfigService()
    cfg = await svc.get_clinic_ai_config(uuid4())
    if cfg.provider_type == "external":
        assert cfg.allow_personal_data is False


class _FakeResult:
    def __init__(self, row: object | None) -> None:
        self._row = row

    def scalars(self) -> "_FakeResult":
        return self

    def first(self) -> object | None:
        return self._row


class _FakeRow:
    def __init__(self, ai_provider_type: str | None, ai_enabled: bool) -> None:
        self.ai_provider_type = ai_provider_type
        self.ai_enabled = ai_enabled


class _FakeSession:
    def __init__(self, row: _FakeRow | None) -> None:
        self._row = row

    async def execute(self, *_args, **_kwargs) -> _FakeResult:  # pragma: no cover - trivial plumbing
        return _FakeResult(self._row)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "provider_type,ai_enabled,expected",
    [
        ("external", True, False),
        ("external", False, False),
        ("ru_compliant", True, True),
        ("ru_compliant", False, False),
        ("on_premise", True, True),
        ("on_premise", False, False),
        (None, True, False),
    ],
)
async def test_ai_config_service_policy_matrix(provider_type, ai_enabled, expected):
    """Matrix test: provider_type/ai_enabled -> allow_personal_data according to policy."""
    row = _FakeRow(ai_provider_type=provider_type, ai_enabled=ai_enabled)
    fake_session = _FakeSession(row=row)
    svc = AiConfigService(session=fake_session)  # type: ignore[arg-type]

    cfg = await svc.get_clinic_ai_config(uuid4())

    assert cfg.provider_type in {"external", "ru_compliant", "on_premise"}
    assert cfg.allow_personal_data is expected

