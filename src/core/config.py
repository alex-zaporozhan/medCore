"""Application configuration from environment variables."""

import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    # Application
    app_name: str = "dental-booking"
    app_env: str = "development"
    debug: bool = True
    secret_key: str
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str
    db_pool_size: int = 20
    db_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_access_token_expire_minutes_patient: int = 60
    jwt_access_token_expire_minutes_admin: int = 20

    # Rate limiting
    rate_auth_send_code_ip_limit: int = 20
    rate_auth_send_code_ip_window_seconds: int = 600
    rate_auth_send_code_phone_limit: int = 5
    rate_auth_send_code_phone_window_seconds: int = 600

    rate_admin_login_ip_limit: int = 30
    rate_admin_login_ip_window_seconds: int = 600
    rate_admin_login_email_limit: int = 10
    rate_admin_login_email_window_seconds: int = 600

    rate_ai_clinic_limit: int = 60
    rate_ai_clinic_window_seconds: int = 60

    rate_ai_heavy_clinic_limit: int = 5
    rate_ai_heavy_clinic_window_seconds: int = 3600

    # YooKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_test_mode: bool = True
    yookassa_return_url: str = "https://localhost:5173/app/booking/success"

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""
    telegram_webhook_secret: str = ""  # Optional: X-Telegram-Bot-Api-Secret-Token for webhook verification

    # SMS (SMSC.ru)
    smsc_login: str = ""
    smsc_password: str = ""
    smsc_sender: str = ""
    smsc_enabled: bool = False
    smsc_timeout_seconds: int = 10

    # OAuth for patients (VK / Yandex)
    vk_client_id: str = ""
    vk_client_secret: str = ""
    vk_redirect_uri: str = ""
    yandex_client_id: str = ""
    yandex_client_secret: str = ""
    yandex_redirect_uri: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@dental-booking.local"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # AI provider (chat assistant)
    ai_provider_base_url: str = ""
    ai_provider_api_key: str = ""
    ai_timeout_seconds: int = 10
    ai_provider_model: str = "deepseek-chat"

    # Observability / metrics
    metrics_enabled: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _disable_admin_login_rate_limit_in_tests(self) -> "Settings":
        """In tests (TESTING=1), disable admin login rate limit to avoid 429 in full suite."""
        if os.environ.get("TESTING") == "1":
            object.__setattr__(self, "rate_admin_login_ip_limit", 0)
            object.__setattr__(self, "rate_admin_login_email_limit", 0)
        return self

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
