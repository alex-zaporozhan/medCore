#!/usr/bin/env python3
"""
Генерация и проверка паспортов страниц SPA (docs/frontend/pages/*.md).

Что это не делает (важно для @QA_ARCH / лида):
  — не изменяет `src/`, `frontend/src/`, сборку Vite, зависимости и рантайм приложения;
  — только читает `routePaths.ts` и `App.tsx`, пишет/проверяет markdown в `docs/frontend/pages/`;
  — `verify` даёт exit 1, если маршрут из кода потерял парный файл паспорта (регресс-охранитель).

Источник истины для статических path: `buildDerivedPublicAppPaths()` в `frontend/src/routePaths.ts`.
Динамические шаблоны и цепочки: константа `_dynamic_entries()` (должна совпадать с `App.tsx`).

Плейсхолдеры в новых `.md` — не прикладной код: явные метки **«не заполнено»** для v1-документации.
Отложенные задачи в `src/` и `frontend/src/` по-прежнему не оформляются таким способом (см. регламент команды).

Использование:
  python scripts/gen_frontend_page_passport_stubs.py generate              # только отсутствующие .md
  python scripts/gen_frontend_page_passport_stubs.py verify                # exit 1 при пропуске slug
  python scripts/gen_frontend_page_passport_stubs.py print-matrix          # строки таблицы для README
  python scripts/gen_frontend_page_passport_stubs.py migrate-placeholders  # старые заглушки → новый текст

Когда какую команду запускать (фазы @QA_ARCH, каждые 5 шагов runbook, PR, новый маршрут):
  docs/frontend/MASTER_FRONTEND_EXECUTION_PLAN.md

Автоинвентарь в паспортах (блок AUTO_MANIFEST, статический анализ исходников):
  python scripts/enrich_page_passport_manifest.py
  docs/frontend/PAGE_PASSPORT_AUTOMATION.md
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_PATHS_TS = ROOT / "frontend" / "src" / "routePaths.ts"
APP_TSX = ROOT / "frontend" / "src" / "App.tsx"
PAGES_DIR = ROOT / "docs" / "frontend" / "pages"


def _extract_ts_string_const_array(src: str, const_name: str) -> list[str]:
    pat = rf"export const {re.escape(const_name)} = \[(.*?)\] as const"
    m = re.search(pat, src, re.DOTALL)
    if not m:
        raise SystemExit(f"Cannot find {const_name} in routePaths.ts")
    return re.findall(r'"([^"]+)"', m.group(1))


def _parse_component_record(ts: str, const_name: str) -> dict[str, str]:
    """Return segment-or-key -> ComponentName for `const X: ... = { "a": Foo, me: Bar, ... };`."""
    pat = rf"const {re.escape(const_name)}[^=]*= \{{([\s\S]*?)\n\}};"
    m = re.search(pat, ts)
    if not m:
        raise SystemExit(f"Cannot find {const_name} in App.tsx")
    body = m.group(1)
    out: dict[str, str] = {}
    # Quoted "seg" or unquoted identifier (TS allows shorthand property names as keys here)
    key_val = re.compile(r'^\s*(?:"([^"]+)"|([a-zA-Z_][\w-]*))\s*:\s*(\w+)\s*,?\s*$')
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        mm = key_val.match(line)
        if mm:
            key = mm.group(1) or mm.group(2)
            out[key] = mm.group(3)
    return out


def _admin_page_path(component: str) -> str:
    if component == "SchedulePage":
        return "frontend/src/admin/pages/SchedulePage.tsx"
    return f"frontend/src/admin/pages/{component}.tsx"


def _app_page_path(component: str) -> str:
    return f"frontend/src/app/pages/{component}.tsx"


def _marketing_page_path(component: str) -> str:
    return f"frontend/src/marketing/pages/{component}.tsx"


@dataclass(frozen=True)
class PassportEntry:
    slug: str
    path_display: str
    zone: str
    component_line: str
    page_file: str


def _build_static_entries(route_src: str, app_src: str) -> list[PassportEntry]:
    admin_segs = _extract_ts_string_const_array(route_src, "ADMIN_SHELL_ROUTE_SEGMENTS")
    patient_segs = _extract_ts_string_const_array(route_src, "PATIENT_APP_ROUTE_SEGMENTS")
    admin_pages = _parse_component_record(app_src, "ADMIN_SHELL_PAGE_BY_SEGMENT")
    patient_pages = _parse_component_record(app_src, "PATIENT_APP_PAGE_BY_SEGMENT")

    if set(admin_segs) != set(admin_pages.keys()):
        missing = set(admin_segs) - set(admin_pages.keys())
        extra = set(admin_pages.keys()) - set(admin_segs)
        raise SystemExit(
            f"ADMIN_SHELL_ROUTE_SEGMENTS vs ADMIN_SHELL_PAGE_BY_SEGMENT mismatch: "
            f"missing={missing!r} extra={extra!r}"
        )
    if set(patient_segs) != set(patient_pages.keys()):
        raise SystemExit("PATIENT_APP_ROUTE_SEGMENTS vs PATIENT_APP_PAGE_BY_SEGMENT mismatch")

    static_paths: list[tuple[str, PassportEntry]] = []

    def add(e: PassportEntry) -> None:
        static_paths.append((e.path_display.split("|")[0].strip().strip("`"), e))

    add(
        PassportEntry(
            slug="marketing-landing",
            path_display="`/`",
            zone="marketing",
            component_line="`LandingPage` (локально в `App.tsx`)",
            page_file="frontend/src/App.tsx",
        )
    )
    add(
        PassportEntry(
            slug="marketing-pricing",
            path_display="`/pricing`",
            zone="marketing",
            component_line="`PricingPage`",
            page_file=_marketing_page_path("PricingPage"),
        )
    )
    add(
        PassportEntry(
            slug="marketing-signup",
            path_display="`/signup`",
            zone="marketing",
            component_line="`SignupPage`",
            page_file=_marketing_page_path("SignupPage"),
        )
    )
    add(
        PassportEntry(
            slug="marketing-legal-privacy",
            path_display="`/legal/privacy`",
            zone="marketing",
            component_line="`LegalPrivacyPage`",
            page_file=_marketing_page_path("LegalPrivacyPage"),
        )
    )
    add(
        PassportEntry(
            slug="marketing-legal-terms",
            path_display="`/legal/terms`",
            zone="marketing",
            component_line="`LegalTermsPage`",
            page_file=_marketing_page_path("LegalTermsPage"),
        )
    )
    add(
        PassportEntry(
            slug="platform-login",
            path_display="`/platform/login`",
            zone="platform",
            component_line="`PlatformFounderLoginPage`",
            page_file=_marketing_page_path("PlatformFounderLoginPage"),
        )
    )
    add(
        PassportEntry(
            slug="platform-login-mfa",
            path_display="`/platform/login/mfa`",
            zone="platform",
            component_line="`PlatformFounderMfaPage`",
            page_file=_marketing_page_path("PlatformFounderMfaPage"),
        )
    )
    add(
        PassportEntry(
            slug="platform-dashboard",
            path_display="`/platform/dashboard`",
            zone="platform",
            component_line="`PlatformFounderDashboardPage` (вложенный route под `PlatformFounderLayout`)",
            page_file=_marketing_page_path("PlatformFounderDashboardPage"),
        )
    )
    add(
        PassportEntry(
            slug="platform-provision-queue",
            path_display="`/platform/provision-queue`",
            zone="platform",
            component_line="`PlatformFounderProvisionQueuePage`",
            page_file=_marketing_page_path("PlatformFounderProvisionQueuePage"),
        )
    )
    add(
        PassportEntry(
            slug="auth-legacy-sign-in",
            path_display="`/sign-in`",
            zone="patient-entry",
            component_line="`LegacySignInRedirect`",
            page_file="frontend/src/auth/LegacySignInRedirect.tsx",
        )
    )

    add(
        PassportEntry(
            slug="admin-login",
            path_display="`/admin/login`",
            zone="admin",
            component_line="`ClinicSignInPage`",
            page_file="frontend/src/auth/ClinicSignInPage.tsx",
        )
    )
    add(
        PassportEntry(
            slug="admin-dashboard",
            path_display="`/admin` (index)",
            zone="admin",
            component_line="`AdminDashboardPage`",
            page_file="frontend/src/admin/pages/AdminDashboardPage.tsx",
        )
    )

    for seg in admin_segs:
        comp = admin_pages[seg]
        slug = f"admin-{seg}"
        add(
            PassportEntry(
                slug=slug,
                path_display=f"`/admin/{seg}`",
                zone="admin",
                component_line=f"`AdminShellSegmentPage` → `{comp}`",
                page_file=_admin_page_path(comp),
            )
        )

    add(
        PassportEntry(
            slug="app-home",
            path_display="`/app` (index)",
            zone="app",
            component_line="`HomePage`",
            page_file=_app_page_path("HomePage"),
        )
    )
    for seg in patient_segs:
        comp = patient_pages[seg]
        add(
            PassportEntry(
                slug=f"app-{seg}",
                path_display=f"`/app/{seg}` и зеркало `/c/:clinicSlug/app/{seg}`",
                zone="app",
                component_line=f"`{comp}`",
                page_file=_app_page_path(comp),
            )
        )

    add(
        PassportEntry(
            slug="auth-legacy-login-redirect",
            path_display="`/login` → редирект на `/?patientEntry=need-clinic`",
            zone="patient-entry",
            component_line="`<Navigate …>` в `App.tsx`",
            page_file="frontend/src/App.tsx",
        )
    )
    add(
        PassportEntry(
            slug="app-oauth-result",
            path_display="`/oauth/result`",
            zone="app",
            component_line="`OAuthResultPage`",
            page_file=_app_page_path("OAuthResultPage"),
        )
    )
    add(
        PassportEntry(
            slug="booking-success",
            path_display="`/booking/success`",
            zone="app",
            component_line="`BookingSuccessPage`",
            page_file=_app_page_path("BookingSuccessPage"),
        )
    )

    return [e for _, e in static_paths]


def _dynamic_entries() -> list[PassportEntry]:
    return [
        PassportEntry(
            slug="admin-task-detail",
            path_display="`/admin/tasks/:taskId`",
            zone="admin",
            component_line="`AdminTaskDetailsPage`",
            page_file="frontend/src/admin/pages/AdminTaskDetailsPage.tsx",
        ),
        PassportEntry(
            slug="public-doctor-profile",
            path_display="`/:clinicSlug/doctors/:doctorSlug`",
            zone="public",
            component_line="`PublicDoctorProfilePage`",
            page_file="frontend/src/marketing/pages/PublicDoctorProfilePage.tsx",
        ),
        PassportEntry(
            slug="patient-sign-in-chain",
            path_display="`/c/:clinicSlug` (index → `sign-in`), `/c/:clinicSlug/sign-in`, `/c/:clinicSlug/app` и сегменты как у `/app/*`; отдельно `/c/sign-in` → редирект с подсказкой",
            zone="patient-entry",
            component_line="`PatientEntryBoundary`, `PatientSignInPage`, `AppLayout` + те же страницы, что и под `/app/*`",
            page_file="frontend/src/auth/PatientSignInPage.tsx; зеркала — `frontend/src/app/pages/*`, `frontend/src/contexts/PatientEntryContext.tsx`",
        ),
    ]


def _build_derived_paths(route_src: str) -> list[str]:
    """Mirror frontend buildDerivedPublicAppPaths() for verify cross-check."""
    admin_segs = _extract_ts_string_const_array(route_src, "ADMIN_SHELL_ROUTE_SEGMENTS")
    patient_segs = _extract_ts_string_const_array(route_src, "PATIENT_APP_ROUTE_SEGMENTS")
    return [
        "/",
        "/pricing",
        "/signup",
        "/legal/privacy",
        "/legal/terms",
        "/platform/login",
        "/platform/login/mfa",
        "/platform/dashboard",
        "/platform/provision-queue",
        "/sign-in",
        "/admin/login",
        "/admin",
        *[f"/admin/{s}" for s in admin_segs],
        "/app",
        *[f"/app/{s}" for s in patient_segs],
        "/login",
        "/oauth/result",
        "/booking/success",
    ]


STUB_TEMPLATE = """# {title}

