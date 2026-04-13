# Решение приоритета: первый крупный код после DOC-1 / OBS-1 (1a-E2 vs 1b-E2)

> **Роли:** утверждает **@LEAD**; **@ARCH** фиксирует последствия для миграций, JWT и **§17.1**.  
> **Источник:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](./LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md), [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) **§18**, **§17.1**, **§2d**.

## Контекст

- В коде уже есть **MVP spine контура B** (webhook YooKassa B, таблицы intent/payment, Org+Clinic, идемпотентность happy path) — см. МП **§16.6** статус шагов и [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](./ARCHITECTURE_SAAS_MASTER_OVERVIEW.md) §1c.
- **1b-E2 (провижининг §6):** закрыт по DoD среза — см. [QA_REPORT_1b_E2_provision.md](../artifacts/QA_REPORT_1b_E2_provision.md); публичный self-service checkout (**1b-E1** / **1b-F5**) остаётся открытым.
- **1a-E2** (platform-operator в БД, JWT/realm Основателя): **done** — см. [QA_REPORT_1a_E2_platform_user.md](../artifacts/QA_REPORT_1a_E2_platform_user.md); открыты **1a-E3…E5** (2FA, audit, RLS fork).

Обе линии законны; выбор влияет на честность формулировок «SaaS готов» и на **§19**.

## Рекомендация @ARCH (не замена решения LEAD)

**По умолчанию** для согласованности идентичности и ворот **§19 п.3** (JWT Основатель vs тенант): начинать с **1a-E1** (спека) + **1a-E2** (platform user + выдача токена) **до** масштабирования публичного self-service и кабинета Основателя.

**Исключение:** если бизнес-приоритет — быстрее продать первый платный поток на существующем B без отдельного login Основателя в UI, LEAD может выбрать **1b-E2** первым при **всех** условиях ниже.

## Обязательная запись при любом выборе

1. **§17.1:** если планируется `replicas(API) ≥ 2` с публичным webhook B и/или signup — зафиксировать в [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) один из путей: outbox на hot-path / одна реплика для приёма B / ADR риска с датой пересмотра.
2. **§18:** любое расширение platform-миграций без полного ADR-007 — тикет или ADR риска «MVP spine до даты X» (МП **§2d** п.1).

## Решение LEAD (заполнить)

| Поле | Значение |
|------|----------|
| Дата | 2026-04-06 |
| Выбранный первый крупный срез | `1a-E2` после закрытия **1a-E1** (рекомендация ARCH: сначала идентичность JWT §19 п.3, затем полный провижининг **1b-E2**) |
| Обоснование (одна фраза) | Избежать расхождения «любой sub в founder-JWT» и кабинета Основателя; платформа-оператор в БД — база для 2FA (**1a-E3**). |
| Подпись | LEAD (рабочее значение по умолчанию из execute_saas_epic_slices plan) |

## Следующий утверждённый срез после закрытия 1a-E2

| Поле | Значение |
|------|----------|
| Дата | 2026-04-06 |
| Срез | **1b-E2** — провижининг контура B: org/clinic, **`organization_entitlements`** из `tariff_snapshot`, owner invite → accept |
| Статус исполнения | **done** по минимальному DoD [STREAM_1B_COMMERCE_EPICS.md](./arch_plan/STREAM_1B_COMMERCE_EPICS.md); отчёт [QA_REPORT_1b_E2_provision.md](../artifacts/QA_REPORT_1b_E2_provision.md) |
| Параллельно (поток 1a) | **1a-E3** (2FA Основателя) — следующий срез [STREAM_1A_PLATFORM_EPICS.md](./arch_plan/STREAM_1A_PLATFORM_EPICS.md) |

После заполнения обновить строку в [SAAS_EPIC_TRACEABILITY_INDEX.md](./SAAS_EPIC_TRACEABILITY_INDEX.md) (колонка примечание или отдельный changelog) при желании.

## Исполнение (зафиксировано при закрытии дорожной карты плана)

| Дата | Решение |
|------|---------|
| 2026-04-06 | Последовательность реализации: **1a-E3 → 1a-E4 → 1a-E5** (SEC / platform spine), затем закрытие **1b-E1** и **1b-E3** в том же цикле (согласовано с рекомендацией ARCH: сначала идентичность и ворота Основателя, затем углубление контура B). |

---

**Версия:** 2026-04-06.
