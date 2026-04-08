#!/usr/bin/env python3
"""SR3: inventory of permission codes in admin routers vs committed baseline (CI gate).

Usage:
  python scripts/audit_rbac_endpoints.py              # print report
  python scripts/audit_rbac_endpoints.py --check      # exit 1 if inventory file out of sync
  python scripts/audit_rbac_endpoints.py --write      # rewrite inventory from codebase

Inventory: docs/product_state/baselines/rbac_router_permissions.txt (one code per line, sorted).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTERS = ROOT / "src" / "api" / "v1" / "routers"
INVENTORY = ROOT / "docs" / "product_state" / "baselines" / "rbac_router_permissions.txt"

# Inner arguments of require_permissions("a", "b", ...)
_PERM_CALL = re.compile(r"require_permissions\s*\(\s*([^)]*)\s*\)")


def collect_permission_codes() -> set[str]:
    """All string permission codes passed to require_permissions in admin routers."""
    codes: set[str] = set()
    if not ROUTERS.is_dir():
        return codes
    for py in sorted(ROUTERS.glob("*.py")):
        text = py.read_text(encoding="utf-8")
        for m in _PERM_CALL.finditer(text):
            inner = m.group(1).strip()
            if not inner:
                continue
            for part in inner.split(","):
                part = part.strip()
                if not part:
                    continue
                if (part.startswith('"') and part.endswith('"')) or (
                    part.startswith("'") and part.endswith("'")
                ):
                    codes.add(part[1:-1])
    return codes


def read_inventory() -> set[str]:
    if not INVENTORY.is_file():
        return set()
    out: set[str] = set()
    for line in INVENTORY.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line)
    return out


def write_inventory(codes: set[str]) -> None:
    INVENTORY.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(sorted(codes)) + "\n"
    INVENTORY.write_text(body, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if inventory != codebase")
    parser.add_argument("--write", action="store_true", help="Overwrite inventory file")
    args = parser.parse_args()

    found = collect_permission_codes()
    if not found:
        print("No permission codes found (wrong path?)", file=sys.stderr)
        return 1

    if args.write:
        write_inventory(found)
        print(f"Wrote {len(found)} codes to {INVENTORY.relative_to(ROOT)}")
        return 0

    if args.check:
        expected = read_inventory()
        if found != expected:
            extra = sorted(found - expected)
            missing = sorted(expected - found)
            print("RBAC permission inventory mismatch.", file=sys.stderr)
            if extra:
                print(f"  In code but not in {INVENTORY.name}: {extra}", file=sys.stderr)
            if missing:
                print(f"  In inventory but not in code: {missing}", file=sys.stderr)
            print("  Run: python scripts/audit_rbac_endpoints.py --write", file=sys.stderr)
            return 1
        print(f"OK: {len(found)} permission codes match {INVENTORY.relative_to(ROOT)}")
        return 0

    # Default: human report
    for c in sorted(found):
        print(c)
    print(f"\nTotal unique codes: {len(found)}")
    print(f"Inventory file: {INVENTORY.relative_to(ROOT)}")
    print("CI: pytest tests/application/test_sec_rbac_router_permissions_inventory.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
