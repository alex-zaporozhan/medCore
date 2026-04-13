# Phase 0 и управление корпусом МП (LEAD / ARCH / QA_ARCH)

> **PRC (L3):** см. [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — **PRC-G1**, перекрёстные ссылки на envelope и честность плана.  
> **МП:** [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md) — **§23** (целостность), **§17** (формулировки), **§19** (ворота).

## Назначение

Один поток для того, что **не** привязано к одной фазе 1a–1e, но блокирует честное объявление масштаба и согласованности документов: envelope, crash-review, индексы, владельцы U-*.

## QA_ARCH: префлайт для @ARCH и приёмка

**Инспектор:** [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **Playbook:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md).

| Этап | Что должно быть зафиксировано |
|------|--------------------------------|
| **Выход @ARCH до «go» на код по корпусу** | Таблица **несоответствий** INDEX ↔ TARGET ↔ RUBRIC (или явное «нет расхождений» с датой); для **0-F1** — численные допущения envelope согласованы с [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md) / TARGET; для **U-*** — один экран/документ с owner и критерием закрытия. |
| **Минимум для @QA_ARCH** | Артефакт **0-F2** (crash-review): ссылка на файл/тикет; для **0-F3** — выборочная проверка 3–5 перекрёстных ссылок МП → модули → STREAM без 404. |
| **Красные флаги** | Обновление МП без правки [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md); envelope без подписи LEAD при заявлении **PRC-G1**; отсутствие владельца на **U-006/U-008/U-009**. |

---

## Phase 0 — артефакты

| ID | Содержание | Владелец | Статус / артефакт |
|----|------------|----------|-------------------|
| **0-F1** | Envelope §31: числа, сценарий нагрузки, допущения | LEAD + ARCH | [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md) или TARGET; строка **PRC-G1** в [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) |
| **0-F2** | LEAD crash-review: TARGET + рубрика | LEAD | Ворота **§19 п.4**; фиксация в QA_ARCH или отдельной заметке по согласованию |
| **0-F3** | Синхронизация **INDEX** / **TARGET** / **RUBRIC** | LEAD + ARCH | [INDEX.md](../INDEX.md), [ENTERPRISE_SAAS_TARGET.md](../ENTERPRISE_SAAS_TARGET.md), [ENTERPRISE_SAAS_RUBRIC.md](../ENTERPRISE_SAAS_RUBRIC.md) без противоречий **§2b** |

---

## U-* журнал и владельцы

| U-* | Тема | Типичный owner | Где закрывается |
|-----|------|----------------|-----------------|
| **U-006** | Webhook A/B, идемпотентность, провижининг | Product epic-owner + SEC + DEV | [STREAM_1B_COMMERCE_EPICS.md](./STREAM_1B_COMMERCE_EPICS.md), **PRC-B*** |
| **U-008** | Политика CI для релиза | ARCH + DEV | [STREAM_PHASE2_RELIABILITY_EPICS.md](./STREAM_PHASE2_RELIABILITY_EPICS.md) **2-E3**, **PRC-E4** |
| **U-009** | DR drill | OPS + ARCH | [DR_RUNBOOK.md](../../operations/DR_RUNBOOK.md), **PRC-E2** |

Новые U-* добавлять в этот раздел и в [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md).

---

## Связь с §23 (целостность мастер-плана)

При изменении МП:

- проверить перекрёстные ссылки на модули, ADR, **§15b**, **§19**;
- обновить [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md) и при необходимости строки **PHASE_FULL_CLOSURE** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md);
- не заявлять L3 без сверки с [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md).

**Ритуал срезов:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md).

---

## Приёмка QA_ARCH (инженерная)

- Отчёт: [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](../../artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md), [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**0-F***).  
- Автоматизация: `scripts/phase0_governance_preflight.py` (`envelope` \| `doc-paths` \| `crash-review` \| `all`).  
- **Решения LEAD (закрытие 0-Q1…0-Q3, 0-F2, 0-F3):** [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](../../artifacts/LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md).  
- Статусы в матрице: [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) — секция «Фаза 0».

---

**Версия:** 2026-04-06 — LEAD Phase 0 closure; QA_ARCH блок прежний.
