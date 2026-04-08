"""Application configuration from environment variables."""

import os
from pathlib import Path

from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _bootstrap_runtime_secrets() -> None:
    """PRC-A3: optional AWS Secrets Manager JSON → os.environ before Settings()."""
    from src.core.runtime_secrets import apply_runtime_secrets_to_environ

    apply_runtime_secrets_to_environ()


_bootstrap_runtime_secrets()


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
    # Staff directory (profession categories JSON list).
    staff_directory_cache_enabled: bool = True
    staff_directory_cache_ttl_seconds: int = 120

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
    jwt_access_token_expire_minutes_platform_founder: int = 30
    #: Short-lived JWT after password OK when TOTP is required (1a-E3).
    jwt_platform_founder_mfa_expire_minutes: int = 5
    #: Issuer for tenant HS256 tokens (admin + patient), `iss` claim (1a-E6 / МП §19 п.3).
    jwt_issuer_tenant: str = "dental-booking-tenant"
    #: Expected `aud` for admin access JWT (`type=admin`).
    jwt_audience_admin: str = "dental-booking-admin"
    #: Expected `aud` for patient access JWT (`role=patient`).
    jwt_audience_patient: str = "dental-booking-patient"
    #: Issuer string for platform founder JWT (separate signing key; 1a-E6).
    jwt_issuer_platform: str = "dental-booking-platform"
    #: `aud` for founder access JWT (`type=platform_founder`).
    jwt_audience_platform_founder: str = "platform-internal"
    #: `aud` for MFA step JWT (`type=platform_founder_mfa`).
    jwt_audience_platform_founder_mfa: str = "platform-mfa-step"
    #: Accept tenant/founder tokens without `iss`/`aud` (cutover only). Set false in prod after rollout.
    jwt_legacy_allow_missing_iss_aud: bool = True

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

    # Chat anti-spam (enterprise): message send limits (per sender + per room)
    rate_admin_chat_send_per_admin_limit: int = 60
    rate_admin_chat_send_window_seconds: int = 60
    rate_admin_chat_send_per_conversation_limit: int = 30

    rate_patient_chat_send_per_patient_limit: int = 20
    rate_patient_chat_send_window_seconds: int = 60
    rate_patient_chat_send_per_conversation_limit: int = 12

    rate_staff_chat_send_per_admin_limit: int = 40
    rate_staff_chat_send_window_seconds: int = 60
    rate_staff_chat_send_per_room_limit: int = 20

    #: GET /clinics without admin JWT — per client IP (U-011 / публичный периметр).
    rate_public_clinics_list_ip_limit: int = 120
    #: POST /public/platform/signup/checkout — per IP (антиспам).
    rate_public_platform_checkout_ip_limit: int = 30
    rate_public_platform_checkout_ip_window_seconds: int = 600
    #: Same route — per normalized email (§27 / PRC-C1).
    rate_public_platform_checkout_email_limit: int = 10
    rate_public_platform_checkout_email_window_seconds: int = 600
    #: Резерв: ранее soft IP → Turnstile; при включённом Turnstile checkout всегда требует токен (см. public_platform_signup).
    rate_public_platform_checkout_captcha_soft_ip_limit: int = 5
    #: GET /public/platform/catalog/* — per IP (лендинг / скрейп). 0 = выкл.
    rate_public_platform_catalog_ip_limit: int = 240
    rate_public_platform_catalog_ip_window_seconds: int = 60
    #: CIDR allowlist: если непусто и peer в списке — client IP из Forwarded/XFF (checkout, catalog, webhook B).
    public_rate_limit_trusted_proxy_cidrs: str = ""
    #: TTL для `platform_signup_intents.expires_at` при создании checkout (pending_payment); очистка — Celery.
    platform_signup_intent_payment_ttl_days: int = 30
    # Platform founder Bearer (GET /platform/internal/*): per-IP window against brute force / noise.
    rate_platform_founder_auth_ip_limit: int = 120
    rate_platform_founder_auth_ip_window_seconds: int = 60
    rate_platform_founder_login_ip_limit: int = 30
    rate_platform_founder_login_ip_window_seconds: int = 600
    rate_platform_founder_login_email_limit: int = 10
    rate_platform_founder_login_email_window_seconds: int = 600
    #: POST /platform/auth/login/mfa — per IP (bruteforce TOTP).
    rate_platform_founder_mfa_ip_limit: int = 40
    rate_platform_founder_mfa_ip_window_seconds: int = 300
    rate_public_clinics_list_ip_window_seconds: int = 60

    #: Patient SMS/OAuth: если true — без ``clinic_slug`` нельзя резолвить «первую клинику в БД» (LEAD: только контекст клиники в prod).
    patient_auth_require_clinic_slug: bool = False
    #: Бюрст перебора несуществующих slug (ответы 400 UNKNOWN_CLINIC_SLUG); 0 = выкл.
    rate_auth_unknown_clinic_slug_ip_limit: int = 0
    rate_auth_unknown_clinic_slug_ip_window_seconds: int = 300

    # Adaptive captcha (Cloudflare Turnstile)
    turnstile_enabled: bool = False
    turnstile_site_key: str = ""
    turnstile_secret_key: str = ""
    # When soft limits are exceeded, require captcha (before hard 429/lockout).
    rate_auth_send_code_captcha_soft_ip_limit: int = 5
    rate_auth_verify_code_captcha_soft_ip_limit: int = 10
    rate_auth_captcha_soft_window_seconds: int = 600
    rate_webchat_message_captcha_soft_ip_limit: int = 10
    rate_webchat_message_window_seconds: int = 60

    # YooKassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_test_mode: bool = True
    yookassa_return_url: str = "https://localhost:5173/app/booking/success"
    #: Return URL for YooKassa redirect after SaaS platform checkout (1b-F5). Falls back to `yookassa_return_url` if empty.
    platform_saas_checkout_return_url: str = ""

    #: Contour A — POST /api/v1/payments/webhook. Empty = no header check (MVP); when set, require X-Patient-Payment-Webhook-Secret (U-006).
    patient_payment_webhook_secret: str = ""
    #: Production: if true, app refuses to start without PATIENT_PAYMENT_WEBHOOK_SECRET (Phase 0 / 0-Q1). Default false so SaaS-only deploys with global YooKassa are not blocked; set true when contour A is live.
    enforce_patient_payment_webhook_secret_in_production: bool = False
    #: POST /api/v1/payments/webhook — per client IP (Redis fixed window). 0 = disabled. Disabled automatically when TESTING=1.
    rate_patient_payment_webhook_ip_limit: int = 240
    rate_patient_payment_webhook_ip_window_seconds: int = 60
    # Platform SaaS subscription webhook (contour B). Separate secret from patient payments.
    platform_billing_webhook_secret: str = ""
    # JWT Основателя (`type=platform_founder`). Empty + non-production: fallback to JWT_SECRET_KEY. Empty + production: founder routes 503, app still starts.
    platform_founder_jwt_secret: str = ""
    #: Production policy (PRC-A2): block `/platform/internal/*` until TOTP enroll+confirm; login + `/platform/auth/totp/*` still allowed for bootstrap.
    platform_founder_totp_required: bool = False
    #: POST /public/platform/owner-invite/accept — per-IP (антиспам перебора токена).
    rate_platform_owner_invite_accept_ip_limit: int = 20
    rate_platform_owner_invite_accept_ip_window_seconds: int = 300
    #: POST platform billing webhook B — per client IP (антиспам / перебор секрета).
    rate_platform_billing_webhook_ip_limit: int = 240
    rate_platform_billing_webhook_ip_window_seconds: int = 60
    #: Throttle DB reads for platform_signup_intent_* gauges on GET /metrics (0 = every scrape).
    platform_billing_metrics_db_refresh_min_interval_seconds: float = 5.0
    #: GET/POST /public/embed/v1/* — per client IP (SaaS §24.4).
    rate_embed_public_ip_limit: int = 120
    rate_embed_public_ip_window_seconds: int = 60
    #: POST /public/embed/v1/hooks/{token}/inbox — per inbound route token + IP.
    rate_embed_webhook_token_ip_limit: int = 120
    rate_embed_webhook_token_ip_window_seconds: int = 60
    #: POST embed webhook inbox: требовать `X-Embed-Signature: v1=<hmac_sha256_hex>` (ключ = тот же Bearer secret).
    embed_webhook_signature_required: bool = False
    #: Максимальный размер тела POST webhook inbox (байты); 413 при превышении.
    embed_webhook_max_body_bytes: int = 1_048_576
    #: GET /public/embed/v1/session — отдельный лимит по IP (брутфорс secret); 0 = как у rate_embed_public_ip_limit.
    rate_embed_session_ip_limit: int = 0
    rate_embed_session_ip_window_seconds: int = 60
    #: POST /public/embed/v1/rag/search — доп. счётчик по IP поверх rate_embed_public_* (тяжёлый ILIKE). 0 = только общий embed-лимит.
    rate_embed_rag_search_ip_limit: int = 0
    rate_embed_rag_search_ip_window_seconds: int = 60
    #: RAG KB §24.3 retrieval: `ilike` (подстрока), `fts` (PostgreSQL tsvector + GIN), `hybrid` (FTS, при пустоте — ILIKE).
    rag_kb_search_mode: str = "ilike"
    #: Максимум фрагментов KB на одну организацию (admin create); 0 = без квоты.
    rag_kb_quota_max_documents_per_org: int = 0
    #: Публичный embed assistant: лимит входных токенов (оценка), §24.2.
    embed_ai_max_input_tokens: int = 2048
    embed_ai_max_output_tokens: int = 512

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

    # S3-compatible object storage (medical files)
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "us-east-1"
    s3_use_ssl: bool = True
    s3_presign_exp_seconds: int = 900
    # PHI/medical data: keep presigned links short-lived.
    s3_medical_presign_exp_seconds: int = 120
    s3_medical_prefix: str = "medical"

    # Staff avatars (S3; metadata in DB)
    s3_staff_avatars_prefix: str = "staff-avatars"
    s3_staff_avatars_presign_exp_seconds: int = 900
    staff_avatar_max_bytes: int = 2 * 1024 * 1024

    # Enterprise medical downloads (token-bound streaming proxy)
    medical_download_token_ttl_seconds: int = 120
    # Enforce user-agent binding for download tokens (recommended on).
    medical_download_token_bind_ua: bool = True
    # IP binding is fragile under corporate proxies; keep tolerant by default.
    medical_download_token_enforce_ip: bool = False
    # Trusted proxies (CIDR allowlist) for reading Forwarded/X-Forwarded-For client IP.
    # Example: "10.0.0.0/8,192.168.0.0/16,127.0.0.1/32"
    medical_trusted_proxy_cidrs: str = ""
    # When enabled and the immediate peer is trusted, use Forwarded/X-Forwarded-For to resolve real client IP.
    medical_resolve_client_ip_from_forwarded: bool = True

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

    # ADR-009: transactional outbox for critical domain events (contour A payment webhook).
    domain_outbox_payment_webhook_enabled: bool = True
    #: Contour B: after YooKassa succeeded, provision org via same outbox + dispatch (§17.1 / 2-E1).
    domain_outbox_platform_billing_provision_enabled: bool = True
    #: Booking lifecycle events (BookingCreated/Cancelled/Completed/NoShow) — same DB txn + post-commit dispatch.
    domain_outbox_booking_events_enabled: bool = True
    domain_outbox_dispatch_batch_limit: int = 50
    #: Min seconds between DB-backed outbox gauge refreshes on GET /metrics (0 = every scrape).
    domain_outbox_metrics_db_refresh_min_interval_seconds: float = 5.0
    #: Skip dispatch for rows with attempts >= this (0 = unlimited). Ops: reconcile or delete stuck rows.
    domain_outbox_max_dispatch_attempts: int = 0
    #: Phase 3 rollout: entitlement enforcement mode.
    #: - legacy: never enforce DB entitlements (except box hard-blocks)
    #: - auto: enforce only when org has entitlement rows (default safe rollout)
    #: - strict: enforce for all orgs, including legacy orgs without rows
    entitlement_enforcement_mode: str = "auto"
    #: Optional cohort rollout for strict enforcement in auto mode (comma-separated UUIDs).
    entitlement_enforcement_strict_org_ids: str = ""

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
    def _normalize_api_prefixes(self) -> "Settings":
        """
        FastAPI requires router prefixes to start with '/'.

        Some environments may provide API_V1_PREFIX without the leading slash (e.g. "api/v1"),
        which breaks app import and test collection.
        """
        p = (self.api_v1_prefix or "").strip()
        if not p:
            p = "/api/v1"
        if not p.startswith("/"):
            p = "/" + p
        if len(p) > 1:
            p = p.rstrip("/")
        object.__setattr__(self, "api_v1_prefix", p)
        return self

    @model_validator(mode="after")
    def _disable_admin_login_rate_limit_in_tests(self) -> "Settings":
        """In tests (TESTING=1), disable admin login rate limit to avoid 429 in full suite."""
        if os.environ.get("TESTING") == "1":
            object.__setattr__(self, "rate_admin_login_ip_limit", 0)
            object.__setattr__(self, "rate_admin_login_email_limit", 0)
            object.__setattr__(self, "rate_platform_founder_login_ip_limit", 0)
            object.__setattr__(self, "rate_platform_founder_login_email_limit", 0)
            object.__setattr__(self, "rate_public_clinics_list_ip_limit", 0)
            object.__setattr__(self, "rate_platform_founder_auth_ip_limit", 0)
            object.__setattr__(self, "rate_platform_owner_invite_accept_ip_limit", 0)
            object.__setattr__(self, "rate_platform_billing_webhook_ip_limit", 0)
            object.__setattr__(self, "rate_patient_payment_webhook_ip_limit", 0)
            object.__setattr__(self, "rate_public_platform_checkout_ip_limit", 0)
            object.__setattr__(self, "rate_public_platform_checkout_email_limit", 0)
            object.__setattr__(self, "rate_public_platform_checkout_captcha_soft_ip_limit", 0)
            object.__setattr__(self, "rate_public_platform_catalog_ip_limit", 0)
            object.__setattr__(self, "domain_outbox_metrics_db_refresh_min_interval_seconds", 0.0)
            object.__setattr__(self, "platform_billing_metrics_db_refresh_min_interval_seconds", 0.0)
            # Avoid suite-wide 403 on /platform/internal/* when .env sets prod TOTP policy; opt-in per test via monkeypatch.
            object.__setattr__(self, "platform_founder_totp_required", False)
        return self

    @model_validator(mode="after")
    def _apply_production_patient_auth_defaults(self) -> "Settings":
        """
        LEAD / QA_ARCH: in ``APP_ENV=production``, require ``clinic_slug`` for patient auth
        and rate-limit unknown slug probes — unless the corresponding env vars are set explicitly.

        Skipped when ``TESTING=1`` so pytest and local dev behavior stay unchanged.
        """
        if os.environ.get("TESTING") == "1":
            return self
        if (self.app_env or "").strip().lower() != "production":
            return self
        if "PATIENT_AUTH_REQUIRE_CLINIC_SLUG" not in os.environ:
            object.__setattr__(self, "patient_auth_require_clinic_slug", True)
        if "RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_LIMIT" not in os.environ:
            object.__setattr__(self, "rate_auth_unknown_clinic_slug_ip_limit", 90)
        if "RATE_AUTH_UNKNOWN_CLINIC_SLUG_IP_WINDOW_SECONDS" not in os.environ:
            object.__setattr__(self, "rate_auth_unknown_clinic_slug_ip_window_seconds", 600)
        return self

    @model_validator(mode="after")
    def _enforce_s3_ssl_in_prod(self) -> "Settings":
        """For PHI storage, require SSL in non-development environments."""
        if str(self.app_env).lower() not in ("development", "dev", "local"):
            if self.s3_endpoint and not bool(self.s3_use_ssl):
                raise ValueError("S3_USE_SSL must be enabled outside development")
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
