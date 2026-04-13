# Marketing Legal Privacy

## Метаданные

- **Path:** `/legal/privacy` (`ROUTE_PATHS.marketing.legalPrivacy`)
- **Зона:** marketing
- **Компонент(ы) в App.tsx:** `LegalPrivacyPage`
- **Файл страницы:** `frontend/src/marketing/pages/LegalPrivacyPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/marketing/pages/LegalPrivacyPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/marketing/pages/LegalPrivacyPage.tsx` |
| Строк (сумма по фрагментам) | 225 |
| Хуки (эвристика, union) | — |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Публичная страница-заглушка политики конфиденциальности: фиксированный маршрут для лендинга, signup (ссылка из чекбокса) и чеклистов; финальный юридический текст подставляется вне этого кода (комментарий в исходнике: Phase 1b / МП §5).

## Логика и данные

- **Хуки:** нет (статический JSX).
- **API / React Query:** нет.
- **Навигация:** ссылка «На главную» → `ROUTE_PATHS.marketing.landing`.

## RBAC / entitlements / edition

Публичная страница; ограничений нет (**fact**).

## UI-скелет (as-built)

- `Container size="sm" py="xl"`.
- `Paper` с бордером: `Stack` — `Title` «Политика конфиденциальности», поясняющий `Text` (dimmed), `Anchor` на главную.

## Инвентарь поверхностей UI (ось H)

Модалок, `Drawer`, `Menu`, `Stepper`, критичных `Alert` **нет**. Интерактив: только `Anchor` (навигация).

## Целевой UX (target vs as-built)

- *as-built:* явная пометка, что текст временный; CTA на главную.
- *target:* полноценная политика ПДн перед продакшеном self-service (**gap** контента).

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md); текущий абзац — плейсхолдер (**fact**).

## Тесты

- `frontend/src/__tests__/routePaths.test.ts` — `ROUTE_PATHS.marketing.legalPrivacy` входит в паритет `ALL_PUBLIC_APP_PATHS` (блок «derived list matches ROUTE_PATHS»).
- Отдельных тестов на разметку страницы **не найдено** (**gap**).

## Gap scan (вторая редакция)

- Юридическое наполнение и локализация не в коде.
- При публикации финального текста обновить компонент и убрать формулировки «здесь будет».
