# PII and logging

Do not log personal data in plaintext telemetry. Use structured logs and masking where applicable (`LOG_MASK_PII` and related settings in `.env.example`).

**Patient PII anonymize (LEAD B2):** `POST /api/v1/patients/{id}/anonymize` writes `rbac_audit_log` with `action=patient_pii_anonymized`, `entity_type=patient`, `after_payload={"anonymized": true}` (no raw PII in payload). Application log line remains id-only.

Observability paths: [documentation/OBSERVABILITY.md](../../documentation/OBSERVABILITY.md).
