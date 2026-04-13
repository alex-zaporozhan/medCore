# Admin Loyalty

## Метаданные

- **Path:** `/admin/loyalty`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminLoyaltyPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminLoyaltyPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminLoyaltyPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminLoyaltyPage.tsx`<br>`frontend/src/api/types.ts ← импорт из frontend/src/admin/pages/AdminLoyaltyPage.tsx`<br>`frontend/src/config/edition.ts ← импорт из frontend/src/admin/pages/AdminLoyaltyPage.tsx` |
| Строк (сумма по фрагментам) | 1387 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useCustomerSubscriptions`, `useLoyaltyCampaignSettings`, `useLoyaltyPackages`, `useRunLoyaltyCampaigns`, `useUpdateLoyaltyCampaignSettings`, `useWalletTransactions`, `useWallets` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Просмотр пакетов абонементов и абонементов пациента по `patient_id`; во вкладке «Лояльность» (не Box) — кошельки, транзакции по выбранному кошельку и настройки/запуск автокампаний лояльности (задачи LOYALTY_*). Параметры вкладок синхронизируются с query string (`tab`, `patient_id`).

## Логика и данные

- **Хуки:** `useLoyaltyPackages`, `useCustomerSubscriptions`, `useWallets`, `useWalletTransactions`, `useLoyaltyCampaignSettings`, `useUpdateLoyaltyCampaignSettings`, `useRunLoyaltyCampaigns` (`frontend/src/hooks/useLoyalty.ts`); `useAdminClinic` для `clinicId` (блокировка экрана без клиники).
- **queryKey (основные):** `["admin","loyalty","packages"]`, `["admin","loyalty","customer-subscriptions", patientId, onlyActive]`, `["admin","loyalty","wallets", patientId]`, `["admin","loyalty","wallet-transactions", walletId]`, `["admin","loyalty","campaign-settings"]`.
- **Мутации:** `PATCH /v1/admin/loyalty/campaign-settings`; `POST /v1/admin/loyalty/campaigns/run` (после успеха инвалидация `["admin","tasks"]` и campaign-settings).
- **API:** `GET /v1/admin/loyalty/packages`; `GET /v1/admin/loyalty/customer-subscriptions?...`; `GET /v1/admin/loyalty/wallets?patient_id=...`; `GET /v1/admin/loyalty/wallets/{id}/transactions`; `GET|PATCH /v1/admin/loyalty/campaign-settings`; `POST /v1/admin/loyalty/campaigns/run`. (Пациентские `/v1/patient/loyalty/*` на этой странице не вызываются.)

## RBAC / entitlements / edition

- **`adminShellSegmentEntitlementKey`:** для сегмента `loyalty` в `SEGMENT_ENTITLEMENT` записи нет (**fact** — гейт только через RBAC бэкенда и видимость пункта меню).
- **Box:** `isBoxEdition()` скрывает вкладку «Лояльность» и при `?tab=loyalty` принудительно переключает на `subscriptions` (`useEffect` + `setSearchParams`).
- Без выбранной клиники в шапке — короткое сообщение вместо основного UI.

## UI-скелет (as-built)

`ContextBar` → при загрузке `PageSkeleton` → верхний `Tabs` (Абонементы / Лояльность): внутри вложенные `Tabs` и `Card` с `Table`, фильтры `TextInput` по `patient_id`, блок кампаний с `Switch`, `NumberInput`, кнопки «Сохранить настройки» и «Запустить кампании сейчас», `QueryErrorAlert` на ошибки мутаций.

## Инвентарь поверхностей UI (ось H)

- **`AdminDrawer` / `GlassModal` / `Modal`:** на странице нет.
- **Клики по строкам:** выбор кошелька подсвечивает строку и подгружает транзакции.

## Целевой UX (target vs as-built)

- *target:* единый поиск пациента, детальный drawer по абонементу/кошельку.
- *as-built:* только таблицы и фильтр по UUID; кампании — один большой блок настроек без мастера.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- `useLoyaltyCampaignSettings(clinicId)` включает запрос по `clinicId`, но URL кампаний **без** `clinic_id` в path — поведение целиком на стороне API/токена (**зафиксировать при аудите мультитенанта**).
- В `campaignDraft` поле `channel_omnichannel_enabled` уходит в `updateCampaignSettings.mutate`, отдельного `Switch` в UI нет — редактирование только через значение с бэкенда (**gap** UX).
- Пакеты абонементов только на чтение в UI («добавьте через админку или API»).
