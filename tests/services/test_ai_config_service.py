from uuid import uuid4

from src.application.services.ai_config_service import AiConfigService, AiProviderConfig


def test_ai_config_service_returns_config():
    svc = AiConfigService()
    cfg = svc.get_clinic_ai_config(uuid4())

    assert isinstance(cfg, AiProviderConfig)
    # base_url can be empty in tests, but fields must exist
    assert cfg.model
    assert cfg.provider_type in {"external", "ru_compliant", "on_premise"}
    assert cfg.allow_personal_data in {True, False}

