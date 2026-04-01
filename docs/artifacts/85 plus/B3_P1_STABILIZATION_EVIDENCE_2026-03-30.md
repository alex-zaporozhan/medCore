# B3_P1_STABILIZATION_EVIDENCE_2026-03-30

> Сводка выполнения P1-бэклога (`DESIGN_P0_P1_BACKLOG.md`) на дату 2026-03-30.

## DGN-P1-01 CRM/Pipeline visual standard

- Обновлены `AdminSalesPipelinePage`, `AdminMarketingPage`, `AdminRetentionPage`:
  - унифицированы section surface/toolbar shells,
  - таблицы переведены на `ADMIN_TABLE_PROPS`,
  - reduced локальный visual drift по карточкам и панелям.

## DGN-P1-02 Settings form contract

- Добавлен shared компонент `AdminSettingsSectionCard`.
- На него переведены:
  - `AdminPaymentGatewayPage`
  - `AdminIntegrationsPage`
  - `AdminAiSettingsPage`
  - `AdminOmniAiSettingsPage`

## DGN-P1-03 Omni and chat convergence

- Добавлен `adminChatChrome` shared слой.
- `AdminChatPage`, `AdminStaffChatPage`, `AdminOmniChatPage` используют единые bubble semantics и message region marker.

## DGN-P1-04 Finance/Reports numeric readability

- `AdminReportsPage` и связанные таблицы используют единый `ADMIN_TABLE_PROPS`.
- KPI/table reading приведены к более консистентной ERP-style плотности.

## DGN-P1-05 Box/Enterprise UX integrity

- Проверен edition gate (`src/config/edition.ts`) для Box:
  - сегменты `retention` и `sales` закрыты в Box edition server/client policy.
- Сняты ложные affordances на скрытых box-only сегментах через существующие route/sidebar guard rules.
- Зафиксировано соответствие с `BOX_PACKAGE_CONTRACT.md` (scope boundaries).

## PWA stabilization (в контуре B3 качества)

- Добавлены install-compatible icons:
  - 192, 512, 512 maskable PNG
  - `apple-touch-icon.png`
- Добавлены manifest screenshots (booking/chat).
- Обновлен web manifest (icons/screenshots/metadata), `index.html` и update flow в patient shell.

## Вердикт B3

- P1 code-level stabilization завершена.
- Рекомендуемый следующий gate: объединить этот файл + B2 evidence в release evidence pack (`C1`).