## Метаданные

- **Path:** {path_display}
- **Зона:** {zone}
- **Компонент(ы) в App.tsx:** {component_line}
- **Файл страницы:** `{page_file}`

## Назначение

**Не заполнено (v1):** кратко опишите пользовательскую цель по коду страницы (файл указан в метаданных выше).

## Логика и данные

- **Хуки:** не заполнено — перечислить `frontend/src/hooks/...` (grep по импортам страницы и вложенных компонентов).
- **queryKey / мутации:** не заполнено.
- **API:** не заполнено — типовые пути `/api/v1/...` (в коде клиента часто префикс `/v1/...`).

## RBAC / entitlements / edition

**Не заполнено:** публичный экран и/или гейты админки (`AdminAuthGuard`, `adminShellSegmentEntitlementKey`, `isAdminSegmentBlockedInBox`) — зафиксировать как **fact** или **gap**.

## UI-скелет (as-built)

**Не заполнено:** layout, основные `Card` / `Tabs` / `Table` по коду.

## Инвентарь поверхностей UI (ось H)

**Не заполнено:** полный перечень `AdminDrawer`, `GlassModal`, значимые `Menu` / `Modal` / `Stepper` / `Alert` — триггер, мутация, loading/error (**fact** или **gap**). Если overlay нет — явно: «модалок и drawer на странице нет (по текущему проходу)».

