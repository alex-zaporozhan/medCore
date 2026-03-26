"""Metrics and observability primitives for the application.

This module provides Prometheus-compatible counters for the omnichannel
assistant while remaining safe to import when `prometheus_client` is not
installed. In that case, all metric operations become no-ops.
"""

from __future__ import annotations

import re
from typing import Any

from src.core.config import settings

# Collapse UUID / numeric id segments for Prometheus labels (low cardinality).
_METRICS_PATH_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
# Path segments that are only digits (e.g. legacy numeric ids).
_METRICS_PATH_NUMERIC = re.compile(r"/\d+(?=/|$)")


def normalize_metrics_path(path: str) -> str:
    """Normalize URL path for metric labels: UUIDs and numeric id segments -> `{id}`."""
    p = _METRICS_PATH_UUID.sub("{id}", path)
    return _METRICS_PATH_NUMERIC.sub("/{id}", p)


def metrics_path_for_request(request: Any) -> str:
    """
    Prefer Starlette/FastAPI route template (e.g. ``/api/v1/foo/{id}``) when available
    to keep Prometheus label cardinality stable; else ``normalize_metrics_path`` on raw path.
    """
    scope = getattr(request, "scope", None) or {}
    route = scope.get("route")
    if route is not None:
        tpl = getattr(route, "path", None)
        if isinstance(tpl, str) and tpl:
            return tpl
    url = getattr(request, "url", None)
    raw = url.path if url is not None else str(scope.get("path", ""))
    return normalize_metrics_path(raw)

try:  # pragma: no cover - import guard
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover - graceful fallback when prometheus_client is missing
    _PROMETHEUS_AVAILABLE = False

    class _NoopMetric:
        def labels(self, *args: Any, **kwargs: Any) -> "_NoopMetric":  # type: ignore[name-match]
            return self

        def inc(self, *args: Any, **kwargs: Any) -> None:
            return None

        def observe(self, *args: Any, **kwargs: Any) -> None:
            return None

        def set(self, *args: Any, **kwargs: Any) -> None:
            return None

    def Counter(*args: Any, **kwargs: Any) -> _NoopMetric:  # type: ignore[no-redef]
        return _NoopMetric()

    def Histogram(*args: Any, **kwargs: Any) -> _NoopMetric:  # type: ignore[no-redef]
        return _NoopMetric()

    def Gauge(*args: Any, **kwargs: Any) -> _NoopMetric:  # type: ignore[no-redef]
        return _NoopMetric()

    def generate_latest(*args: Any, **kwargs: Any) -> bytes:  # type: ignore[no-redef]
        return b""

    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"  # type: ignore[assignment]



# ------------------------------------------------------------------------------
# Domain event bus (in-process subscribers)
# ------------------------------------------------------------------------------

domain_event_handler_failures_total = Counter(  # type: ignore[call-arg]
    "domain_event_handler_failures_total",
    "Handler exceptions during domain event publish (each handler isolated).",
    ["event_name", "handler"],
)


# ------------------------------------------------------------------------------
# Core omnichannel metrics
# ------------------------------------------------------------------------------

omni_messages_total = Counter(  # type: ignore[call-arg]
    "omni_messages_total",
    "Total omnichannel messages by direction, actor type and channel.",
    ["direction", "actor_type", "channel_id", "account_bucket"],
)

omni_ai_auto_replies_total = Counter(  # type: ignore[call-arg]
    "omni_ai_auto_replies_total",
    "Total AI auto replies sent to clients.",
    ["account_bucket"],
)

omni_ai_suggestions_total = Counter(  # type: ignore[call-arg]
    "omni_ai_suggestions_total",
    "Total AI suggestions stored as drafts for admins.",
    ["account_bucket"],
)

omni_ai_escalations_total = Counter(  # type: ignore[call-arg]
    "omni_ai_escalations_total",
    "Total AI escalations that require human operators.",
    ["reason"],
)

