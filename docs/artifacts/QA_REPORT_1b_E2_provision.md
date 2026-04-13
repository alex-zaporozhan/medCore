# QA_REPORT: срез 1b-E2 — провижининг контура B после оплаты

**Дата:** 2026-04-06  
**Epic:** 1b-E2  
**STREAM:** [STREAM_1B_COMMERCE_EPICS.md](../architecture/arch_plan/STREAM_1B_COMMERCE_EPICS.md)  
**Статус:** закрыт по минимальному DoD среза (код + pytest)

## DoD (из STREAM_1B)

- Провижининг: первый владелец (invite), **`organization_entitlements`** из `tariff_snapshot`, не сценарий «только Org+Clinic».
- E2E happy path после `paid` (webhook B → provision → при необходимости accept invite).

## Факты реализации

| Элемент | Где |
|---------|-----|
| Ядро провижининга | `execute_platform_provision` в [platform_billing_service.py](../../src/application/services/platform_billing_service.py): `Organization`, `Clinic`, `resolve_entitlement_keys_for_intent` → `_replace_org_entitlements`, `_provision_owner_invite` (owner `AdminUser` + invite hash) |
| Идемпотентность | Повтор при `active` + `organization_id` — no-op |
| Owner path | Mint invite: platform internal; accept: [public_platform_owner_invite.py](../../src/api/v1/routers/public_platform_owner_invite.py) |

## Тесты (доказательства)

- `tests/api/test_platform_billing.py::test_platform_billing_writes_organization_entitlements` — строки `organization_entitlements` после успешного webhook и ключи из snapshot.
- `tests/api/test_platform_billing.py::test_platform_owner_invite_mint_and_accept` — полный путь paid → provision → mint invite (founder JWT) → accept → admin login.

## Остаточные риски / не входит в срез

- **1b-E1** (публичный checkout с лендинга), **1b-F5** — по-прежнему открыты; snapshot в тестах задаётся явно.
- **1b-F6** (retry vs гейт каталога), **§17.1** multi-replica — см. [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md), [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md).

## Связь с backlog

- Строка **1b-F1** («полный провижининг §6 …») закрывается вместе с приёмкой этого среза при трактовке ядра как Org + Clinic + entitlements + первый владелец через invite; продуктовый лендинг/checkout — отдельные F5/F3.
