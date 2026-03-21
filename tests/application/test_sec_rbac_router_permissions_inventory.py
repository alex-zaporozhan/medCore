"""SR3: committed permission inventory matches require_permissions() in routers."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_sec_rbac_router_permissions_inventory_matches_codebase() -> None:
    script = ROOT / "scripts" / "audit_rbac_endpoints.py"
    r = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
