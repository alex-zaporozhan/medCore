# Журнал неясностей и путаницы

> Пополняется по мере аудита. Формат строки: **вопрос → где смотрели → что проверить**.

**Как это используется:** остальные файлы в `docs/architecture/` утверждают только то, что подтверждено чтением кода или конфигов. Если поведение зависит от окружения, объём кода слишком большой для одного прохода или есть риск побочных эффектов (утечка полей в API), фиксируется здесь строкой таблицы с ID — это часть качества карты, а не «пробел документации».

| ID | Вопрос | Где смотрели | Что проверить / гипотеза |
|----|--------|--------------|---------------------------|
| U-011 | **Закрыто (код 2026-04-05, QA_ARCH; усиление списка 2026-04-05).** Анонимный `GET /api/v1/clinics/{id}` → **404**; анонимный список: **PII scrub**, **rate limit** по IP (`rate_public_clinics_list_*`), только клиники с **непустым `clinic_slug`**, кроме **legacy single-clinic** (ровно одна активная строка в БД — допускается без slug). Админский SPA шлёт Bearer на `/v1/clinics`. | `clinics.py`, `clinic_service.get_clinics_for_unauthenticated_discovery`, `config`, `client.ts` | Регрессии: `test_u011_*`, `test_platform_provisioned_clinic_not_accessible_to_other_admin`. |
| U-010 | Какой первый коннектор импорта (Битрикс24 vs 1С vs CSV-only) и минимальный набор сущностей v1? | [ADR-010](../adr/ADR-010-external-crm-import-scope.md), [modules/data_migration_import_connectors.md](./modules/data_migration_import_connectors.md) | Продуктовое решение; затем эпик в DEV; негативные тесты tenant scope. |
| U-009 | Зафиксированы ли для выбранного прод-окружения retention, PITR, шифрование дампов и факт restore drill? | [ADR-008](../adr/ADR-008-backup-restore-bcp.md), [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md), `docker-compose.yml` | **2026-04-06:** журнал учения §6.1 в DR_RUNBOOK (CI drill). OPS заполняет RPO/RTO в §1 и staging PITR. **Бэклог Phase 2:** [2-F2 (partial), 2-F4](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md). |
| U-008 | Гарантирует ли репозиторий качество поставки без внешнего CI? Основные workflow backend/frontend/e2e/security лежат в `workflows_disabled`. | `.github/workflows/build-and-test-entitlements.yml` (**verify** + **full-backend-tests** `pytest tests/`), `.github/workflows/release-gate.yml`, `.github/workflows_disabled/` | **Политика LEAD (2026-04-06):** [LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md](../artifacts/LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md) — baseline релиза на тегах `v*` + явный waiver для e2e/security до включения. **2-F8** в [PHASE_FULL_CLOSURE](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) — `done`. |
| U-006 | Достаточна ли идемпотентность **контура A** (`PaymentService.handle_webhook`, YooKassa) и отдельно **контура B** (подписка платформы по [ADR-011](../adr/ADR-011-platform-subscription-webhook-provisioning.md))? | `payment_service.py`, `payments` webhook router; контур B — по спеке [modules/platform_subscription_billing.md](./modules/platform_subscription_billing.md) | Тесты двойного webhook и веток статусов для **A**; для **B** — после реализации по §16.6 / U-006 в [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md). |
| U-007 | Нужна ли таблица outbox и воркер для событий вместо только in-process EventBus при целевом масштабировании API? | `domain_outbox`, `domain_outbox_service.py`, `event_bus.py`, ADR-009 | **Частично закрыто в коде:** outbox + Celery для `PaymentSuccess` (контур A). **Бэклог Phase 2:** [2-F1, 2-F5, 2-F7](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (остальные события, тесты redelivery, контур B при multi-replica). |
| U-004 | Как без поломки изоляции по `clinic_id` ввести platform-operator (владелец SaaS) и self-service регистрацию нового бизнеса с отдельным root-tenant? | `Organization`, `AdminUser`, JWT в `admin_auth` | Нужен ADR: новая сущность/claim, RLS или строгие policy в каждом запросе, отдельный admin shell; сейчас такого контура нет. |
| U-005 | Достаточно ли переименовать/документировать `/owner/*`, или нужен отдельный dependency для «сетевого владельца» (несколько клиник)? | `owner_omni_channels.py` (`get_current_admin`, `clinic_id`); **черновик спеки Phase 0:** [specs/OWNER_API_SEMANTICS_U005_DRAFT.md](./specs/OWNER_API_SEMANTICS_U005_DRAFT.md) | LEAD + Product: вариант A (переименование) vs B (сеть клиник); до решения — не расширять `/owner/*`. |
| U-001 | В ответе `GET /health/replica` при ошибке пробы в теле может попадать `error: str(exc)` — утечка деталей наружу? | `src/main.py` `health_replica` | См. [../product_state/RAG_NECESSARY_IMPROVEMENTS.md](../product_state/RAG_NECESSARY_IMPROVEMENTS.md) §1.3; для prod — маскирование или отсутствие поля `error`. |
| U-002 | Полный ли список репозиториев в `infrastructure/database` относительно всех доменных сущностей? | 18 файлов в `src/infrastructure/database/` | Часть доступа к данным может идти через общие сессии в сервисах без отдельного `*_repo_impl`; grep по `AsyncSession` в `application/services`. |
| U-003 | Все ли Celery-задачи из `tasks/*.py` реально ставятся в очередь из API/сервисов? | `src/infrastructure/messaging/tasks/` | Поиск `.delay(` / `apply_async` по `src/`. |

Добавляйте строки сверху таблицы (новый ID) при обнаружении зон, где код прочитан частично или поведение зависит от окружения.

### Enterprise-аудит (честная оценка)

- **Критические риски:** не решены на уровне журнала; фиксируются вопросы U-004–U-010 и в [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) (U-011 перенесён в строку таблицы как **закрытый** с остаточным риском списка).
- **Средние риски:** накопление открытых вопросов без владельца и срока закрытия.
- **Формально / недоделано:** таблица — не трекер задач; для исполнения переносить в бэклог.
- **Рекомендуемые доработки:** закрывать U-* решением в коде или явным «won’t fix» в ADR.

### Соответствие фактам (проверка)

- Строки U-004, U-005 согласованы с чтением `owner_omni_channels.py` и entity `Organization`/`Clinic`. **U-011** закрыт в коде 2026-04-05; остаточный риск — анонимный список клиник (см. ячейку U-011).
- U-006, U-007 добавлены по [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md); U-008 — по [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) (CI/поставка); U-009, U-010 — по пакету ADR и [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md).

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** накопление U-* без владельца превращает архитектуру в «список страхов» без действий.
- **Что усилить:** каждую U-* закрывать ADR или тестом; webhook/outbox — см. U-006, U-007; поставка — U-008; backup/drill — U-009; импорт — U-010.
- **С нуля:** трекер задач вне markdown при росте команды.
- **БД:** вопросы миграций при outbox — в U-007.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md); приёмка LEAD и бэклог: [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).
