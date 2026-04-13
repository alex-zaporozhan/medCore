# QA_ARCH — отчёт SaaS Phase 0 (D0 / SaaS-P0-D0)

> **Канон:** [LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md](../architecture/LEAD_SAAS_SWITCH_PLAN_MODE_PHASE_0.md) DoD **D0.1–D0.5**. Дата: **2026-04-05**.

## Резюме

| Критерий | Оценка | Комментарий |
|----------|--------|-------------|
| D0.1 §2b план↔код | 🟡 | Расхождения по-прежнему в U-* и LEAD-доках; не спорят с фактом репо при чтении ADR-011 / кода B. |
| D0.2 ADR-007…011 / §16 / §2d | 🟢 | ADR-011 шапка = MVP spine; §16.6 шаги 3–4 открыты; ADR-007 дополнен fork Phase 0 (см. ниже). |
| D0.3 §17.1 | 🟢 | Запись: [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) + чеклист релиза. |
| D0.4 INDEX / обзор | 🟢 | Навигация дополнена ссылками на sequence Phase 0 и §17.1. |
| D0.5 честность §2b–§2d / §19 | 🟡 | Публичный платный лендинг и полный §16.6 **не** заявлены; ворота §19 частично закрыты документами, не кодом. |

**Вердикт для LEAD:** документальный **go на подготовку к первому кодовому срезу 1a** при условии соблюдения [DEV_EXECUTION_SEQUENCE.md](../architecture/arch_plan/DEV_EXECUTION_SEQUENCE.md) (без новых platform-миграций без §18).

## §2b / §2c / §2d (кратко)

- **Контур B:** в коде есть; **не** полный продукт (владелец, entitlements, OpenAPI B, retry/reconcile).
- **Контур A:** отдельный webhook; идемпотентность A — отдельная линия тестов (U-006).
- **§17.1:** зафиксировано операционное **interim** (singleton приём до outbox).

## §19 — что остаётся открытым документами vs кодом

- Privacy signup, rate limit публичных путей, 2FA Владельца — ворота мастер-плана, не полный код.
- Инвентарь entitlement ↔ роутер — до приёмки перед 1c.

## Ссылки на новые/обновлённые артефакты

- [WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md](./WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md)
- [ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md](../architecture/ENTITLEMENT_KEYS_PHASE0_ALIGNMENT.md)
- [OWNER_API_SEMANTICS_U005_DRAFT.md](../architecture/specs/OWNER_API_SEMANTICS_U005_DRAFT.md)

---

## Ревизия QA_ARCH по качеству среза @DEV (цикл 2, 2026-04-05)

### Критические риски (было упущено или недоговорено)

| Риск | Было | Сделано |
|------|------|---------|
| Публичное **`GET /api/v1/clinics/{id}`** / PII в анонимном списке | Закрыто в коде 2026-04-05 | [U-011](../architecture/UNRESOLVED_AND_CONFUSION_LOG.md): 404 без admin на GET by id; scrub PII в списке; `client.ts` шлёт admin token на `/v1/clinics`; тесты `test_u011_*`, обновлённый `test_platform_billing` |
| §17.1 документ назван «каноном» без явного LEAD/OPS | Средний риск ложного чувства закрытости | В [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md) добавлена таблица **Статус записи (governance)** |

### Средние риски

| Риск | Мера |
|------|------|
| Аудит A vs B с неточным путём контура A | Исправлен на `POST /api/v1/payments/webhook` в [WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md](./WEBHOOK_PAYMENT_CONTOURS_A_VS_B_AUDIT.md) |
| Дублирование setup в тестах контура B | Рефакторинг: общие `_insert_intent_and_payment`, `_fake_yookassa_class` в `test_platform_billing.py` |
| Тест изоляции проверял только один admin-маршрут | Оставлено как минимум DoD 1a; расширение — матрица `admin/clinics/{id}/*` отдельным эпиком |

### Формально / слабые места (осознанно)

- **ENTITLEMENT_KEYS_PHASE0_ALIGNMENT** — копия МП без отдельной верификации LEAD в тикете; назначение — трассировка, не контракт с биллингом.
- **QA_REPORT D0** — не заменяет прогон pytest в CI; при `pytest.skip` из-за БД зелёный прогон локально не гарантирует приёмку.
- **ADR-007** остаётся **Proposed** по объёму; зафиксирован только fork изоляции Phase 0.

### Рекомендации на следующий спринт

1. ~~**Опционально:** сузить анонимный `GET /clinics`~~ — сделано: slug-фильтр при N>1, rate limit, seed со slug (`conftest`).
2. Прогнать `tests/api/test_platform_billing.py` и `test_stage1_universal_business.py` в среде с БД (не skip) перед merge.
3. OPS: заполнить поле подтверждения в §17.1 при первом multi-replica деплое с webhook B.
