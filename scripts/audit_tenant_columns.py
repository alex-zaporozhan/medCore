#!/usr/bin/env python3
"""ORM-аудит изоляции tenant: колонка clinic_id или business_account_id (омниканал), иначе allowlist.

Ожидаемые колонки области tenant: clinic_id или business_account_id (или allowlist в скрипте).
"""

from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path

# Корень репозитория
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

TENANT_SCOPE_COLUMNS = frozenset({"clinic_id", "business_account_id"})


def _load_all_entity_modules() -> None:
    import src.domain.entities as entities_pkg

    for _finder, name, _ispkg in pkgutil.walk_packages(
        entities_pkg.__path__,
        entities_pkg.__name__ + ".",
    ):
        importlib.import_module(name)


def _read_allowlist() -> set[str]:
    path = Path(__file__).with_name("tenant_allowlist.txt")
    out: set[str] = set()
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line.lower())
    return out


def _has_tenant_scope(table) -> bool:
    cols = set(table.columns.keys())
    return bool(TENANT_SCOPE_COLUMNS & cols)


def main() -> int:
    _load_all_entity_modules()
    from src.infrastructure.database.base import Base

    allow = _read_allowlist()
    missing: list[str] = []
    for table in Base.metadata.tables.values():
        tname = table.name
        if tname.lower() in allow:
            continue
        if _has_tenant_scope(table):
            continue
        missing.append(tname)

    if missing:
        print("Tables without clinic_id/business_account_id (not in tenant_allowlist.txt):")
        for m in sorted(missing):
            print(f"  - {m}")
        return 1
    print("OK: tenant scope column present or table allowlisted.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
