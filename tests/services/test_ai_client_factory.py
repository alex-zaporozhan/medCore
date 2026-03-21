import pytest
from uuid import uuid4

from src.application.services.ai_client_factory import build_safe_ai_client, SafeAiClientContext
from src.application.services import ai_client_factory as factory_module


@pytest.mark.asyncio
async def test_build_safe_ai_client_global_mode_has_no_personal_data():
    """Global (clinic_id=None) AI client must never allow personal data."""
    safe_client, ctx = await build_safe_ai_client(clinic_id=None, session=None)

    assert safe_client is not None
    assert isinstance(ctx, SafeAiClientContext)
    assert ctx.clinic_id is None
    assert ctx.allow_personal_data is False


@pytest.mark.asyncio
async def test_build_safe_ai_client_passes_allow_personal_data_to_sanitizer(monkeypatch):
    """AiSanitizer in factory must receive allow_personal_data from AiProviderConfig."""

    captured_allow_flag: list[bool] = []

    class FakeConfig(factory_module.AiProviderConfig):  # type: ignore[misc]
        pass

    async def fake_get_clinic_ai_config(self, clinic_id):  # type: ignore[unused-argument]
        return FakeConfig(
            base_url="http://test",
            api_key="key",
            model="gpt-test",
            allow_personal_data=True,
            provider_type="ru_compliant",
        )

    class FakeAiSanitizer:
        def __init__(self, allow_personal_data: bool = False) -> None:
            captured_allow_flag.append(allow_personal_data)

        def sanitize(self, text: str):
            class _Result:
                def __init__(self, original: str) -> None:
                    self.original = original
                    self.sanitized = original

            return _Result(text)

    monkeypatch.setattr(factory_module.AiConfigService, "get_clinic_ai_config", fake_get_clinic_ai_config)
    monkeypatch.setattr(factory_module, "AiSanitizer", FakeAiSanitizer)

    safe_client, ctx = await build_safe_ai_client(clinic_id=uuid4(), session=object())  # type: ignore[arg-type]

    assert safe_client is not None
    assert isinstance(ctx, SafeAiClientContext)
    assert ctx.allow_personal_data is True
    assert ctx.provider_type == "ru_compliant"
    assert captured_allow_flag == [True]


@pytest.mark.asyncio
async def test_build_safe_ai_client_external_provider_forces_no_personal_data(monkeypatch):
    """For external provider, factory must enforce allow_personal_data=False for sanitizer and context."""

    captured_allow_flag: list[bool] = []

    class FakeConfig(factory_module.AiProviderConfig):  # type: ignore[misc]
        pass

    async def fake_get_clinic_ai_config(self, clinic_id):  # type: ignore[unused-argument]
        return FakeConfig(
            base_url="http://test",
            api_key="key",
            model="gpt-test",
            allow_personal_data=False,
            provider_type="external",
        )

    class FakeAiSanitizer:
        def __init__(self, allow_personal_data: bool = False) -> None:
            captured_allow_flag.append(allow_personal_data)

        def sanitize(self, text: str):
            class _Result:
                def __init__(self, original: str) -> None:
                    self.original = original
                    self.sanitized = original

            return _Result(text)

    monkeypatch.setattr(factory_module.AiConfigService, "get_clinic_ai_config", fake_get_clinic_ai_config)
    monkeypatch.setattr(factory_module, "AiSanitizer", FakeAiSanitizer)

    safe_client, ctx = await build_safe_ai_client(clinic_id=uuid4(), session=object())  # type: ignore[arg-type]

    assert safe_client is not None
    assert isinstance(ctx, SafeAiClientContext)
    assert ctx.provider_type == "external"
    assert ctx.allow_personal_data is False
    assert captured_allow_flag == [False]

