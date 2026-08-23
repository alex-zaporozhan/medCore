"""
LEAD A3: auto-start ``vite preview`` for Playwright when ``FRONTEND_E2E_URL`` is unset.

Used from ``pytest_collection_modifyitems`` when ``test_critical_path_smoke`` is selected.
Opt out: ``PYTEST_DISABLE_VITE_AUTOSTART=1`` (local only; CI should set ``FRONTEND_E2E_URL``).
"""

from __future__ import annotations

import asyncio
import atexit
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 4173
_DEFAULT_URL = f"http://{_DEFAULT_HOST}:{_DEFAULT_PORT}"

_proc: subprocess.Popen[bytes] | None = None
_started_by_us = False


def _npm_executable() -> str | None:
    if sys.platform == "win32":
        return shutil.which("npm.cmd") or shutil.which("npm")
    return shutil.which("npm")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _http_ok(url: str, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            return int(getattr(resp, "status", 200)) < 500
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0


def _apply_windows_proactor_for_playwright() -> None:
    if sys.platform != "win32":
        return
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except (AttributeError, OSError):
        pass


def stop_vite_preview_if_started() -> None:
    global _proc, _started_by_us
    if not _started_by_us or _proc is None:
        return
    proc = _proc
    _proc = None
    _started_by_us = False
    try:
        proc.terminate()
        proc.wait(timeout=12)
    except (subprocess.TimeoutExpired, OSError):
        try:
            proc.kill()
        except OSError:
            pass


def _fail_or_exit(msg: str, *, ci_strict: bool) -> None:
    import pytest

    if ci_strict:
        pytest.exit(msg, returncode=1)
    raise RuntimeError(msg)


def ensure_vite_preview_for_smoke(*, ci_strict: bool = False) -> None:
    """If ``FRONTEND_E2E_URL`` is empty, reuse or start preview on 127.0.0.1:4173."""
    global _proc, _started_by_us

    existing = (os.environ.get("FRONTEND_E2E_URL") or "").strip().rstrip("/")
    if existing:
        return

    if os.environ.get("PYTEST_DISABLE_VITE_AUTOSTART", "").strip().lower() in ("1", "true", "yes"):
        if ci_strict:
            _fail_or_exit(
                "CRITICAL_PATH_CI: FRONTEND_E2E_URL unset and PYTEST_DISABLE_VITE_AUTOSTART is enabled",
                ci_strict=ci_strict,
            )
        return

    base = f"{_DEFAULT_URL}/"
    if _http_ok(base):
        os.environ["FRONTEND_E2E_URL"] = _DEFAULT_URL
        _apply_windows_proactor_for_playwright()
        return

    if _port_in_use(_DEFAULT_HOST, _DEFAULT_PORT):
        for _ in range(40):
            if _http_ok(base):
                os.environ["FRONTEND_E2E_URL"] = _DEFAULT_URL
                _apply_windows_proactor_for_playwright()
                return
            time.sleep(0.25)
        _fail_or_exit(
            f"Port {_DEFAULT_PORT} is in use but did not respond with HTTP; "
            f"free the port or set FRONTEND_E2E_URL to your frontend base URL",
            ci_strict=ci_strict,
        )

    npm_bin = _npm_executable()
    if npm_bin is None:
        _fail_or_exit(
            "npm not found on PATH; install Node.js or set FRONTEND_E2E_URL to a running frontend",
            ci_strict=ci_strict,
        )

    frontend = repo_root() / "frontend"
    dist_index = frontend / "dist" / "index.html"
    emoji_sheet = (
        frontend
        / "node_modules"
        / "emoji-datasource-apple"
        / "img"
        / "apple"
        / "sheets-256"
        / "64.png"
    )
    if not dist_index.is_file() or not emoji_sheet.is_file():
        # prebuild copies emoji spritesheet from node_modules; CI jobs that only
        # `poetry install` must not run `npm run build` without `npm ci` first.
        if not emoji_sheet.is_file():
            try:
                subprocess.run(
                    [npm_bin, "ci"],
                    cwd=frontend,
                    check=True,
                    timeout=900,
                    env={**os.environ, "CI": os.environ.get("CI", "true")},
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
                _fail_or_exit(f"frontend npm ci failed: {e}", ci_strict=ci_strict)
        try:
            subprocess.run(
                [npm_bin, "run", "build"],
                cwd=frontend,
                check=True,
                timeout=900,
                env={**os.environ, "CI": os.environ.get("CI", "true")},
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            _fail_or_exit(f"frontend npm run build failed: {e}", ci_strict=ci_strict)

    cmd = [
        npm_bin,
        "run",
        "preview",
        "--",
        "--host",
        _DEFAULT_HOST,
        "--port",
        str(_DEFAULT_PORT),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=frontend,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )
    except OSError as e:
        _fail_or_exit(f"could not start vite preview: {e}", ci_strict=ci_strict)

    _proc = proc
    _started_by_us = True
    deadline = time.monotonic() + 90.0
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            err = b""
            if proc.stderr:
                err = proc.stderr.read()[:4000]
            code = proc.returncode
            stop_vite_preview_if_started()
            _fail_or_exit(
                f"vite preview exited early (code={code}): {err.decode(errors='replace')}",
                ci_strict=ci_strict,
            )
        if _http_ok(base):
            os.environ["FRONTEND_E2E_URL"] = _DEFAULT_URL
            _apply_windows_proactor_for_playwright()
            return
        time.sleep(0.35)

    stop_vite_preview_if_started()
    _fail_or_exit(
        "Timed out waiting for vite preview on "
        f"{_DEFAULT_URL} (try: cd frontend && npm run build && npm run preview -- --host 127.0.0.1 --port 4173)",
        ci_strict=ci_strict,
    )


atexit.register(stop_vite_preview_if_started)