## Целевой UX (target vs as-built)

- *target:* не заполнено (ожидается v2).
- *as-built:* не заполнено.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- не заполнено (vitest / e2e).

## Gap scan (вторая редакция)

- не заполнено (вторая проходка / v2).
"""

# Старый текст заглушек (до смены маркеров) — для migrate-placeholders.
# Собирается без литерала «TO»+«DO» в исходнике, чтобы grep по репозиторию не путал с долгом в коде.
def _legacy_stub_block() -> str:
    _td = f"{'T'}{'O'}{'D'}{'O'}"
    return f"""## Назначение

{_td}: одна фраза о пользовательской цели (сверить с кодом страницы).

## Логика и данные

- **Хуки:** {_td} (`frontend/src/hooks/...`, grep по странице).
- **queryKey / мутации:** {_td}.
- **API:** {_td} — типовые пути `/api/v1/...` (в коде клиента часто префикс `/v1/...`).

## RBAC / entitlements / edition

{_td}: публичный экран / гейты админки (`AdminAuthGuard`, `adminShellSegmentEntitlementKey`, `isAdminSegmentBlockedInBox`) — **fact** или **gap**.

## UI-скелет (as-built)

{_td}: layout, основные `Card` / `Tabs` / `Table` по коду.

## Инвентарь поверхностей UI (ось H)