omni_ai_provider_errors_total = Counter(  # type: ignore[call-arg]
    "omni_ai_provider_errors_total",
    "Errors from external AI provider in omnichannel pipeline.",
    ["source", "error_type"],
)


# ------------------------------------------------------------------------------
# ERP loyalty obligations metrics
# ------------------------------------------------------------------------------

erp_loyalty_obligations_created_total = Counter(  # type: ignore[call-arg]
    "erp_loyalty_obligations_created_total",
    "Total ERP loyalty obligations created from subscription sales.",
    ["clinic_bucket"],
)

erp_loyalty_write_off_amount_total = Counter(  # type: ignore[call-arg]
    "erp_loyalty_write_off_amount_total",
    "Total monetary write-off amount for ERP loyalty obligations on visits.",
    ["clinic_bucket"],
)

erp_loyalty_sync_errors_total = Counter(  # type: ignore[call-arg]
    "erp_loyalty_sync_errors_total",
    "Total ERP loyalty obligation sync/consistency errors.",
    ["clinic_bucket", "error_type"],
)

loyalty_family_spend_denied_total = Counter(  # type: ignore[call-arg]
    "loyalty_family_spend_denied_total",
    "Denied subscription spend where beneficiary != owner (family link / limits).",
    ["clinic_bucket", "reason"],
)

loyalty_subscription_usage_path_total = Counter(  # type: ignore[call-arg]
    "loyalty_subscription_usage_path_total",
    "Subscription usage recorded by authorization path (owner / package member / FamilyLink).",
    ["clinic_bucket", "path"],
)

loyalty_family_link_lifecycle_total = Counter(  # type: ignore[call-arg]
    "loyalty_family_link_lifecycle_total",
    "FamilyLink rows created or deactivated (clinic-scoped).",
    ["clinic_bucket", "action"],
)

loyalty_campaign_runs_total = Counter(  # type: ignore[call-arg]
    "loyalty_campaign_runs_total",
    "Loyalty campaign engine runs by clinic and outcome.",
    ["clinic_bucket", "status"],
)

loyalty_campaign_tasks_created_total = Counter(  # type: ignore[call-arg]
    "loyalty_campaign_tasks_created_total",
    "Tasks created by loyalty campaign engine.",
    ["clinic_bucket", "campaign_type"],
)

loyalty_campaign_batch_errors_total = Counter(  # type: ignore[call-arg]
    "loyalty_campaign_batch_errors_total",
    "Failures when running loyalty campaign engine (e.g. per-clinic Celery batch).",
    ["clinic_bucket"],
)


# ------------------------------------------------------------------------------
# Multi-tenant boundaries (Booking / Schedule, BKG_MULTI)
# ------------------------------------------------------------------------------

multitenancy_clinic_mismatch_total = Counter(  # type: ignore[call-arg]
    "multitenancy_clinic_mismatch_total",
    "Cross-tenant clinic boundary denials (assert_entity, schedule guard, etc.).",
    ["source"],
)

# Booking / payment structured errors (BKG_ERRORS_005, QA_ARCH W7 BE4).
booking_errors_total = Counter(  # type: ignore[call-arg]
    "booking_errors_total",
    "Structured booking/payment errors by canonical code, clinic bucket and source (api vs ai_tool).",
    ["code", "clinic_bucket", "source"],
)

# Domain validation / business-rule errors (patients, schedule, …) — QA_ARCH observability.
domain_errors_total = Counter(  # type: ignore[call-arg]
    "domain_errors_total",
    "Structured domain-layer errors by domain, code and clinic bucket.",
    ["domain", "code", "clinic_bucket"],
)

booking_error_attention_tasks_created_total = Counter(  # type: ignore[call-arg]
    "booking_error_attention_tasks_created_total",
    "Tasks created from booking error burst threshold (BE5).",
    ["clinic_bucket", "code"],
)

payment_webhook_failures_total = Counter(  # type: ignore[call-arg]
    "payment_webhook_failures_total",
    "YooKassa webhook failures by reason (invalid_json, processing_error).",
    ["reason"],
)


