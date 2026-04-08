"""
Numeric anchors for enterprise SaaS scale (Phase 0 / 0-F1).

Authoritative prose and load-scenario checklist live in:
docs/architecture/ENTERPRISE_SAAS_SCALE_ENVELOPE.md and
docs/operations/LOAD_SCENARIO_MARKETING_10K.md.

Use these constants in code only where a single shared cap is required; marketing
claims remain gated by LEAD sign-off (PRC-G1).
"""

# --- §1 table (orientation; LEAD approves public claims) ---
MAX_ACTIVE_ORGANIZATIONS_MARKETING: int = 10_000
MAX_SITES_PER_ORGANIZATION: int = 10
MAX_STAFF_PER_SITE_OR_ORG: int = 40

# --- API / UX defaults aligned with "no full table scans" rule ---
DEFAULT_ADMIN_LIST_PAGE_SIZE: int = 50
DEFAULT_ADMIN_LIST_PAGE_SIZE_CAP: int = 200
