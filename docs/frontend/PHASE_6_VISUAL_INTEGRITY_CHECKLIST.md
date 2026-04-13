# Фаза 6 — визуальная целостность (критерий C4)

> **Версия:** 2026-04-09  
> **Мастер-план:** [`MASTER_FRONTEND_EXECUTION_PLAN.md`](./MASTER_FRONTEND_EXECUTION_PLAN.md) · **критерии:** [`pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md`](./pages/MASTER_FRONTEND_DOC_CRITERIA_EXTRACT.md) (C4)

## Что делаете вы лично (фаза 6)

Робот и CI **не видят** «ровные отступы», «красивую иерархию» и «не кустарно ли выглядит карточка». Поэтому ваша часть такая:

1. Поднять локально фронт и бэк по [`docs/RUN_SERVICES.md`](../RUN_SERVICES.md) (или staging).
2. Пройти **пять пилотных URL** из таблицы ниже в браузере (десктоп; при необходимости повторить в узком окне / мобильной эмуляции).
3. Зафиксировать результат: скопировать шаблон в конце раздела «Пилотные экраны» → вставить в описание PR, в тикет или внутренний отчёт релиза.
4. Если что-то бросается в глаза — либо завести задачу на правку, либо добавить **gap** в соответствующий паспорт страницы в `docs/frontend/pages/`.

Пока этого нет, фаза 6 **продуктово** не закрыта, даже если все команды ниже зелёные.

## Назначение

Зафиксировать **проверяемый** минимум для C4 без подмены живого браузера одним markdown: автоматизируемое + пилотные экраны + ручной проход. Полный скрин-регресс остаётся на решение команды (Playwright/Chromatic и т.д.).

## Быстрые автоматические ворота

| Проверка | Команда / артефакт | Ожидание |
|----------|-------------------|----------|
| Сборка SPA | из корня `frontend/`: `npm run build` | Успех |
| Правый drawer админки | из `frontend/`: `npx vitest run src/__tests__/adminNoRawMantineDrawer.test.ts` | 1 test passed |
| Соответствие маршрутов паспортам | из корня репо: `python scripts/gen_frontend_page_passport_stubs.py verify` | exit 0 |

## Журнал автоматических ворот (обновлять при релизном проходе)

| Дата (UTC) | Сборка / контекст | `verify` | `npm run build` | `adminNoRawMantineDrawer` | Кто зафиксировал |
|------------|-------------------|----------|-----------------|---------------------------|------------------|
| 2026-04-09 | локальный прогон агента @LEAD | OK | OK | OK (1 test) | automation |

*Строку можно копировать вниз и дополнять перед релизом.*

## Канон и дизайн-слой (что сверять глазами)

- Тема и семантика: [`UI_THEME.md`](./UI_THEME.md), `frontend/src/theme.ts`, `frontend/src/index.css`.
- Карта design→code: [`../design/DESIGN_CODE_MAP.md`](../design/DESIGN_CODE_MAP.md).
- Макро/микро оси: [`../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md`](../architecture/ENTERPRISE_SAAS_FRONTEND_RUBRIC_AND_ITERATIONS.md) (§3–4, μ1–μ7).

## Пилотные экраны (минимум для ручного прохода)

Согласованы с [`pages/README.md`](./pages/README.md) §«Эталонные паспорта»:

| Зона | Маршрут | Паспорт | Фокус проверки |
|------|---------|---------|----------------|
| Витрина | `/` | [`pages/marketing-landing.md`](./pages/marketing-landing.md) | иерархия блоков, CTA, отступы |
| Админка | `/admin` | [`pages/admin-dashboard.md`](./pages/admin-dashboard.md) | карточки, таблицы, плотность |
| Админка | `/admin/finance` | [`pages/admin-finance.md`](./pages/admin-finance.md) | Tabs, таблицы, toolbar-карточки |
| PWA | `/app/booking` (и зеркало `/c/.../app/booking`) | [`pages/app-booking.md`](./pages/app-booking.md) | шаги записи, состояния загрузки |
| Платформа | `/platform/login` | [`pages/platform-login.md`](./pages/platform-login.md) | форма, ошибки, без «сырого» HTML |

**Шаблон фиксации ручного прохода (копировать в PR или тикет):**

```text
Дата:
Сборка / коммит:
Пилоты: landing, admin dashboard, finance, app booking, platform login
Замечания (экран → наблюдение → серьёзность):
Регрессия дизайн-токенов: да/нет
```

## Критерий «готово» по фазе 6 (минимум документа)

- Ворота из таблицы выше зелёные на момент релиза/PR.
- Пилотные экраны пройдены вручную хотя бы один раз после значимых UI-изменений; результат зафиксирован (PR-описание или тикет).
- Расхождения с [`UI_THEME.md`](./UI_THEME.md) либо исправлены, либо занесены как **gap** в соответствующий паспорт страницы (ось target vs as-built).

## Связанные файлы

- [`../design/`](../design/) — концепт 85+, токены, playbook внедрения.  
- [`PAGE_PASSPORT_CRITERIA.md`](./PAGE_PASSPORT_CRITERIA.md) — ось H и согласованность с каноном.