# ------------------------------------------------------------------------------
# Business chain metrics (OBS_CHAINS_023)
# ------------------------------------------------------------------------------

business_chain_booking_erp_total = Counter(  # type: ignore[call-arg]
    "business_chain_booking_erp_total",
    "Total runs of Booking→ERP/CRM/Loyalty chain by clinic bucket and outcome.",
    ["clinic_bucket", "status"],
)

business_chain_booking_erp_errors_total = Counter(  # type: ignore[call-arg]
    "business_chain_booking_erp_errors_total",
    "Errors in Booking→ERP/CRM/Loyalty chain by clinic bucket and error type.",
    ["clinic_bucket", "error_type"],
)

business_chain_booking_erp_duration_seconds = Histogram(  # type: ignore[call-arg]
    "business_chain_booking_erp_duration_seconds",
    "Total duration of Booking→ERP/CRM/Loyalty chain in seconds.",
    ["clinic_bucket"],
)

business_chain_booking_erp_step_duration_seconds = Histogram(  # type: ignore[call-arg]
    "business_chain_booking_erp_step_duration_seconds",
    "Step duration in Booking→ERP/CRM/Loyalty chain in seconds.",
    ["clinic_bucket", "step"],
)

business_chain_omni_ai_total = Counter(  # type: ignore[call-arg]
    "business_chain_omni_ai_total",
    "Total runs of Omnichannel+AI chain by account bucket and status.",
    ["account_bucket", "status"],
)

business_chain_omni_ai_errors_total = Counter(  # type: ignore[call-arg]
    "business_chain_omni_ai_errors_total",
    "Errors in Omnichannel+AI chain by account bucket and error type.",
    ["account_bucket", "error_type"],
)

business_chain_omni_ai_duration_seconds = Histogram(  # type: ignore[call-arg]
    "business_chain_omni_ai_duration_seconds",
    "Total duration of Omnichannel+AI chain in seconds.",
    ["account_bucket"],
)

business_chain_omni_ai_step_duration_seconds = Histogram(  # type: ignore[call-arg]
    "business_chain_omni_ai_step_duration_seconds",
    "Step duration in Omnichannel+AI chain in seconds.",
    ["account_bucket", "step"],
)

# ------------------------------------------------------------------------------
# CRM + Attribution and Tasks & Attention business chains (OBS_CHAINS_023)
# ------------------------------------------------------------------------------

business_chain_crm_attribution_total = Counter(  # type: ignore[call-arg]
    "business_chain_crm_attribution_total",
    "Total runs of CRM+Attribution reporting chain by clinic bucket and status.",
    ["clinic_bucket", "status"],
)

business_chain_crm_attribution_errors_total = Counter(  # type: ignore[call-arg]
    "business_chain_crm_attribution_errors_total",
    "Errors in CRM+Attribution reporting chain by clinic bucket and error type.",
    ["clinic_bucket", "error_type"],
)

business_chain_crm_attribution_duration_seconds = Histogram(  # type: ignore[call-arg]
    "business_chain_crm_attribution_duration_seconds",
    "Total duration of CRM+Attribution reporting chain in seconds.",
    ["clinic_bucket"],
)

business_chain_tasks_attention_total = Counter(  # type: ignore[call-arg]
    "business_chain_tasks_attention_total",
    "Total runs of Tasks&Attention chain by clinic bucket and status.",
    ["clinic_bucket", "status"],
)

business_chain_tasks_attention_errors_total = Counter(  # type: ignore[call-arg]
    "business_chain_tasks_attention_errors_total",
    "Errors in Tasks&Attention chain by clinic bucket and error type.",
    ["clinic_bucket", "error_type"],
)

business_chain_tasks_attention_duration_seconds = Histogram(  # type: ignore[call-arg]
    "business_chain_tasks_attention_duration_seconds",
    "Total duration of Tasks&Attention chain in seconds.",
    ["clinic_bucket"],
)


# ------------------------------------------------------------------------------
# AI tools registry metrics
# ------------------------------------------------------------------------------

