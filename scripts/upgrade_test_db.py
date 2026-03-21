"""Apply Alembic migrations to the database from DATABASE_URL_TEST (or DATABASE_URL).

Usage (from repo root):
  python scripts/upgrade_test_db.py

Ensures pytest and local dev use the same schema as production (e.g. Paperless h4i5j6k7l8m9).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and os.environ.get(k) is None:
                os.environ[k] = v


def main() -> None:
    _load_dotenv()
    if os.environ.get("DATABASE_URL_TEST"):
        os.environ["DATABASE_URL"] = os.environ["DATABASE_URL_TEST"]
    subprocess.check_call(["alembic", "upgrade", "head"])


if __name__ == "__main__":
    main()