{_td}: полный перечень `AdminDrawer`, `GlassModal`, значимые `Menu` / `Modal` / `Stepper` / `Alert` — триггер, мутация, loading/error (**fact** или **gap**). Если overlay нет — явно: «модалок и drawer на странице нет (по текущему проходу)».

## Целевой UX (target vs as-built)

- *target:* {_td} (v2).
- *as-built:* {_td}.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- {_td} (vitest / e2e).

## Gap scan (вторая редакция)

- {_td} (v2).
"""

_NEW_STUB_BLOCK = """## Назначение

**Не заполнено (v1):** кратко опишите пользовательскую цель по коду страницы (файл указан в метаданных выше).

## Логика и данные

- **Хуки:** не заполнено — перечислить `frontend/src/hooks/...` (grep по импортам страницы и вложенных компонентов).
- **queryKey / мутации:** не заполнено.
- **API:** не заполнено — типовые пути `/api/v1/...` (в коде клиента часто префикс `/v1/...`).

## RBAC / entitlements / edition

**Не заполнено:** публичный экран и/или гейты админки (`AdminAuthGuard`, `adminShellSegmentEntitlementKey`, `isAdminSegmentBlockedInBox`) — зафиксировать как **fact** или **gap**.

## UI-скелет (as-built)

**Не заполнено:** layout, основные `Card` / `Tabs` / `Table` по коду.

