# Architecture Decision Records (ADR)

## Почему в каталоге ADR-007…011, а не с 001

Нумерация **007–010** выбрана осознанно: в коде и конфигах **уже зафиксированы** номера **ADR-005** (реплика для reporting) и **ADR-006** (Playwright / браузерный E2E). Чтобы не перезаписывать смысл этих ссылок, новые файлы в `docs/adr/` начали с **007**.

**Файлов ADR-001…004 в этом репозитории сейчас нет** (в истории проекта часть старых ADR могла быть в других путях или удалена при чистке `docs/`).

**ADR-005 и ADR-006** — решения описаны по сути в комментариях к коду, отдельных `.md` в `docs/adr/` для них пока нет:

| ID | Суть | Якоря в репо |
|----|------|----------------|
| ADR-005 | Read replica + `statement_timeout` для reporting GET | `src/infrastructure/database/base.py`, `src/api/v1/dependencies.py`, `src/core/config.py` |
| ADR-006 | Браузерный E2E (Playwright), smoke/regress | `.github/workflows_disabled/e2e.yml`, `frontend/e2e/smoke-public.spec.ts` |

При необходимости можно добавить короткие **ретроспективные** `ADR-005-*.md` / `ADR-006-*.md` со статусом Accepted и ссылками на этот код.

---

Индекс принятых и предлагаемых решений. Статус **Proposed** — требуется ревью @LEAD и реализация по этапам; после внедрения в код помечать **Accepted** и ссылку на PR/миграцию.

| ID | Тема | Файл | Статус |
|----|------|------|--------|
| ADR-007 | Platform multi-tenancy, super-admin, self-service (EN ADR text); **Phase 0:** fork изоляции = Option B для 1a, RLS = цель | [ADR-007-platform-multitenancy-super-admin.md](./ADR-007-platform-multitenancy-super-admin.md) | Proposed (fork зафиксирован 2026-04-05) |
| ADR-008 | Backup, restore, BCP (managed vs docker) | [ADR-008-backup-restore-bcp.md](./ADR-008-backup-restore-bcp.md) | Accepted (partial: logical-export metrics + runbook §8) |
| ADR-009 | Надёжная доставка доменных событий (outbox) | [ADR-009-async-outbox-event-delivery.md](./ADR-009-async-outbox-event-delivery.md) | Accepted (partial: PaymentSuccess / contour A) |
| ADR-010 | Импорт из внешних CRM/ERP: scope v1 | [ADR-010-external-crm-import-scope.md](./ADR-010-external-crm-import-scope.md) | Proposed |
| ADR-011 | Webhook подписки платформы, идемпотентность, провижининг | [ADR-011-platform-subscription-webhook-provisioning.md](./ADR-011-platform-subscription-webhook-provisioning.md) | Accepted (MVP spine; см. шапку ADR) |
| ADR-012 | Возврат / chargeback контура B и жизненный цикл org после «денег назад» | [ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md](./ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md) | Accepted (политика; реализация — бэклог фаз) |
| ADR-013 | Commerce / магазин / 1С — bounded context, мультитенантность, ворота; **доп.** публичная read-model витрины PWA (`GET …/commerce/vitrine`) без отдельного ADR | [ADR-013-commerce-store-bounded-context-scope.md](./ADR-013-commerce-store-bounded-context-scope.md) | Proposed |
| ADR-014 | RAG §24.3: FTS в Postgres, эволюция к векторному retrieval (pgvector vs внешний store) | [ADR-014-rag-retrieval-vectors-and-stores.md](./ADR-014-rag-retrieval-vectors-and-stores.md) | Proposed (фаза FTS/hybrid — в коде) |
| ADR-015 | Вебхуки A/B: 502 при сбое верификации YooKassa для известной локальной оплаты (P0-3) | [ADR-015-webhook-provider-verify-http-semantics.md](./ADR-015-webhook-provider-verify-http-semantics.md) | Accepted |

**Связь:** [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../architecture/TARGET_PLATFORM_MULTITENANCY_REFERENCE.md), [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](../architecture/LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md), [ENTERPRISE_SAAS_RUBRIC.md](../architecture/ENTERPRISE_SAAS_RUBRIC.md).
