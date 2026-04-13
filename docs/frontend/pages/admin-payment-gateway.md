# Admin Payment Gateway

## Метаданные

- **Path:** `/admin/payment-gateway`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminPaymentGatewayPage`
- **Файл страницы:** `frontend/src/admin/pages/AdminPaymentGatewayPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminPaymentGatewayPage.tsx`<br>`frontend/src/contexts/AdminClinicContext.tsx ← импорт из frontend/src/admin/pages/AdminPaymentGatewayPage.tsx`<br>`frontend/src/shared/emptyStateHint.tsx ← импорт из frontend/src/admin/pages/AdminPaymentGatewayPage.tsx` |
| Строк (сумма по фрагментам) | 487 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useBusinessLexicon`, `useClinics`, `useSetClinicPaymentGatewayCredentials`, `useUpdateClinicMutation` |
| Пути в строках `/v1/...` | — |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Выбор одной платёжной системы на клинику и ввод учётных данных из кабинета провайдера. Для ЮKassa часть полей уходит в общий `PUT` клиники; для остальных шлюзов секреты отправляются отдельным `POST` credentials.

## Логика и данные

- **Хуки:** `useAdminClinic` (`currentClinicId`); `useClinics`, `useUpdateClinicMutation` из `@/hooks/useClinics`; `useSetClinicPaymentGatewayCredentials` из `@/hooks/useAdminPaymentGateway`.
- **queryKey:** список клиник — `queryKeys.clinics.list(...)` (см. `useClinics`).
- **API:**
  - `GET /v1/clinics` — текущая клиника из списка (поля `payment_gateway`, `payment_gateway_custom_name`, `yookassa_shop_id`).
  - `PUT /v1/clinics/{clinicId}` — тип шлюза, кастомное имя, для ЮKassa: `yookassa_shop_id`, опционально `yookassa_secret_key` при непустом вводе.
  - `POST /v1/admin/clinics/{clinicId}/payment-gateway/credentials` — JSON-тело `{ gateway, payload }`, где `payload` — строка с сериализованным объектом полей (Тинькофф, Сбер, Robokassa, Stripe, PayPal, custom); для `yookassa` этот путь в коде не вызывается.

## RBAC / entitlements / edition

- В `SEGMENT_ENTITLEMENT` (`frontend/src/shared/adminEntitlementNav.ts`) для сегмента `payment-gateway` ключа нет (**fact**).
- Прямой гейт по SaaS-entitlement на сегмент не навешан в этой карте.

## UI-скелет (as-built)

Без выбранной клиники: `ContextBar` «Касса» + `EmptyStateHint`. Иначе: `ContextBar` «Платёжный шлюз», поясняющий `Text`, при ошибках — `QueryErrorAlert`, карточка `AdminSettingsSectionCard` с `Select` провайдера и условными `TextInput` по типу, кнопка «Сохранить».

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer, GlassModal, Modal, Menu, Stepper:** на странице нет.
- **Alert / баннеры:** только `QueryErrorAlert` для ошибок сохранения клиники и credentials.

## Целевой UX (target vs as-built)

- *target:* единый безопасный поток настройки кассы, валидация полей, подсказки по webhook/return URL.
- *as-built:* одна форма на все провайдеры; секреты частично через clinic PUT, частично через admin credentials POST; пустой секрет ЮKassa = не менять сохранённый.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Нет явной индикации «какой шлюз сейчас активен» кроме локального состояния после загрузки клиники.
- Удаление/ротация credentials для не-ЮKassa без частичного ввода не отражена в UI (отправка только если есть непустые значения в объекте).
