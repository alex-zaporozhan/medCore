# Admin Embed

## Метаданные

- **Path:** `/admin/embed`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminEmbedPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminEmbedPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminEmbedPage.tsx`<br>`frontend/src/hooks/useAdminEmbed.ts ← импорт из frontend/src/admin/pages/AdminEmbedPage.tsx`<br>`frontend/src/hooks/useAdminSession.ts ← импорт из frontend/src/admin/pages/AdminEmbedPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminEmbedPage.tsx` |
| Строк (сумма по фрагментам) | 959 |
| Хуки (эвристика, union) | `useAdminEmbed`, `useAdminEmbedApiKeys`, `useAdminEmbedSettings`, `useAdminSession`, `useCreateAdminEmbedApiKeyMutation`, `useMutation`, `useQuery`, `useQueryClient`, `useRevokeAdminEmbedApiKeyMutation`, `useRotateAdminEmbedWebhookMutation` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/admin/organization/embed/api-keys`, `/v1/admin/organization/embed/settings`, `/v1/admin/organization/embed/webhook-secret/rotate`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 2, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Организационные настройки встраивания: публичный URL webhook inbox (`/api/v1/public/embed/v1/hooks/{token}/inbox`), ротация Bearer-секрета, выпуск и отзыв API-ключей для виджета и server-to-server. Одноразовые секреты показываются в модалках после создания.

## Логика и данные

- **Хуки:** `useAdminSession`, `useAdminEmbedSettings`, `useAdminEmbedApiKeys`, `useCreateAdminEmbedApiKeyMutation`, `useRevokeAdminEmbedApiKeyMutation`, `useRotateAdminEmbedWebhookMutation` (`frontend/src/hooks/useAdminEmbed.ts`).
- **queryKey:** `queryKeys.adminEmbed.settings()`, `queryKeys.adminEmbed.apiKeys()` (см. `frontend/src/queryKeys.ts`).
- **API:** `GET /v1/admin/organization/embed/settings`; `GET /v1/admin/organization/embed/api-keys`; `POST /v1/admin/organization/embed/api-keys`; `POST /v1/admin/organization/embed/api-keys/{id}/revoke`; `POST /v1/admin/organization/embed/webhook-secret/rotate`.

## RBAC / entitlements / edition

- **Entitlement:** `omni.embed.bundle` — см. `SEGMENT_ENTITLEMENT.embed` и `ADMIN_NAV_PATH_ENTITLEMENT_KEY`; при `entitlement_required` в ответе API — красный `Alert`.
- **Permission:** выпуск ключей и ротация webhook — `manage_embed_settings`; без него серый `Alert` «Только просмотр» и disabled кнопки.
- **Организация:** без `organization_id` — жёлтый `Alert` про привязку и опцию тарифа.
- **Box:** сегмент `embed` в `BOX_DISALLOWED_ADMIN_SEGMENTS` — редирект на дашборд при прямом заходе в редакции Box.

## UI-скелет (as-built)

`ContextBar` — блоки `AdminSettingsSectionCard` (webhook URL с копированием, таблица ключей) — два **`Modal`** для показа одноразового токена и webhook secret.

## Инвентарь поверхностей UI (ось H)

- **`Modal` (Mantine), два:** «Сохраните API key» и «Webhook secret» — после успешных мутаций, с `Alert` про однократный показ и кнопкой «Готово».
- **`AdminDrawer` / `GlassModal`:** на странице нет.
- **Отзыв ключа:** `window.confirm` перед `revokeKey.mutate` (**gap** относительно единообразия с модалками админки).

## Целевой UX (target vs as-built)

- *target:* подтверждение отзыва в дизайн-системе админки без `window.confirm`.
- *as-built:* секреты показываются осознанно в модалках; публичный путь webhook собирается из `window.location.origin`.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Сборка базового URL webhook зависит от `window` — для браузера нормально, для SSR-пререндера страницы не подходит.
