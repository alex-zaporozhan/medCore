# Эталон: платформа SaaS, мультитенантность и super-owner

> **Статус:** целевая модель (target state). **Текущее состояние кода** — см. [INDEX.md](./INDEX.md), [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).  
> **ADR:** [../adr/README.md](../adr/README.md) (ADR-007 … ADR-011).  
> **Версия:** 2026-04-03

## 1. Зачем этот документ

Зафиксировать **конву-эталон** для позиционирования продукта как **мультиарендаторного SaaS** с оператором платформы (вендор) и самостоятельной регистрацией бизнес-клиентов. Документ не дублирует [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md), а задаёт **куда идём**.

## 2. Слои идентичности

| Слой | Кто | Назначение |
|------|-----|------------|
| **Platform** | Вендор (вы), доверенные сотрудники | Глобальные политики, биллинг самого SaaS, поддержка, аудит, ограниченный доступ к данным тенантов **по процедуре** |
| **Organization (business tenant)** | Юрлицо / ИП — клиент SaaS | Self-service онбординг, владелец бизнеса, подписка/план, создание клиник |
| **Clinic** | Операционная единица | Данные сегодня изолированы прежде всего по `clinic_id` ([`src/domain/entities/clinic.py`](../../src/domain/entities/clinic.py)) |
| **Staff / пользователи клиники** | Врачи, админы ресепшена | RBAC внутри клиники/организации |

## 3. Super-owner платформы: полномочия (эталон)

Все действия — с **аудитом** (кто, когда, на какой organization_id/clinic_id, основание). PII — маскирование по политике.

- **Управление жизненным циклом тенанта:** приостановка/возобновление доступа организации к SaaS; отзыв не оплаченного доступа.
- **Биллинг платформы:** планы, лимиты, metering (см. ось 7 рубрики).
- **Поддержка:** impersonation **только** с журналированием и ограничением по времени (отдельная политика).
- **Данные по запросу:** **логический экспорт** сущностей тенанта (шифрованный архив); не «ssh на прод» без процедуры.
- **Наблюдаемость:** агрегированные ошибки, health тенанта, трассировки с `organization_id` / `clinic_id` в structured logs (после ADR по логам).
- **Отзыв полномочий бизнеса:** не «ломать БД», а **отключить доступ** (JWT, API keys интеграций) и зафиксировать в audit.

Физический **database-per-tenant** — опция только для отдельных enterprise-договоров (ADR-007 fork).

## 4. Self-service регистрация бизнеса

1. Регистрация организации (email, юрданные по необходимости).
2. Подтверждение и создание первого **organization owner**.
3. Создание первой клиники и приглашение админов.
4. Все API и фоновые задачи обязаны знать **tenant context** (organization + clinic).

## 5. Инженерные опоры (связь с ADR)

- **Изоляция:** RLS или усиленный policy-слой — [ADR-007](../adr/ADR-007-platform-multitenancy-super-admin.md).
- **События и масштаб API:** outbox — [ADR-009](../adr/ADR-009-async-outbox-event-delivery.md).
- **Backup / DR:** [ADR-008](../adr/ADR-008-backup-restore-bcp.md), [09_backup_restore_bcp.md](./09_backup_restore_bcp.md), [../operations/DR_RUNBOOK.md](../operations/DR_RUNBOOK.md).
- **Импорт CRM:** [ADR-010](../adr/ADR-010-external-crm-import-scope.md), [modules/data_migration_import_connectors.md](./modules/data_migration_import_connectors.md).
- **Подписка платформы (webhook, провижининг):** [ADR-011](../adr/ADR-011-platform-subscription-webhook-provisioning.md), [modules/platform_subscription_billing.md](./modules/platform_subscription_billing.md).

## 6. Монолит и масштаб

Целевая топология на горизонте 1k–100k организаций: **модульный монолит** API + горизонтально масштабируемые **Celery**-воркеры + **PostgreSQL** (реплика чтения, при росте — партиционирование) + **Redis** с HA. Отдельные сервисы — только при доказанном SLO-узком месте (см. план Platform SaaS).

## 7. Соответствие рубрике и трекеру 8W

- [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md) — оси 1–2, 6, 11–12.
- [STREAM_PRODUCTION_READINESS.md](./arch_plan/STREAM_PRODUCTION_READINESS.md), [PHASE_FULL_CLOSURE_BACKLOG.md](./arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) — операционные KPI и долг сверх DoD.

## 8. Связанные документы

- [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md) — U-004, U-009, U-010.
- [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) — текущие риски транзакций и БД.