ai_tool_calls_total = Counter(  # type: ignore[call-arg]
    "ai_tool_calls_total",
    "Total AI tool calls by tool, source and status.",
    ["tool_id", "source", "status"],
)

ai_tool_call_duration_seconds = Histogram(  # type: ignore[call-arg]
    "ai_tool_call_duration_seconds",
    "Duration of AI tool calls in seconds.",
    ["tool_id", "source"],
)

# ------------------------------------------------------------------------------
# CRM AI recommendation metrics (CRM_AI_009)
# ------------------------------------------------------------------------------

crm_ai_recommendations_total = Counter(  # type: ignore[call-arg]
    "crm_ai_recommendations_total",
    "CRM AI recommendation lifecycle events (generated/accepted/ignored/errors).",
    ["clinic_bucket", "kind", "outcome"],
)

crm_leads_list_requests_total = Counter(  # type: ignore[call-arg]
    "crm_leads_list_requests_total",
    "CRM GET /leads requests by projection (full vs kanban).",
    ["projection"],
)

# HTTP layer (PERF observability): route template when available; status_class for latency SLO slices.
http_request_duration_seconds = Histogram(  # type: ignore[call-arg]
    "http_request_duration_seconds",
    "HTTP request duration in seconds (path template or normalized path; excludes /metrics /health).",
    ["method", "path", "status_class"],
)


# ------------------------------------------------------------------------------
# Tasks & Attention per-task metrics
# ------------------------------------------------------------------------------

tasks_created_total = Counter(  # type: ignore[call-arg]
    "tasks_created_total",
    "Total tasks created by clinic bucket, source and attention kind.",
    ["clinic_bucket", "source", "attention_kind"],
)

task_time_to_close_seconds = Histogram(  # type: ignore[call-arg]
    "task_time_to_close_seconds",
    "Time from task creation to closing (status=done) in seconds.",
    ["clinic_bucket", "source", "attention_kind"],
)

task_status_transitions_total = Counter(  # type: ignore[call-arg]
    "task_status_transitions_total",
    "Task status transitions by clinic bucket and from/to statuses.",
    ["clinic_bucket", "from_status", "to_status"],
)

task_blocked_events_total = Counter(  # type: ignore[call-arg]
    "task_blocked_events_total",
    "Task blocked/unblocked events by clinic bucket and action.",
    ["clinic_bucket", "action"],
)

task_sla_overdue_total = Counter(  # type: ignore[call-arg]
    "task_sla_overdue_total",
    "Tasks completed after due_at (SLA overdue) by clinic bucket and source.",
    ["clinic_bucket", "source"],
)

task_bulk_status_total = Counter(  # type: ignore[call-arg]
    "task_bulk_status_total",
    "Bulk status update outcomes by clinic bucket, target status and outcome.",
    ["clinic_bucket", "to_status", "outcome"],
)

# ------------------------------------------------------------------------------
# CRM funnel / lifecycle metrics (CRM_EVENTS_007)
# ------------------------------------------------------------------------------

crm_leads_created_total = Counter(  # type: ignore[call-arg]
    "crm_leads_created_total",
    "Total CRM leads created by clinic and source/campaign.",
    ["clinic_id", "source", "utm_campaign"],
)

crm_lead_stage_transitions_total = Counter(  # type: ignore[call-arg]
    "crm_lead_stage_transitions_total",
    "Total CRM lead stage transitions by clinic and semantics (low-cardinality).",
    ["clinic_id", "from_semantic", "to_semantic", "initiator"],
)

crm_lead_time_to_close_seconds = Histogram(  # type: ignore[call-arg]
    "crm_lead_time_to_close_seconds",
    "Time from lead creation to terminal status (success/lost).",
    ["clinic_id", "outcome"],
)

crm_lead_lifecycle_transitions_total = Counter(  # type: ignore[call-arg]
    "crm_lead_lifecycle_transitions_total",
    "Event-driven CRM stage transitions from LeadLifecycleService by clinic, event and outcome.",
    ["clinic_id", "event_type", "outcome"],
)

