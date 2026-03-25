"""Product edition (Box vs Enterprise) — сервер как источник правды для гейтов API.

См. `MASTER_PRODUCT_ROADMAP_2026`, фронт: `VITE_EDITION`; бэкенд: переменная окружения `EDITION`.
Значения коробки: `box`, `basic` (как на фронте). По умолчанию — Enterprise-режим API.
"""

from __future__ import annotations

import os


def is_box_edition() -> bool:
    """True если развёртывание в редакции коробки (без Enterprise-only модулей на API)."""
    edition = (os.getenv("EDITION") or "enterprise").lower().strip()
    return edition in ("box", "basic")
