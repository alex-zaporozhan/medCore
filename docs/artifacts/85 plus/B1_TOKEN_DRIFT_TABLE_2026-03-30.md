# B1_TOKEN_DRIFT_TABLE_2026-03-30

> Цель: закрыть DoD B1 по таблице `current -> target token` и зафиксировать остаточный drift после B2/B3.

## Проверенный scope

- `frontend/src/admin/pages/*` (P0 + P1 экраны)
- `frontend/src/admin/layouts/AdminLayout.tsx`
- `frontend/src/shared/*` (chat chrome / semantic palette)

## Таблица отклонений и фиксов

| Area | Current | Target token / semantic | Статус |
|---|---|---|---|
| `AdminLayout` content wrapper | `bg="#ffffff"` | Mantine body surface / `var(--mantine-color-body)` | Fixed |
| `AdminOmniChatPage` composer bg | `bg="white"` | `var(--mantine-color-body)` | Fixed |
| `AdminReportsPage` attribution table | ad-hoc table props | `ADMIN_TABLE_PROPS` + `AdminDataTableSurface` | Fixed |
| `AdminTasksPage` list/empty/audit cards | ad-hoc `Card` | `AdminDataTableSurface` | Fixed |
| `AdminChatPage` bubbles | inline bg color rules | `adminChatChrome` shared styles | Fixed |
| `AdminStaffChatPage` bubbles | card-based per-message style | `adminChatChrome` shared styles | Fixed |
| `AdminOmniChatPage` bubbles | inline bubble style matrix | `adminChatChrome` omni helpers | Fixed |
| `AdminPaymentGatewayPage` settings blocks | ad-hoc `Paper` shell | `AdminSettingsSectionCard` | Fixed |
| `AdminIntegrationsPage` settings blocks | ad-hoc `Card` shell | `AdminSettingsSectionCard` | Fixed |
| `AdminAiSettingsPage` sections | ad-hoc `Paper` shell | `AdminSettingsSectionCard` | Fixed |
| `AdminOmniAiSettingsPage` sections | ad-hoc `Paper` shell | `AdminSettingsSectionCard` + `ADMIN_TABLE_PROPS` | Fixed |

## Остаточный drift (допустимый)

1. `AdminStylingPage` содержит hex как демонстрацию токенов (дизайн-инвентарь), не runtime drift.
2. Unit-test файлы могут содержать тестовые цвета (`__tests__`), на product UI не влияет.

## Вердикт B1

- Для P0/P1 runtime экранов новый drift по запрещенным hex не внесен.
- B1 DoD по token mapping table закрыт (код + эта таблица).