crm_lead_stale_handled_total = Counter(  # type: ignore[call-arg]
    "crm_lead_stale_handled_total",
    "Stale-lead lifecycle handling: stage move applied vs skipped.",
    ["clinic_id", "outcome"],
)

crm_lead_visit_completion_outcomes_total = Counter(  # type: ignore[call-arg]
    "crm_lead_visit_completion_outcomes_total",
    "Visit-completed CRM lifecycle: close vs skip (no won stage / transition failed).",
    ["clinic_id", "outcome"],
)

crm_lead_booking_onboarded_total = Counter(  # type: ignore[call-arg]
    "crm_lead_booking_onboarded_total",
    "BookingCreated CRM: attached to existing open lead vs new lead created.",
    ["clinic_id", "outcome"],
)

crm_lead_actual_value_erp_updates_total = Counter(  # type: ignore[call-arg]
    "crm_lead_actual_value_erp_updates_total",
    "CRM lead actual_value refresh from ERP financial_transactions by clinic, trigger and whether value changed.",
    ["clinic_id", "source", "changed"],
)

crm_lead_actual_value_erp_missing_fact_total = Counter(  # type: ignore[call-arg]
    "crm_lead_actual_value_erp_missing_fact_total",
    "CRM lead refresh from ERP yielded zero income while a completed booking was in scope (consistency signal).",
    ["clinic_id", "source"],
)

# ------------------------------------------------------------------------------
# AI Task Manager metrics (TASKS_AI_021)
# ------------------------------------------------------------------------------

ai_task_manager_proposed_total = Counter(  # type: ignore[call-arg]
    "ai_task_manager_proposed_total",
    "Total proposed tasks by AI Task Manager per clinic and task class.",
    ["clinic_id", "task_class"],
)

ai_task_manager_created_total = Counter(  # type: ignore[call-arg]
    "ai_task_manager_created_total",
    "Total tasks created by AI Task Manager per clinic, source and task class.",
    ["clinic_id", "source", "task_class"],
)

ai_task_manager_skipped_total = Counter(  # type: ignore[call-arg]
    "ai_task_manager_skipped_total",
    "Total skipped proposed tasks by AI Task Manager per clinic and reason.",
    ["clinic_id", "reason"],
)

ai_task_manager_errors_total = Counter(  # type: ignore[call-arg]
    "ai_task_manager_errors_total",
    "Errors in AI Task Manager per clinic and error type.",
    ["clinic_id", "error_type"],
)

ai_task_manager_duration_seconds = Histogram(  # type: ignore[call-arg]
    "ai_task_manager_duration_seconds",
    "Duration of AI Task Manager run per clinic.",
    ["clinic_id"],
)

# ------------------------------------------------------------------------------
# Waitlist (BKG_WAITLIST_004)
# ------------------------------------------------------------------------------

waitlist_entries_total = Counter(  # type: ignore[call-arg]
    "waitlist_entries_total",
    "WaitlistService mutations by clinic and operation.",
    ["clinic_id", "op"],
)

waitlist_status_transitions_total = Counter(  # type: ignore[call-arg]
    "waitlist_status_transitions_total",
    "Waitlist status transitions by clinic and from/to status.",
    ["clinic_id", "from_status", "to_status"],
)

waitlist_slot_notify_total = Counter(  # type: ignore[call-arg]
    "waitlist_slot_notify_total",
    "Slot-freed waitlist handling: notified candidates vs no match.",
    ["clinic_id", "outcome"],
)

waitlist_booking_conversion_total = Counter(  # type: ignore[call-arg]
    "waitlist_booking_conversion_total",
    "Waitlist to booking conversion attempts by clinic and outcome.",
    ["clinic_id", "outcome"],
)


# ------------------------------------------------------------------------------
# Paperless / digital forms (PPR-2)
# ------------------------------------------------------------------------------

