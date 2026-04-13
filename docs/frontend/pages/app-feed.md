# App Feed

## Метаданные

- **Path:** `/app/feed` и зеркало `/c/:clinicSlug/app/feed`
- **Зона:** app (пациент)
- **Компонент(ы) в App.tsx:** `FeedPage`
- **Файл страницы:** `frontend/src/app/pages/FeedPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/FeedPage.tsx`<br>`frontend/src/hooks/usePublicFeed.ts ← импорт из frontend/src/app/pages/FeedPage.tsx`<br>`frontend/src/routePaths.ts ← импорт из frontend/src/app/pages/FeedPage.tsx`<br>`frontend/src/shared/semanticUi.ts ← импорт из frontend/src/app/pages/FeedPage.tsx` |
| Строк (сумма по фрагментам) | 495 |
| Хуки (эвристика, union) | `useClinics`, `usePublicFeed`, `usePublicStories`, `useQuery` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Публичная лента клиники внутри PWA: горизонтальные сторис и список постов (текст, медиа, внешняя ссылка). Клиника берётся как **первая** из `useClinics()` — без списка клиник экран показывает «Нет выбранной клиники».

## Логика и данные

- **Хуки:** `useClinics`; `usePublicFeed`, `usePublicStories` из `usePublicFeed`.
- **queryKey:** список клиник как в `useClinics`; `public`, `clinics`, clinicId, `feed` и `stories`.
- **API:** `GET /v1/public/clinics/{clinicId}/feed`, `GET /v1/public/clinics/{clinicId}/stories` — без пациентского токена (общий `api` клиент).

## RBAC / entitlements / edition

- Не требует входа пациента в коде страницы (**fact**); при этом маршрут живёт под `AppLayout` с `PatientAuthProvider` в дереве `/c/.../app` и `/app` — фактический guard зависит от layout.

## UI-скелет (as-built)

`Title`, пояснение, блок сторис в `ScrollArea` с карточками (video/img), блок постов в `Card` с видео/картинками и `Anchor` «Подробнее», ссылка на booking.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu:** на странице нет.

## Целевой UX (target vs as-built)

- *target:* выбор клиники согласованный с `app.selectedClinicId` и домашним экраном, интерактив сторис.
- *as-built:* только `clinics[0]`; нет связи с localStorage выбора клиники.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Мультиклиника: пользователь может видеть ленту «не той» клиники.
- Пустой alt у картинок постов.
