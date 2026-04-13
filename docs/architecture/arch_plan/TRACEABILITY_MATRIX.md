# Матрица трассировки: разделы мастер-плана → артефакты

Источник разделов: [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md).

| МП § | Тема | Артефакт(ы) в репозитории | Фаза `arch_plan` |
|------|------|---------------------------|------------------|
| §1 | Роли, изоляция, C5 | [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../TARGET_PLATFORM_MULTITENANCY_REFERENCE.md), [FOUNDER_ACCESS_BREAKGLASS.md](../../operations/FOUNDER_ACCESS_BREAKGLASS.md) | 1a, сквозное |
| §2 | Желаемое vs факт | [ARCHITECTURE_SAAS_MASTER_OVERVIEW.md](../ARCHITECTURE_SAAS_MASTER_OVERVIEW.md), [PRINCIPLE*](../../artifacts/) | 0, обзор |
| §2b | Слои A–F | [PRINCIPLE_SAAS_PLAN_CODE_DEEP_ANALYSIS_2026-04-03.md](../../artifacts/PRINCIPLE_SAAS_PLAN_CODE_DEEP_ANALYSIS_2026-04-03.md) | 0, все фазы |
| §2c–§2d | QA_ARCH циклы | Отчёт ревью МП — в репозитории не заведён; ворота: `docs/LEAD_PRODUCT_GATE_PROTOCOL.md`, журнал [UNRESOLVED_AND_CONFUSION_LOG.md](../UNRESOLVED_AND_CONFUSION_LOG.md) | 1b, ворота |
| §3–§4 | Тарифы, каталог ключей | МП, [LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md](../LEAD_RF_PACKAGES_AND_PRICING_FIRST_LAUNCH.md) | 1b, 1c |
| §3 (периоды оплаты) | Месяц / год на пресете плана; гейт webhook vs каталог | МП §3 п.3, [platform_subscription_billing.md](../modules/platform_subscription_billing.md) §4.3, [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1b-F4–F9**, [05_PHASE_1D](./05_PHASE_1D_OBSERVABILITY.md) п.6 | 1b, 1d |
| §5–§6 | Лендинг, оплата, провижининг | [PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md](../PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md), [platform_subscription_billing.md](../modules/platform_subscription_billing.md) | 1b |
| §7–§8 | Кабинет Основателя, конструктор | Спеки UI (будущие), МП | 1b |
| §9–§10 | 2FA, секреты, кассы B | ADR-007/011, МП | 1a, 1b |
| §11 | Observability | [07_metrics_observability.md](../07_metrics_observability.md), `deploy/prometheus`, `deploy/grafana` | 1d |
| §12–§13 | Box, базовый пакет | [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md) | 1c |
| §14 | Vertical | [05_data_migrations_multitenancy.md](../05_data_migrations_multitenancy.md) | 3 |
| §15–§15b | Дорожная карта, DoD | МП, [RELEASE_CHECKLIST.md](../../operations/RELEASE_CHECKLIST.md), [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (полное vs минимум) | все |
| §15a | P0 security | [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](../LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md), U-* | сквозное |
| §15c | P0 commerce | [ADR-011](../../adr/ADR-011-platform-subscription-webhook-provisioning.md) | 1b |
| §16 | ADR-шаги | [docs/adr/README.md](../../adr/README.md) | по фазам |
| §17–§17.1 | Риски, outbox | [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md) | 1a–2 |
| §18–§19 | Go/no-go | МП, INDEX | 0 |
| §20 | Рубрика | [ENTERPRISE_SAAS_RUBRIC.md](../ENTERPRISE_SAAS_RUBRIC.md) | 0 |
| §24 | Embed / AI / RAG | МП, frontend/backend спеки | 1e |
| §25 | Enterprise import | [modules/data_migration_import_connectors.md](../modules/data_migration_import_connectors.md), ADR-010 | 3 |
| §26 | Commerce | [ADR-013](../../adr/ADR-013-commerce-store-bounded-context-scope.md), [domains/commerce_bounded_context.md](../domains/commerce_bounded_context.md), [09_PHASE_4](./09_PHASE_4_OPTIONAL_COMMERCE.md) | 4 |
| §27–§28 | Антиспам, security metrics | МП, [07_metrics_observability.md](../07_metrics_observability.md) | сквозное |
| §28 (коды API, SaaS) | Единый регистр `code` + контракт 403 после 1c | [04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md) B2/B4, [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) 1c-Q2/Q4, [PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md) | 1c долг → **10** §28, **1e** |
| §29–§30 | Бренд, монолит | МП, i18n | сквозное |
| §31 | Envelope 10k+ | [ROLE_ARCH.md](../../ROLE_ARCH.md) ШАГ 0A, QA_ARCH отчёт | сквозное |

**U-* журнал:** [UNRESOLVED_AND_CONFUSION_LOG.md](../UNRESOLVED_AND_CONFUSION_LOG.md) (МП §2a).

**Эпик-срезы LEAD (DOC-1):** [SAAS_EPIC_TRACEABILITY_INDEX.md](../SAAS_EPIC_TRACEABILITY_INDEX.md) — таблица Epic_ID ↔ МП § ↔ PHASE_FULL_CLOSURE ↔ ADR ↔ `src/` ↔ QA_REPORT; потоки в `STREAM_*_EPICS.md` в этой папке.
