# Admin Data Export

## Метаданные

- **Path:** `/admin/data-export`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminDataExportPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminDataExportPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminDataExportPage.tsx`<br>`frontend/src/api/client.ts ← импорт из frontend/src/admin/pages/AdminDataExportPage.tsx`<br>`frontend/src/hooks/useAdminDataExport.ts ← импорт из frontend/src/admin/pages/AdminDataExportPage.tsx`<br>`frontend/src/hooks/useAdminSession.ts ← импорт из frontend/src/admin/pages/AdminDataExportPage.tsx` |
| Строк (сумма по фрагментам) | 734 |
| Хуки (эвристика, union) | `useAdminDataExport`, `useAdminDataExportSummary`, `useAdminSession`, `useMutation`, `useQuery`, `useQueryClient`, `useRequestDataExportMutation` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/admin/auth/session`, `/v1/admin/organization/data-export/request`, `/v1/admin/organization/data-export/summary`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Для роли **owner**: просмотр сводки объёмов данных организации без PII, скачивание machine-readable манифеста (`manifest.jsonl`) и регистрация заявки на полную выгрузку через OPS (комментарий до 500 символов).

## Логика и данные

- **Хуки:** `useAdminSession`, `useAdminDataExportSummary` (`isOwner && orgReady`), `useRequestDataExportMutation` (`frontend/src/hooks/useAdminDataExport.ts`).
- **queryKey:** `queryKeys.adminDataExport.summary()`.
- **API:** `GET /v1/admin/organization/data-export/summary`; `POST /v1/admin/organization/data-export/request`; манифест — прямой `fetch` на `${API_BASE}/v1/admin/organization/data-export/manifest.jsonl` с Bearer (`getAdminToken`), вне TanStack Query.

## RBAC / entitlements / edition

- **Роль:** без `owner` в `session.roles` — жёлтый `Alert`, основной контент не показывается.
- **Организация:** без `organization_id` — серый `Alert` про привязку.
- В `SEGMENT_ENTITLEMENT` для `data-export` ключа нет (**fact**).
- Box не блокирует сегмент.

## UI-скелет (as-built)

`Stack` с отступом → `ContextBar` → три блока `AdminSettingsSectionCard`: сводка (список `approximate_counts`), кнопка скачивания манифеста, заявка с `Textarea` и кнопкой «Зарегистрировать заявку».

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** нет.
- **Обратная связь:** `window.alert` при ошибке скачивания манифеста, при успехе/ошибке мутации заявки (**gap** относительно `QueryErrorAlert`/тостов).

## Целевой UX (target vs as-built)

- *target:* уведомления в стиле админки, прогресс скачивания больших файлов.
- *as-built:* минимальный UI + алерты браузера.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Манифест не кэшируется в React Query; повторные скачивания — только по кнопке.
