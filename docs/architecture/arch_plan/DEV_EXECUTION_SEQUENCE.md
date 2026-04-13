# Последовательность работ для @DEV (от старта к масштабу)

Этот файл — **операционный порядок** поверх фаз. Детали — в `01_…`–`10_…`.  
**Полное закрытие фазы** (сверх минимального DoD в `02_`…`10_`): [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).

## Шаг 0 — до кода platform/SaaS

1. Прочитать [00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md](./00_ARCHITECTURAL_LAYERS_AND_PRINCIPLES.md) и МП **§18–§19**.
2. Убедиться, что зафиксировано решение **§17.1**, если в staging/prod планируется **>1 реплики** API и уже есть или будет публичный webhook **B** / signup.
3. Зафиксировать «go на MVP spine» или ADR риска для уже влитых миграций B (МП **§18 исключение**).

## Два параллельных P0-потока (до платного лендинга)

МП **§15a** (безопасность) и **§15c** (коммерция) **не сливаются** в один тикет без явного разделения ответственности.

| Поток | Примеры задач | Ворота |
|--------|----------------|--------|
| **P0 Security** | U-001 health/replica, B-4 XSS/токены, rate limit на публичные пути, §27–§28 по мере появления поверхностей | §15a, §19 |
| **P0 Commerce** | Завершение контура B: OpenAPI B, ветки webhook, первый Владелец + `organization_entitlements`, retry/DLQ/reconcile; затем **реализация [ADR-012](../../adr/ADR-012-platform-subscription-refund-chargeback-org-lifecycle.md)** (refund/chargeback → отзыв entitlements) — [03_PHASE_1B](./03_PHASE_1B_COMMERCE_AND_UX.md) волна ADR-012 | DoD **§15b 1b**, §16.6 |

## Рекомендуемый порядок фаз (линейный «скелет»)

1. **[01_PHASE_0_PREPARATION.md](./01_PHASE_0_PREPARATION.md)** — ADR, gap, согласование ключей §4 / §16.5, чеклисты.
2. **[02_PHASE_1A_PLATFORM_CORE.md](./02_PHASE_1A_PLATFORM_CORE.md)** — модель Основателя (спека+миграции по ADR-007), граница platform/tenant, `pending_payment` в БД, негативные тесты изоляции.
3. **[03_PHASE_1B_COMMERCE_AND_UX.md](./03_PHASE_1B_COMMERCE_AND_UX.md)** — каталог в БД, UI Основателя/лендинг (эпиками), доведение B до МП §6 (не только Org+Clinic).
4. **[04_PHASE_1C_ENTITLEMENTS.md](./04_PHASE_1C_ENTITLEMENTS.md)** — только после **merge** и приёмки [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md). Долг QA_ARCH сверх минимального DoD 1c (коды ошибок, CI pytest, контракт 403) — [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) §**Фаза 1c** и раздел «Бэклог после merge 1c» в самом `04_`.
5. **[05_PHASE_1D_OBSERVABILITY.md](./05_PHASE_1D_OBSERVABILITY.md)** — можно параллельно с поздней **1a** / **1b**, если не ломает деплой; включая алерты по метрикам **контура B** (webhook платформы, отзыв биллинга ADR-012 — см. п.5–6 в файле фазы).
6. **[06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md)** — offboarding/export документ + продуктовые фичи §24.
7. **[07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md)** — ADR-008/009, CI U-008; усиливает **§17.1**.
8. **[08_PHASE_3_PLUS.md](./08_PHASE_3_PLUS.md)** — vertical, ADR-010, §25.
9. **[09_PHASE_4_OPTIONAL_COMMERCE.md](./09_PHASE_4_OPTIONAL_COMMERCE.md)** — по отдельному go.
10. **[10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md)** — не «после всего»: вшивать в **1b** (лендинг), **1d** (метрики), **все** публичные API.

## Запреты (кратко, МП §17)

- Не расширять `/owner/*` без закрытия **U-005** (спека семантики).
- Не провижинить org только из Redis (МП §6).
- Не публиковать Grafana без auth/VPN (МП §11 M5).
- Не добавлять `security_*` / spam metrics без реестра имён (МП §11, §28).

## Когда просить @ARCH

- Новый публичный маршрут или префикс `/platform/*`.
- Новая миграция, touching platform + tenant в одной транзакции без барьера.
- Изменение модели JWT / claims.
- Любой «десятки тысяч» список без пагинации или отчёт без витрины.
