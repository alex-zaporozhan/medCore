#!/usr/bin/env python3
"""
Сводка устаревших зависимостей продукта (Python + frontend) и опционально pip-audit.

Запуск из корня репозитория:
  poetry run python scripts/dev/check_dependency_updates.py
  poetry run python scripts/dev/check_dependency_updates.py --audit

В CI не заменяет poetry/npm; только печатает, что можно обновить вручную после ревью.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path | None = None) -> tuple[int, str]:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out


def main() -> int:
    parser = argparse.ArgumentParser(description="Report outdated deps (Poetry + npm) and optional pip-audit.")
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Run pip-audit against the Poetry venv (fails if known vulns).",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    code = 0

    print("=== Poetry (backend) — outdated ===")
    rc, out = _run(["poetry", "show", "--outdated"], cwd=root)
    print(out.strip() or "(none or poetry error)")
    if rc != 0:
        code = 1

    fe = root / "frontend"
    if (fe / "package.json").is_file():
        print("\n=== npm (frontend) — outdated ===")
        if shutil.which("npm") is None:
            print("(npm not in PATH — skipped. Install Node.js or run from CI.)")
        else:
            try:
                npm = _run(["npm", "outdated"], cwd=fe)
            except (FileNotFoundError, OSError):
                # Windows: npm.cmd/shim may confuse which(); avoid non-ASCII in message for cp1252 consoles.
                print("(npm unavailable: executable not found or not runnable)")
            else:
                # npm outdated exits 1 when updates exist (expected)
                npm_out = npm[1].strip()
                if npm_out:
                    print(npm_out)
                elif npm[0] != 0:
                    print(f"(npm exited with code {npm[0]}; often 1 = updates available)")
                else:
                    print("(npm: up to date)")

    if args.audit:
        print("\n=== pip-audit (Poetry env) ===")
        _run(["poetry", "run", "pip", "install", "-q", "pip-audit"], cwd=root)
        ar, ao = _run(["poetry", "run", "pip-audit"], cwd=root)
        print(ao.strip())
        if ar != 0:
            code = ar

    return code


if __name__ == "__main__":
    sys.exit(main())
