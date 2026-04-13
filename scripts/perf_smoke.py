#!/usr/bin/env python3
"""
Minimal HTTP smoke for API availability (QA_ARCH QA-AUDIT-003 — стартовый артефакт perf).

Usage:
  PERF_SMOKE_BASE_URL=http://127.0.0.1:8000 poetry run python scripts/perf_smoke.py

Optional:
  PERF_SMOKE_PATHS=/health,/api/v1/public/clinics  (comma-separated, GET each)
  PERF_SMOKE_TIMEOUT_SECONDS=30  (per-request timeout)
"""

from __future__ import annotations

import os
import sys
import time


def main() -> int:
    try:
        import httpx
    except ImportError:
        print("httpx required (project dependency)", file=sys.stderr)
        return 2

    base = os.environ.get("PERF_SMOKE_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    raw_paths = os.environ.get("PERF_SMOKE_PATHS", "/health").strip()
    paths = [p.strip() for p in raw_paths.split(",") if p.strip()]
    timeout_s = float(os.environ.get("PERF_SMOKE_TIMEOUT_SECONDS", "30"))

    failures: list[str] = []
    durations_ms: list[float] = []
    with httpx.Client(timeout=timeout_s) as client:
        for path in paths:
            url = f"{base}{path}" if path.startswith("/") else f"{base}/{path}"
            try:
                t0 = time.perf_counter()
                r = client.get(url)
                durations_ms.append((time.perf_counter() - t0) * 1000.0)
                if r.status_code >= 400:
                    failures.append(f"{url} -> {r.status_code}")
            except Exception as exc:
                failures.append(f"{url} -> {exc!s}")

    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        return 1
    if durations_ms:
        slowest = max(durations_ms)
        print(
            f"ok {len(paths)} GET(s) against {base} "
            f"(max {slowest:.1f} ms, timeout {timeout_s}s)"
        )
    else:
        print(f"ok {len(paths)} GET(s) against {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
