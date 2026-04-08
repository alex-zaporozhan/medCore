#!/usr/bin/env python3
"""
Regenerate docs/product_state/generated/router_surface/ from src/api/v1/router.py and routers.

Usage (repo root):
  python scripts/generate_router_surface_docs.py

After router.py or any router file changes, re-run and commit outputs under docs/product_state/generated/.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER_PY = ROOT / "src/api/v1/router.py"
ROUTERS_DIR = ROOT / "src/api/v1/routers"
TESTS_DIR = ROOT / "tests"
OUT_DIR = ROOT / "docs" / "product_state" / "generated" / "router_surface"

INCLUDE_RE = re.compile(r"api_router\.include_router\((\w+)\.router\)")
PREFIX_RE = re.compile(
    r"router\s*=\s*APIRouter\s*\(\s*(?:[^)]*?prefix\s*=\s*[\"']([^\"']+)[\"'])?",
    re.DOTALL,
)
# Simpler: prefix= on one line or multiline
PREFIX_LINE_RE = re.compile(r"prefix\s*=\s*[\"']([^\"']+)[\"']")
METHOD_RE = re.compile(
    r"@router\.(get|post|put|patch|delete)\s*\(\s*[\"']([^\"']*)[\"']",
    re.MULTILINE,
)
METHOD_RE_MULTILINE = re.compile(
    r"@router\.(get|post|put|patch|delete)\s*\(\s*\n\s*[\"']([^\"']*)[\"']",
    re.MULTILINE,
)
METRICS_IMPORT_RE = re.compile(
    r"from\s+src\.core\.metrics\s+import\s+([^\n]+)",
    re.MULTILINE,
)


def parse_include_order() -> list[str]:
    text = ROUTER_PY.read_text(encoding="utf-8")
    return INCLUDE_RE.findall(text)


def extract_prefix(content: str) -> str:
    m = PREFIX_LINE_RE.search(content)
    return m.group(1) if m else "(see decorators — no APIRouter prefix)"


def extract_routes(content: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for m in METHOD_RE.finditer(content):
        found.append((m.group(1).upper(), m.group(2)))
    for m in METHOD_RE_MULTILINE.finditer(content):
        t = (m.group(1).upper(), m.group(2))
        if t not in found:
            found.append(t)
    return found


def extract_metrics_imports(content: str) -> list[str]:
    out: list[str] = []
    for m in METRICS_IMPORT_RE.finditer(content):
        names = m.group(1).strip().rstrip(",")
        for part in names.split(","):
            part = part.strip().split(" as ")[0].strip()
            if part:
                out.append(part)
    return sorted(set(out))


def _stem_matches_module(stem: str, module: str) -> bool:
    """True if pytest file stem clearly targets this router module."""
    if stem == f"test_{module}":
        return True
    if stem.startswith(f"test_{module}_"):
        return True
    if stem.endswith(f"_{module}"):
        return True
    if f"_{module}_" in stem:
        return True
    return False


def find_test_files(module: str) -> list[str]:
    """Paths under tests/: filename stem hints + explicit v1 router import of this module."""
    hits: set[str] = set()
    if not TESTS_DIR.is_dir():
        return []
    import_re = re.compile(
        rf"from\s+src\.api\.v1\.routers(?:\.\w+)?\s+import\s+[^\n#]*\b{re.escape(module)}\b"
    )
    alt_import = re.compile(
        rf"from\s+src\.api\.v1\.routers\.{re.escape(module)}\s+import"
    )
    for p in TESTS_DIR.rglob("*.py"):
        stem = p.stem
        if not stem.startswith("test_"):
            continue
        try:
            t = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if _stem_matches_module(stem, module) or import_re.search(t) or alt_import.search(t):
            hits.add(p.relative_to(ROOT).as_posix())
    return sorted(hits)


def frontend_grep_hint(module: str, prefix: str) -> str:
    """Single line hint for manual / rg search."""
    if prefix.startswith("/admin"):
        return f"rg {prefix.replace('/admin/', '')} frontend/src --glob '*.ts*'"
    return f"rg '{module}' frontend/src --glob '*.ts*'"


def render_module_md(order: int, module: str) -> str:
    path = ROUTERS_DIR / f"{module}.py"
    if not path.exists():
        return f"\n## {order}. `{module}`\n\n**MISSING FILE** `{path.relative_to(ROOT)}`\n"
    content = path.read_text(encoding="utf-8")
    prefix = extract_prefix(content)
    routes = extract_routes(content)
    metrics = extract_metrics_imports(content)
    tests = find_test_files(module)
    lines = [
        f"\n## {order}. `{module}`\n",
        f"- **Backend:** `{path.relative_to(ROOT).as_posix()}`\n",
        f"- **APIRouter prefix:** `{prefix}`\n",
        f"- **Frontend search hint:** `{frontend_grep_hint(module, prefix)}`\n",
    ]
    if metrics:
        lines.append("- **Prometheus / `src.core.metrics` symbols used in this file:**\n")
        for m in metrics:
            lines.append(f"  - `{m}`\n")
    else:
        lines.append(
            "- **Metrics:** *(no direct `src.core.metrics` import in this router file; "
            "HTTP still counted by global middleware if enabled)*\n"
        )
    lines.append("\n### HTTP routes (decorator paths only)\n\n")
    lines.append("| Method | Path |\n|--------|------|\n")
    if routes:
        for method, rpath in routes:
            display = "`(root)`" if rpath == "" else f"`{rpath}`"
            lines.append(f"| {method} | {display} |\n")
    else:
        lines.append("| — | *(none matched by static parse — check file)* |\n")
    lines.append("\n### Tests (files under `tests/` mentioning this module)\n\n")
    if tests:
        for t in tests[:40]:
            lines.append(f"- `{t}`\n")
        if len(tests) > 40:
            lines.append(f"- … and {len(tests) - 40} more (narrow search manually)\n")
    else:
        lines.append("- *(no pytest file matched — add coverage or document gap)*\n")
    lines.append("\n---\n")
    return "".join(lines)


def main() -> int:
    modules = parse_include_order()
    if not modules:
        print("No include_router entries found", file=sys.stderr)
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    header = (
        "# Поверхность API v1 по каждому роутеру (автогенерация)\n\n"
        "> **Источник:** `scripts/generate_router_surface_docs.py` · порядок = `include_router` в "
        "`src/api/v1/router.py`.\n"
        "> **Полный URL:** значение `api_v1_prefix` из `src/core/config.py` + prefix роутера + path.\n\n"
        "Чек-лист для разработки: бэкенд-файл, префикс, маршруты (статический разбор), "
        "тесты (эвристика по вхождению имени модуля), метрики (импорты из `src.core.metrics`).\n\n"
        "После изменений роутеров: `python scripts/generate_router_surface_docs.py` и закоммитить diff.\n\n"
        "## Ограничения автогенерации\n\n"
        "- Пути в декораторах на нескольких строках без кавычек сразу после `(` могут не попасть в таблицу.\n"
        "- Список тестов неполный, если модуль не упоминается в тексте файла теста.\n"
        "- Связка с экранами SPA — сверять с `frontend/src/App.tsx` и `frontend/src/routePaths.ts`.\n\n"
    )
    parts = [header, "# Роутеры по порядку подключения\n"]
    for i, mod in enumerate(modules, start=1):
        parts.append(render_module_md(i, mod))
    index_path = OUT_DIR / "INDEX.md"
    index_path.write_text("".join(parts), encoding="utf-8")
    print(f"Wrote {index_path} ({len(modules)} modules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
