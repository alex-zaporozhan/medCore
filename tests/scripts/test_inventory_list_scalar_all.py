"""Smoke: inventory script runs (QA_ARCH QA-AUDIT-006 automation)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_inventory_list_scalar_all_runs() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "inventory_list_scalar_all.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "src/api/v1/routers/" in proc.stdout or "api/v1/routers" in proc.stdout
