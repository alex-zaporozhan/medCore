#!/usr/bin/env python3
"""
Phase 0 governance preflight (STREAM_PHASE0_AND_GOVERNANCE.md) — DEV automation.

QA_ARCH приёмка (Phase 0): docs/artifacts/IMPLEMENTATION_REPORT_1A_E2_PLATFORM_FOUNDER_2026-04-06.md приложение B;
  LEAD: docs/artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md; STREAM: docs/architecture/arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md

- 0-F1: import enterprise scale envelope constants (same numbers as ENTERPRISE_SAAS_SCALE_ENVELOPE.md §1).
- 0-F2: run a fixed pytest bundle for LEAD/QA_ARCH crash-review evidence (TARGET + rubric smoke).
- 0-F3: verify key architecture doc paths exist (sample trace MP → arch_plan → operations).

Usage:
  python scripts/phase0_governance_preflight.py envelope
  python scripts/phase0_governance_preflight.py crash-review
  python scripts/phase0_governance_preflight.py doc-paths
  python scripts/phase0_governance_preflight.py all
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

CRASH_REVIEW_TESTS = (
    "tests/api/test_platform_billing.py",
    "tests/api/test_payments.py",
    "tests/application/test_domain_outbox_payment.py",
    "tests/application/test_domain_outbox_platform_provision.py",
    "tests/core/test_api_error_codes.py",
    "tests/core/test_http_exception_envelope.py",
    "tests/core/test_payment_webhook_governance.py",
    "tests/core/test_enterprise_scale_envelope.py",
)

PHASE0_DOC_PATHS = (
    "docs/architecture/ENTERPRISE_SAAS_SCALE_ENVELOPE.md",
    "docs/architecture/ENTERPRISE_SAAS_TARGET.md",
    "docs/architecture/arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md",
    "docs/architecture/arch_plan/STREAM_PRODUCTION_READINESS.md",
    "docs/architecture/INDEX.md",
    "docs/architecture/SAAS_STRENGTHENING_MASTER_PLAN.md",
    "docs/architecture/ENTERPRISE_SAAS_RUBRIC.md",
    "docs/operations/DR_RUNBOOK.md",
    "docs/operations/LOAD_SCENARIO_MARKETING_10K.md",
)


def cmd_envelope() -> int:
    from src.core import enterprise_scale_envelope as env

    print("0-F1 envelope constants (code mirror of ENTERPRISE_SAAS_SCALE_ENVELOPE.md section 1):")
    print(f"  MAX_ACTIVE_ORGANIZATIONS_MARKETING = {env.MAX_ACTIVE_ORGANIZATIONS_MARKETING}")
    print(f"  MAX_SITES_PER_ORGANIZATION = {env.MAX_SITES_PER_ORGANIZATION}")
    print(f"  MAX_STAFF_PER_SITE_OR_ORG = {env.MAX_STAFF_PER_SITE_OR_ORG}")
    print(f"  DEFAULT_ADMIN_LIST_PAGE_SIZE_CAP = {env.DEFAULT_ADMIN_LIST_PAGE_SIZE_CAP}")
    return 0


def cmd_crash_review() -> int:
    tests = [str(REPO_ROOT / p) for p in CRASH_REVIEW_TESTS]
    missing = [p for p in tests if not Path(p).is_file()]
    if missing:
        print("Missing test files:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1
    r = subprocess.run(
        [sys.executable, "-m", "pytest", *tests, "-q", "--tb=short"],
        cwd=str(REPO_ROOT),
    )
    return int(r.returncode)


def cmd_doc_paths() -> int:
    missing = []
    for rel in PHASE0_DOC_PATHS:
        p = REPO_ROOT / rel
        if not p.is_file():
            missing.append(rel)
    if missing:
        print("0-F3: missing paths:", file=sys.stderr)
        for m in missing:
            print(f"  {m}", file=sys.stderr)
        return 1
    print("0-F3: OK —", len(PHASE0_DOC_PATHS), "paths present")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0 governance preflight")
    parser.add_argument(
        "command",
        choices=("envelope", "crash-review", "doc-paths", "all"),
        nargs="?",
        default="all",
    )
    args = parser.parse_args()
    if args.command == "envelope":
        return cmd_envelope()
    if args.command == "crash-review":
        return cmd_crash_review()
    if args.command == "doc-paths":
        return cmd_doc_paths()
    # all
    rc = cmd_envelope()
    if rc != 0:
        return rc
    rc = cmd_doc_paths()
    if rc != 0:
        return rc
    return cmd_crash_review()


if __name__ == "__main__":
    sys.path.insert(0, str(REPO_ROOT))
    raise SystemExit(main())
