#!/usr/bin/env python3
"""
DoD Phase 1c: optional SaaS modules must declare require_entitlement on APIRouter.

Run from repo root: python scripts/check_admin_entitlement_routers.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ROUTERS_DIR = ROOT / "src" / "api" / "v1" / "routers"

EXPECTED: dict[str, str] = {
    "admin_tasks.py": "tasks.kanban",
    "admin_task_boards.py": "tasks.kanban",
    "admin_task_streams.py": "tasks.kanban",
    "admin_task_tags.py": "tasks.kanban",
    "admin_marketing.py": "marketing.attribution",
    "admin_marketing_attribution.py": "marketing.attribution",
    "admin_crm.py": "crm.pipeline",
    "admin_retention.py": "retention.bundle",
    "admin_recall.py": "marketing.attribution",
    "admin_embed.py": "omni.embed.bundle",
    "admin_rag_kb.py": "ai.rag.org_kb",
    "admin_crm_import.py": "import.crm_v1",
    "admin_commerce.py": "commerce.store_network",
    "admin_commerce_network.py": "commerce.store_network",
}


def main() -> int:
    failed = False
    for fname, key in EXPECTED.items():
        path = ROUTERS_DIR / fname
        if not path.is_file():
            print(f"FAIL: missing file {path.relative_to(ROOT)}")
            failed = True
            continue
        text = path.read_text(encoding="utf-8")
        if "require_entitlement" not in text and "get_crm_import_organization_id" not in text:
            print(
                f"FAIL: {fname} must use require_entitlement or get_crm_import_organization_id "
                "(effective-org SaaS gate)"
            )
            failed = True
            continue
        if key not in text:
            print(f"FAIL: {fname} must reference entitlement key {key!r}")
            failed = True
    if failed:
        return 1
    print("OK: admin entitlement routers wired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
