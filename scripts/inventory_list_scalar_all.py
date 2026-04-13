#!/usr/bin/env python3
"""
Inventory `result.scalars().all()` (and variants) under API routers (QA_ARCH QA-AUDIT-006).

Heuristic only: each hit is a candidate for pagination review — not all are unbounded
(e.g. small reference data, already-limited queries above in the same function).

Usage:
  poetry run python scripts/inventory_list_scalar_all.py
  poetry run python scripts/inventory_list_scalar_all.py --markdown
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_ROUTERS = _ROOT / "src" / "api" / "v1" / "routers"

_PATTERN = re.compile(
    r"\.scalars\(\)\.all\(\)|scalars\(\)\.all\(\)",
)


def _scan_file(path: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"{path}: read error: {exc}", file=sys.stderr)
        return hits
    for i, line in enumerate(text.splitlines(), start=1):
        if _PATTERN.search(line):
            hits.append((i, line.strip()))
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description="List scalars().all() usages in v1 routers.")
    parser.add_argument(
        "--markdown",
        action="store_true",
        help="Print a markdown table (for pasting into QA inventories).",
    )
    args = parser.parse_args()

    if not _ROUTERS.is_dir():
        print(f"Routers dir not found: {_ROUTERS}", file=sys.stderr)
        return 2

    rows: list[tuple[str, int, str]] = []
    for py in sorted(_ROUTERS.glob("*.py")):
        for lineno, line in _scan_file(py):
            rel = py.relative_to(_ROOT)
            rows.append((str(rel).replace("\\", "/"), lineno, line))

    if args.markdown:
        print("| Файл | Строка | Фрагмент |")
        print("|------|--------|----------|")
        for path, lineno, line in rows:
            esc = line.replace("|", "\\|")
            if len(esc) > 120:
                esc = esc[:117] + "..."
            print(f"| `{path}` | {lineno} | `{esc}` |")
    else:
        for path, lineno, line in rows:
            print(f"{path}:{lineno}: {line}")

    print(f"\n# total hits: {len(rows)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
