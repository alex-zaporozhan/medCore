# Маршрут @LEAD: унификация дизайна под Swiss Slate / Ink

**Роль:** @LEAD (координация DESIGN + DEV FE + правка артефактов).  
**Канон визуала:** `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` **§3.6** (токены, тени, кнопки, эффекты).  
**Выбранная палитра:** вариант **1 — Swiss Slate / Ink** (`docs/design/DESIGN_PALETTE_OPTIONS_PREMIUM_V1.md`, свотчи `docs/design/DESIGN_PALETTE_SPECTRUM_SWATCHES.html`).

Цель: один **design language** в коде и в документации; убрать рассинхрон **indigo + синий alpha** и устаревшие формулировки «Crisp = indigo по умолчанию».

---

## Порядок работ (кратко)

1. **Зафиксировать канон** — ссылка на §3.6 в weekly / decision log (см. `LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md` Step 0).
2. **Код** — тема + CSS-токены → shell → P0 страницы (по roadmap из `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §8).
3. **Документы** — обновить перечисленные ниже файлы, чтобы не врали новым разработчикам.
4. **Проверка** — свотчи HTML + spot-check админки; `prefers-reduced-motion` для whitelist-анимаций §3.6.9.

---

## A. Источник правды (прочитать один раз, дальше только ссылаться)

| Файл | Зачем |
|------|--------|
| `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` | §3.2–3.6 — роли цвета, токены, elevation, кнопки, эффекты |
| `docs/design/DESIGN_PALETTE_PREMIUM_MANTINE.md` | Техдолг alpha/hue, Mantine |
| `docs/design/DESIGN_PALETTE_OPTIONS_PREMIUM_V1.md` | Вариант 1 (таблица hex) |
| `docs/design/DESIGN_PALETTE_SPECTRUM_SWATCHES.html` | Визуальная проверка спектра |

---

## B. Код — обязательный проход (унификация реализации)

| Приоритет | Файл / зона | Действие |
|-------------|-------------|----------|
| P0 | `frontend/src/theme.ts` | Кортеж **brand/ink** (не stock indigo); `primaryColor` → `brand` или сохранить ключ с кортежем ink; тени §3.6.4 |
| P0 | `frontend/src/index.css` | `:root`: `--primary`, `--focus-ring`, **`--primary-alpha-*` из RGB ink** (`#1c2e45`), не `rgba(59,130,246,…)`; поверхности `--surface-app` `#f4f6f8` по канону |
| P0 | `frontend/src/admin/layouts/AdminLayout.tsx` + глобальные стили навигации | Активный пункт: `--brand-50` + текст/иконка `--brand-600` (§3.6.3) |
| P1 | `frontend/src/app/layouts/AppLayout.tsx` | Согласовать фон main / shell с токенами §3.6 |
| P1 | `frontend/src/shared/ui/shellPanelStyles.ts` | Любые хардкоды primary/sidebar — на токены |
| P2 | Страницы из инвентаря `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §2 | Убрать ad-hoc hex; P0 экраны первыми |

**Поиск по репозиторию (для sweep):** `4f46e5`, `6366F1`, `indigo.`, `59, 130, 246`, `3b82f6` в `frontend/src` — вне обоснованной семантики info.

---

## C. Артефакты и шаблоны — обновить под новое решение

Ниже документы, которые **до сих пор описывают indigo / Crisp без ink** или расходятся с §3.6. LEAD направляет @DESIGN или @DEV на правку **по очереди приоритета**.

### C1 — Критичные (вводят в заблуждение при онбординге)

| Файл | Что сделать |
|------|----------------|
| `docs/ARCH_FRONTEND_UI_LOGIC.md` | Заменить канон primary: **ink** и токены §3.6.2; сайдбар `brand.0` / `brand.6`; чеклист согласовать с `theme.ts` |
| `docs/TECH_PASSPORT_FRONTEND_UI_LOGIC.md` | §7 (и при необходимости §9): Crisp SaaS + **Swiss Slate / Ink**, не «indigo как primaryColor по умолчанию» |
| `docs/ROLE_FRONTEND.md` | Уже есть `primaryColor: "brand"` — убедиться, что описание совпадает с **ink**-кортежом и ссылкой на §3.6 |
| `docs/artifacts/DEV_PROMPTS_ADMIN_CRISP_SAAS_UI_2026.md` | Заменить чеклисты `indigo` → **ink/brand**; ссылка на `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6 |
| `docs/design/DESIGN_TOKENS_85_PLUS.json` | Синхронизация с `theme.ts` / `index.css`; `meta.source` + версия |

### C2 — Продуктовые / LEAD / дизайн-процесс

| Файл | Что сделать |
|------|----------------|
| `docs/design/LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md` | Step 1 Token adoption: явная ссылка на **Swiss Slate / Ink** и `LEAD_DESIGN_UNIFICATION_ROUTE_SWISS_SLATE_INK.md` |
| `docs/design/LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md` | Секции про цвет/primary — выровнять с §3.6 |
| `docs/artifacts/DEV_A_TO_B_EXECUTION_PATH_85_PLUS.md` | Если файл есть в репозитории — пункт про канон палитры §3.6 |
| `docs/TEMPLATE_ADMIN_UI_UX.md` | § про визуальные нorms — ink + ссылка на enterprise concept |

### C3 — Справочные / могут остаться с пометкой «история»

| Файл | Что сделать |
|------|----------------|
| `docs/artifacts/ARCH_FRONTEND_ENTERPRISE_BASELINE.md` | Дополнить примечанием: визуальный канон 85+ см. `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6 (не полагаться только на «indigo» из старых roadmap) |
| `docs/artifacts/ARCH_FRONTEND_85_PLUS_ALIGNMENT.md` | При наличии расхождений — таблица «было indigo → стало ink» |
| `docs/design/DESIGN_PALETTE_PREMIUM_MANTINE.md` | Обновить §3.1: целевой primary = **ink**, после миграции закрыть пункт про blue-alpha баг |

### C4 — Опционально (не блокер, но полезно)

| Файл | Зачем |
|------|--------|
| `docs/DOMAIN_STANDARDS.md` | Если есть UI-отсылка — одна ссылка на §3.6 |
| [STREAM_PRODUCTION_READINESS.md](../architecture/arch_plan/STREAM_PRODUCTION_READINESS.md) (PRC / L3) | Критерий приёмки UI: соответствие токенам Swiss Slate / Ink |

---

## D. Definition of Done для «унификация завершена»

- [x] `theme.ts` + `index.css` отражают **один** hue для brand и alpha (выполнено 2026-03: `primaryColor: brand`, ink-кортеж, alpha RGB 28,46,69).
- [x] `docs/design/DESIGN_TOKENS_85_PLUS.json` совпадает с каноном §3.6 (см. `meta.version`).
- [x] Документы **C1** и ключевые **C2/C3** обновлены под Swiss Slate / Ink; оставшиеся упоминания `indigo` в коде — **намеренный алиас** шкалы ink.
- [ ] Полный grep по `frontend/src` на ad-hoc hex старых primary + визуальная приёмка всех P0 экранов — по мере прохода roadmap §8 концепта.
- [ ] `docs/design/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §9 DoD закрыт по токенам (после финального sign-off @LEAD).

---

*Этот файл — единая точка входа для @LEAD: «куда смотреть и что править» после принятия Swiss Slate / Ink.*