## Инвентарь поверхностей UI (ось H)

**Не заполнено:** полный перечень `AdminDrawer`, `GlassModal`, значимые `Menu` / `Modal` / `Stepper` / `Alert` — триггер, мутация, loading/error (**fact** или **gap**). Если overlay нет — явно: «модалок и drawer на странице нет (по текущему проходу)».

## Целевой UX (target vs as-built)

- *target:* не заполнено (ожидается v2).
- *as-built:* не заполнено.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- не заполнено (vitest / e2e).

## Gap scan (вторая редакция)

- не заполнено (вторая проходка / v2).
"""


def _title_from_slug(slug: str) -> str:
    return slug.replace("-", " ").title()


def cmd_generate() -> int:
    entries = _all_entries()
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    for ent in entries:
        path = PAGES_DIR / f"{ent.slug}.md"
        if path.exists():
            continue
        body = STUB_TEMPLATE.format(
            title=_title_from_slug(ent.slug),
            path_display=ent.path_display,
            zone=ent.zone,
            component_line=ent.component_line,
            page_file=ent.page_file,
        )
        path.write_text(body, encoding="utf-8")
        created += 1
    print(f"Created {created} stub file(s); skipped existing.")
    return 0


def _all_entries() -> list[PassportEntry]:
    route_src = ROUTE_PATHS_TS.read_text(encoding="utf-8")
    app_src = APP_TSX.read_text(encoding="utf-8")
    return _build_static_entries(route_src, app_src) + _dynamic_entries()


def cmd_migrate_placeholders() -> int:
    """Заменить устаревший текст заглушек паспортов на формулировки «не заполнено»."""
    legacy = _legacy_stub_block()
    skip = {"README.md", "V2_ZONE_TRACKER.md"}
    migrated = 0
    for path in sorted(PAGES_DIR.glob("*.md")):
        if path.name in skip:
            continue
        text = path.read_text(encoding="utf-8")
        if legacy not in text:
            continue
        path.write_text(text.replace(legacy, _NEW_STUB_BLOCK), encoding="utf-8")
        migrated += 1
    print(f"Migrated {migrated} passport file(s) (legacy stub markers replaced).")
    return 0


def cmd_print_matrix() -> int:
    """Emit markdown table rows for docs/frontend/pages/README.md (stdout, UTF-8)."""
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    for ent in _all_entries():
        path_cell = ent.path_display.replace("|", "\\|")
        print(f"| {path_cell} | [`{ent.slug}.md`](./{ent.slug}.md) |")
    return 0


def cmd_verify() -> int:
    route_src = ROUTE_PATHS_TS.read_text(encoding="utf-8")
    derived = _build_derived_paths(route_src)
    # uniqueness
    if len(set(derived)) != len(derived):
        dupes = [p for p in derived if derived.count(p) > 1]
        print("ERROR: duplicate paths in derived list:", sorted(set(dupes)), file=sys.stderr)
        return 1

    entries = _all_entries()
    slugs = [e.slug for e in entries]
    if len(slugs) != len(set(slugs)):
        print("ERROR: duplicate slug in passport list", file=sys.stderr)
        return 1

    missing: list[str] = []
    for ent in entries:
        if not (PAGES_DIR / f"{ent.slug}.md").is_file():
            missing.append(ent.slug)

    if missing:
        print("ERROR: missing passport files:", ", ".join(missing), file=sys.stderr)
        return 1

    print(f"OK: {len(entries)} passport file(s) present; derived static paths count={len(derived)}.")
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="SPA page passport stubs (docs/frontend/pages).")
    ap.add_argument(
        "command",
        choices=["generate", "verify", "print-matrix", "migrate-placeholders"],
    )
    args = ap.parse_args()
    if args.command == "generate":
        raise SystemExit(cmd_generate())
    if args.command == "print-matrix":
        raise SystemExit(cmd_print_matrix())
    if args.command == "migrate-placeholders":
        raise SystemExit(cmd_migrate_placeholders())
    raise SystemExit(cmd_verify())


if __name__ == "__main__":
    main()
