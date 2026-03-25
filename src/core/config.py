"""Application configuration from environment variables."""

import os
from pathlib import Path

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


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
    # Optional read replica for reporting GETs (Wave 5 / ADR-005). Unset = primary only.
    database_replica_url: str | None = None
    db_pool_size: int = 20
    db_max_overflow: int = 10
    # Applied to reporting sessions (SET LOCAL); 0 = disabled.
    db_reporting_statement_timeout_ms: int = 120_000
    # GET /health/replica: add "lag_warning" when observed lag exceeds this (seconds).
    db_replica_lag_warn_seconds: float = 60.0

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_pool_size: int = 10
    # ERP admin dashboard JSON cache (A9); invalidated after aggregate refresh.
    erp_dashboard_cache_enabled: bool = True
    erp_dashboard_cache_ttl_seconds: int = 60

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Form send-link: base URL for form fill page (token appended as ?token=...)
    form_link_base_url: str = ""

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

    #: POST /admin/omni-chats/{id}/messages — per admin_id (P0-H / ARCH §5).
    rate_admin_omni_send_per_admin_limit: int = 30
    rate_admin_omni_send_window_seconds: int = 60

    # YooKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_test_mode: bool = True
    yookassa_return_url: str = "https://localhost:5173/app/booking/success"

    # Telegram Bot
    telegram_bot_token: str = ""
    telegram_admin_chat_id: str = ""
    telegram_owner_chat_id: str = ""  # Owner briefs (G5); fallback to telegram_admin_chat_id if unset
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

    # Staff chat attachments (local disk; clinic-scoped paths)
    staff_chat_upload_root: str = "data/staff_chat_uploads"
    staff_chat_max_attachment_bytes: int = 5 * 1024 * 1024

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"
    log_mask_pii: bool = True

    # AI provider (chat assistant)
    ai_provider_base_url: str = ""
    ai_provider_api_key: str = ""
    ai_timeout_seconds: int = 10
    ai_provider_model: str = "deepseek-chat"
    # Omnichannel AI Telegram notifications (operator/suggestions). Disabled suggestions by
    # default to avoid noisy messages on local/demo startup unless explicitly enabled.
    omni_ai_notify_suggestion_telegram_enabled: bool = False
    omni_ai_notify_operator_telegram_enabled: bool = True
    omni_ai_notify_suggestion_dedup_seconds: int = 300
    omni_ai_notify_operator_dedup_seconds: int = 120

    # Observability / metrics
    metrics_enabled: bool = True

    # ERP report pre-aggregates (Engine L2): read from vitrine when populated; Celery refresh
    erp_reports_read_from_aggregate: bool = True
    # Per-report overrides (A14): if set, wins over erp_reports_read_from_aggregate for that vitrine only.
    erp_visit_revenue_read_from_aggregate: bool | None = None
    erp_payroll_read_from_aggregate: bool | None = None
    erp_materials_read_from_aggregate: bool | None = None
    erp_attribution_read_from_aggregate: bool | None = None
    erp_aggregate_refresh_lookback_days: int = 8
    # If max(updated_at) for vitrine rows in the requested date range is older than this, read path
    # falls back to raw ERP query (financial correctness over latency).
    erp_aggregate_stale_max_seconds: int = 7200
    # BOOKING_COMPLETED → Celery refresh for visit day (off by default; needs Redis + worker).
    erp_aggregate_event_refresh_enabled: bool = False
    erp_aggregate_event_debounce_seconds: int = 120
    # Daily Celery: one clinic × yesterday UTC — compare raw vs visit_revenue vitrine totals (low-cost trust signal).
    erp_aggregate_parity_sample_enabled: bool = False

    # Compliance: immutable DB audit for selected CRM admin mutations (CRM_MONEY H6).
    compliance_crm_audit_enabled: bool = False

    # Booking AI tools (BKG_AI_TOOLS_006 / QA_ARCH W4.1 J3): cap LLM-facing slot payloads.
    booking_ai_tools_max_range_days: int = 14
    booking_ai_tools_max_slots: int = 80

    # Burst → Attention Task (QA_ARCH W7 BE5); uses Redis + separate DB session.
    booking_error_attention_enabled: bool = False
    booking_error_attention_window_seconds: int = 300
    booking_error_attention_threshold: int = 12

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

    @model_validator(mode="after")
    def _resolve_staff_chat_upload_root(self) -> "Settings":
        """
        Make `staff_chat_upload_root` independent of backend working directory.

        Previously this was a relative path (e.g. `data/staff_chat_uploads`),
        which can break after restart when CWD changes, turning attachment
        previews into download links (404/empty payload on blob fetch).
        """
        p = Path(self.staff_chat_upload_root)
        if not p.is_absolute():
            resolved = (_REPO_ROOT / p).resolve()
            # Ensure base directory exists for subsequent writes.
            resolved.mkdir(parents=True, exist_ok=True)
            object.__setattr__(self, "staff_chat_upload_root", str(resolved))
        return self

    def erp_read_from_aggregate_for_kind(
        self,
        kind: Literal["visit_revenue", "payroll", "materials", "attribution"],
    ) -> bool:
        """Whether GET report paths may read from L2 vitrine for this aggregate kind."""
        override = {
            "visit_revenue": self.erp_visit_revenue_read_from_aggregate,
            "payroll": self.erp_payroll_read_from_aggregate,
            "materials": self.erp_materials_read_from_aggregate,
            "attribution": self.erp_attribution_read_from_aggregate,
        }[kind]
        if override is not None:
            return bool(override)
        return bool(self.erp_reports_read_from_aggregate)

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


settings = Settings()