paperless_form_operations_total = Counter(  # type: ignore[call-arg]
    "paperless_form_operations_total",
    "Paperless operations (issue, sign, revoke, cancel, expire) by clinic and action.",
    ["clinic_id", "action"],
)

paperless_form_status_transitions_total = Counter(  # type: ignore[call-arg]
    "paperless_form_status_transitions_total",
    "Form instance status transitions by clinic and from/to status.",
    ["clinic_id", "from_status", "to_status"],
)

paperless_form_issue_to_sign_seconds = Histogram(  # type: ignore[call-arg]
    "paperless_form_issue_to_sign_seconds",
    "Time from instance created_at to signed_at when completing an issued/in_progress form.",
    ["clinic_id"],
)


# ------------------------------------------------------------------------------
# ERP report pre-aggregates (Engine L2)
# ------------------------------------------------------------------------------

erp_aggregate_refresh_seconds = Histogram(  # type: ignore[call-arg]
    "erp_aggregate_refresh_seconds",
    "Duration of ERP aggregate refresh job.",
    ["job_type"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

erp_aggregate_lag_seconds = Histogram(  # type: ignore[call-arg]
    "erp_aggregate_lag_seconds",
    "Seconds between aggregate max(updated_at) and request time (observed on read path).",
    ["aggregate_kind"],
    buckets=(60, 300, 900, 3600, 7200, 86400, 172800, 604800),
)

erp_aggregate_rows_processed = Counter(  # type: ignore[call-arg]
    "erp_aggregate_rows_processed",
    "Rows written during ERP aggregate refresh.",
    ["job_type"],
)

erp_aggregate_read_fallback_total = Counter(  # type: ignore[call-arg]
    "erp_aggregate_read_fallback_total",
    "ERP report API fell back to raw scan instead of vitrine.",
    ["report_type", "reason"],
)

erp_aggregate_nightly_kind_failures_total = Counter(  # type: ignore[call-arg]
    "erp_aggregate_nightly_kind_failures_total",
    "Nightly Celery ERP vitrine refresh failed for an aggregate kind (one tx per clinic; all kinds rolled back).",
    ["aggregate_kind"],
)

erp_aggregate_empty_trusted_total = Counter(  # type: ignore[call-arg]
    "erp_aggregate_empty_trusted_total",
    "ERP report read used empty vitrine rows trusted by coverage watermark (no raw fallback).",
    ["aggregate_kind"],
)

erp_aggregate_parity_sample_total = Counter(  # type: ignore[call-arg]
    "erp_aggregate_parity_sample_total",
    "Daily sample: visit_revenue sum(raw) vs sum(vitrine) for one clinic (see erp_parity_sample_service).",
    ["result"],
)

# ------------------------------------------------------------------------------
# Wave 5: dashboard Redis cache + replica probe
# ------------------------------------------------------------------------------

erp_dashboard_cache_requests_total = Counter(  # type: ignore[call-arg]
    "erp_dashboard_cache_requests_total",
    "Redis read-through for admin dashboard JSON: hit, miss, or redis_error.",
    ["result"],
)

erp_dashboard_cache_invalidations_total = Counter(  # type: ignore[call-arg]
    "erp_dashboard_cache_invalidations_total",
    "Clinic-scoped dashboard cache invalidations after ERP vitrine refresh.",
)

db_replica_lag_observed_seconds = Gauge(  # type: ignore[call-arg]
    "db_replica_lag_observed_seconds",
    "Last replication lag (s) on reporting DSN from GET /health/replica; NaN if not standby.",
)


def render_prometheus_metrics() -> tuple[bytes, str]:
    """Return serialized metrics payload and content type.

    If Prometheus client is not available or metrics are disabled via settings,
    returns an empty payload with text/plain content type.
    """
    if not _PROMETHEUS_AVAILABLE or getattr(settings, "metrics_enabled", True) is False:
        # Minimal safe response so that /metrics endpoint is always callable.
        return b"", "text/plain; charset=utf-8"

    data = generate_latest()
    return data, CONTENT_TYPE_LATEST

