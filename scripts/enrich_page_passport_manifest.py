#!/usr/bin/env python3
"""
Обогащение паспортов `docs/frontend/pages/<slug>.md` машиночитаемым блоком **из исходников фронта**.

Что это делает:
  — для каждого slug из `gen_frontend_page_passport_stubs._all_entries()` читает один или несколько `.tsx/.ts`;
  — извлекает эвристикой: импорты из `@/hooks`, идентификаторы `use*` (с фильтром React/Router/Mantine),
    строковые пути `/v1/...`, счётчики `AdminDrawer` / `GlassModal` / `<Modal` / `Menu`;
  — вставляет или обновляет фрагмент между HTML-комментариями `AUTO_MANIFEST` (идемпотентно).

Что это НЕ делает (честно для @QA_ARCH):
  — не поднимает Vite, не логинится в админку, **не делает скриншоты**;
  — не разбирает TSX через AST (эвристики могут давать ложные срабатывания на сложных файлах);
  — не заменяет ручной паспорт v2: блок помечен как вспомогательный инвентарь.

Использование (из корня репозитория):
  python scripts/enrich_page_passport_manifest.py [--dry-run]

После изменений:
  python scripts/gen_frontend_page_passport_stubs.py verify
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES_DIR = ROOT / "docs" / "frontend" / "pages"

# Компоненты React / router / частые @mantine/hooks — не считаем «доменными» хуками продукта.
_EXCLUDE_USE = frozenset(
    {
        "useState",
        "useEffect",
        "useLayoutEffect",
        "useMemo",
        "useCallback",
        "useRef",
        "useContext",
        "useId",
        "useReducer",
        "useImperativeHandle",
        "useSyncExternalStore",
        "useDeferredValue",
        "useTransition",
        "useDebugValue",
        "useInsertionEffect",
        "useForm",
        "useFieldArray",
        "useWatch",
        "useController",
        "useNavigate",
        "useSearchParams",
        "useParams",
        "useLocation",
        "useMatch",
        "useResolvedPath",
        "useOutlet",
        "useOutletContext",
        "useFetcher",
        "useSubmit",
        "useFormAction",
        "useHref",
        "useDisclosure",
        "useHotkeys",
        "useClipboard",
        "useMediaQuery",
        "useViewportSize",
        "useIntersection",
        "useScroll",
        "useCounter",
        "useToggle",
        "useLocalStorage",
        "useSessionStorage",
        "useColorScheme",
        "useComputedColorScheme",
        "useMantineColorScheme",
        "useMatches",
        "useShallowEffect",
        "useInViewport",
        "useWindowEvent",
        "useNetwork",
        "useFullscreen",
        "useHeadroom",
        "useFocusTrap",
        "useDidUpdate",
        "useIsomorphicEffect",
        "usePagination",
        "useListState",
        "useSetState",
        "useMap",
        "usePrevious",
        "useValidatedState",
        "useInputState",
        "useEyeDropper",
        "useFileDialog",
        "useHash",
        "useInterval",
        "useTimeout",
        "useMergedRef",
        "useMouse",
        "useMove",
        "useOrientation",
        "useQueue",
        "usePageLeave",
        "useTextSelection",
        "useIdle",
        "useFullscreen",
        "useLogger",
        "useValidatedState",
    }
)

_RE_IMPORT_HOOKS = re.compile(
    r"""import\s+\{([^}]+)\}\s+from\s+["']@/hooks(?:/[^"']+)?["']""",
    re.MULTILINE,
)
_RE_V1_PATH = re.compile(r"""["'](/v1/[a-zA-Z0-9_/{}\-.$]+)["']""")
_RE_HOOK_ID = re.compile(r"\b(use[A-Z][a-zA-Z0-9_]*)\b")


def _load_gen_module():
    path = ROOT / "scripts" / "gen_frontend_page_passport_stubs.py"
    name = "_dental_booking_gen_frontend_page_passport_stubs"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SystemExit("Cannot load gen_frontend_page_passport_stubs.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def _special_scan_slices(slug: str) -> list[tuple[Path, int | None, int | None]]:
    """(path, 1-based start line inclusive, 1-based end inclusive) or whole file if None."""
    if slug == "marketing-landing":
        return [(ROOT / "frontend/src/App.tsx", 212, 437)]
    return []


def _parse_page_files_field(raw: str) -> list[Path]:
    """`page_file` from PassportEntry may list multiple paths."""
    paths: list[Path] = []
    for m in re.finditer(r"(frontend/src/[a-zA-Z0-9_./\-]+\.(?:tsx|ts))", raw):
        paths.append(ROOT / m.group(1))
    return paths


def _posix_rel(p: Path) -> str:
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p).replace("\\", "/")


def _expand_at_imports(main_text: str) -> list[Path]:
    """Один уровень: разрешить `from "@/..."` относительно `frontend/src`."""
    found: list[Path] = []
    for m in re.finditer(r"""from\s+["']@/([^"']+)["']""", main_text):
        rel = m.group(1).strip()
        base = ROOT / "frontend" / "src" / rel
        candidates: list[Path] = [base]
        if not str(rel).endswith((".ts", ".tsx")):
            candidates = [base.with_suffix(".tsx"), base.with_suffix(".ts"), base]
        for c in candidates:
            if c.is_file():
                found.append(c)
                break
    seen: set[str] = set()
    out: list[Path] = []
    for p in found:
        k = str(p.resolve())
        if k not in seen:
            seen.add(k)
            out.append(p)
    return out[:14]


def _resolve_scan_blobs(slug: str, page_file_raw: str) -> list[tuple[str, str]]:
    """Return list of (label, text) to analyze."""
    special = _special_scan_slices(slug)
    if special:
        out: list[tuple[str, str]] = []
        for p, la, lb in special:
            lines = p.read_text(encoding="utf-8").splitlines()
            if la is not None and lb is not None:
                chunk = "\n".join(lines[la - 1 : lb])
                out.append((f"{_posix_rel(p)} (стр. {la}–{lb}, фрагмент `{slug}`)", chunk))
            else:
                out.append((_posix_rel(p), p.read_text(encoding="utf-8")))
        return out

    if slug == "auth-legacy-login-redirect":
        p = ROOT / "frontend/src/auth/LegacySignInRedirect.tsx"
        if p.is_file():
            return [(str(p.relative_to(ROOT)), p.read_text(encoding="utf-8"))]

    paths = _parse_page_files_field(page_file_raw)
    if not paths:
        raw0 = page_file_raw.split(";")[0].strip()
        m = re.match(r"^(frontend/src/[^\s`;]+)", raw0)
        if m:
            p = ROOT / m.group(1)
            if p.is_file():
                paths = [p]
    if not paths:
        return []

    blobs: list[tuple[str, str]] = []
    loaded: set[str] = set()
    for p in paths[:6]:
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        label = _posix_rel(p)
        if len(paths) > 1:
            label += " (часть цепочки)"
        blobs.append((label, text))
        loaded.add(str(p.resolve()))
        for extra in _expand_at_imports(text):
            k = str(extra.resolve())
            if k in loaded:
                continue
            loaded.add(k)
            blobs.append((f"{_posix_rel(extra)} ← импорт из {_posix_rel(p)}", extra.read_text(encoding="utf-8")))
    return blobs[:24]


def _hooks_from_imports(text: str) -> list[str]:
    found: set[str] = set()
    for m in _RE_IMPORT_HOOKS.finditer(text):
        inner = m.group(1)
        for part in inner.split(","):
            part = part.strip()
            if not part or part.startswith("//"):
                continue
            # `useX as y` → take first token
            tok = part.split()[0].strip()
            if tok.startswith("use"):
                found.add(tok)
    return sorted(found)


def _hooks_heuristic(text: str) -> list[str]:
    found: set[str] = set()
    for m in _RE_HOOK_ID.finditer(text):
        name = m.group(1)
        if name in _EXCLUDE_USE:
            continue
        if name.startswith("use"):
            found.add(name)
    return sorted(found)


def _api_paths(text: str) -> list[str]:
    seen: set[str] = set()
    for m in _RE_V1_PATH.finditer(text):
        s = m.group(1)
        if ".." in s:
            continue
        seen.add(s)
    return sorted(seen)


def _overlay_counts(text: str) -> dict[str, int]:
    return {
        "AdminDrawer": text.count("AdminDrawer"),
        "GlassModal": text.count("GlassModal"),
        "Mantine Modal": text.count("<Modal"),
        "Menu": text.count("<Menu"),
    }


def _build_manifest_markdown(
    slug: str,
    sources: list[tuple[str, str]],
    generated_at: str,
) -> str:
    if not sources:
        return (
            f"| Поле | Значение |\n|------|----------|\n"
            f"| Ошибка | не удалось сопоставить файлы для `page_file` |\n\n"
            f"_Проверьте `gen_frontend_page_passport_stubs.py` для slug `{slug}`._\n"
        )

    total_lines = 0
    all_text_parts: list[str] = []
    labels: list[str] = []
    for label, blob in sources:
        lines = blob.count("\n") + (1 if blob else 0)
        total_lines += lines
        all_text_parts.append(blob)
        labels.append(label)

    combined = "\n\n".join(all_text_parts)
    hooks_imp = _hooks_from_imports(combined)
    hooks_h = _hooks_heuristic(combined)
    apis = _api_paths(combined)[:48]
    oc = _overlay_counts(combined)

    # Показываем доменные хуки: импорт из @/hooks + эвристика без известного шума
    hooks_union = sorted(set(hooks_imp) | set(hooks_h))
    if len(hooks_union) > 60:
        hooks_show = hooks_union[:60]
        hooks_note = f" (показаны первые 60 из {len(hooks_union)})"
    else:
        hooks_show = hooks_union
        hooks_note = ""

    apis_note = ""
    if len(_api_paths(combined)) > 48:
        apis_note = f" — показано 48 из {len(_api_paths(combined))} уникальных"

    src_cell = "<br>".join(f"`{lb}`" for lb in labels[:4])
    if len(labels) > 4:
        src_cell += f"<br>… +{len(labels) - 4} файлов"

    lines = [
        f"**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **{generated_at}**).",
        "",
        "| Поле | Значение |",
        "|------|----------|",
        f"| Источник | {src_cell} |",
        f"| Строк (сумма по фрагментам) | {total_lines} |",
        f"| Хуки (эвристика, union){hooks_note} | {', '.join(f'`{h}`' for h in hooks_show) or '—' } |",
        f"| Пути в строках `/v1/...`{apis_note} | {', '.join(f'`{a}`' for a in apis) or '—' } |",
        f"| Вхождения UI | AdminDrawer: {oc['AdminDrawer']}, GlassModal: {oc['GlassModal']}, Modal: {oc['Mantine Modal']}, Menu: {oc['Menu']} |",
        "",
        "> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.",
        "",
    ]
    return "\n".join(lines)


BEGIN = "<!-- AUTO_MANIFEST:BEGIN -->"
END = "<!-- AUTO_MANIFEST:END -->"


def _inject_or_replace(content: str, manifest_body: str) -> str:
    block = f"{BEGIN}\n{manifest_body}\n{END}\n"
    if BEGIN in content and END in content:
        pre, rest = content.split(BEGIN, 1)
        _, post = rest.split(END, 1)
        post = post.lstrip("\n")
        if post.startswith("##"):
            return pre + block + "\n" + post
        return pre + block + post

    # Вставить перед «## Назначение», иначе после первого заголовка # 
    if "## Назначение" in content:
        parts = content.split("## Назначение", 1)
        return parts[0].rstrip() + "\n\n" + block + "\n## Назначение" + parts[1]
    return content.rstrip() + "\n\n" + block


def cmd_run(dry_run: bool) -> int:
    mod = _load_gen_module()
    entries = mod._all_entries()
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    updated = 0
    for ent in entries:
        md_path = PAGES_DIR / f"{ent.slug}.md"
        if not md_path.is_file():
            print("WARN: missing", md_path, file=sys.stderr)
            continue
        sources = _resolve_scan_blobs(ent.slug, ent.page_file)
        manifest = _build_manifest_markdown(ent.slug, sources, ts)
        text = md_path.read_text(encoding="utf-8")
        new_text = _inject_or_replace(text, manifest)
        if new_text != text:
            updated += 1
            if not dry_run:
                md_path.write_text(new_text, encoding="utf-8")
    print(f"OK: processed {len(entries)} passport(s); updated {updated} file(s)" + (" (dry-run)" if dry_run else "."))
    return 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Inject AUTO_MANIFEST blocks into page passports.")
    ap.add_argument("--dry-run", action="store_true", help="Print stats only; do not write files.")
    args = ap.parse_args()
    raise SystemExit(cmd_run(args.dry_run))


if __name__ == "__main__":
    main()
