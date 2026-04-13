# Cross-cutting go-live (публичный периметр, безопасность, наблюдаемость, масштаб)

> **PRC (L3):** см. [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — блоки **C**, **F**, часть **G**, **PRC-B7**, **PRC-I2**.  
> **Единый чеклист релиза:** [RELEASE_CHECKLIST.md](../../operations/RELEASE_CHECKLIST.md).  
> **Детализация §10 и смежных тем:** [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md).

## Назначение

Оглавление ссылок на **сквозные** требования МП — **без** дублирования полного текста МП. DoD: «всё для go-live периметра в одном месте для OPS/SEC/LEAD».

## QA_ARCH: префлайт для @ARCH и приёмка

**Инспектор:** [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **Детализация тем:** [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md). **Образец аудита:** строки **10-Q*** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).

| Этап | Что должно быть зафиксировано |
|------|--------------------------------|
| **Выход @ARCH** | По каждой **строке карты** ниже: периметр (публичный / staff / platform), точки **rate limit**, **webhook B**, **метрики** (имена + запрет высокой cardinality), связь с **RELEASE_CHECKLIST**. Отдельно: план закрытия **PRC-C***, **PRC-F***, **PRC-B7** ссылками на тикеты или срезы **1b-F3**, **1d**, **1b-E6**. |
| **Минимум для @QA_ARCH** | Негативный сценарий на signup/checkout **или** webhook B (один на релиз периметра); подтверждение OPS по Grafana (не в открытой сети без auth) — см. **PRC-F1**. |
| **Красные флаги** | Ссылки в этой таблице есть, а контракт OpenAPI / edge не обновлялись; «antispam позже» без **waiver** LEAD при публичном лендинге; дашборды в репозитории без факта импорта в стенд. |

---

## Карта требований → документы

| Тема МП | Якорь | Куда смотреть |
|---------|--------|----------------|
| Публичный лендинг, CTA, злоупотребления | **§5** C3, C4 | [SAAS_STRENGTHENING_MASTER_PLAN.md](../SAAS_STRENGTHENING_MASTER_PLAN.md); лендинг/маркетинг — [STREAM_FRONTEND_SAAS_EPICS.md](./STREAM_FRONTEND_SAAS_EPICS.md) |
| Периметр webhook B, edge | **§10** | [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md); **PRC-B7** |
| Антиспам, rate limit (сквозное) | **§27** | МП + реализация signup/checkout; **PRC-C1** |
| Коды ошибок, UX ошибок | **§28** | [PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md); **PRC-C3** |
| Cardinality метрик, доступ Grafana, алерты | **§11** M1, M5, M6 | [deploy/prometheus/](../../../deploy/prometheus/); [deploy/grafana/](../../../deploy/grafana/); **PRC-F1–F3** |
| Envelope масштаба | **§31**, **§30** | [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md); [STREAM_PHASE0_AND_GOVERNANCE.md](./STREAM_PHASE0_AND_GOVERNANCE.md) **0-F1** |
| Privacy signup | **§19** п.13, **§2c** C4 | [PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md](../PLATFORM_SIGNUP_PRIVACY_AND_RETENTION.md); **PRC-C2** |
| Реплики API + webhook/signup | **§17.1** | [API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md](../../operations/API_REPLICAS_WEBHOOK_SIGNUP_DECISION.md); **PRC-E1** |
| SLO | §11 + ops | [SLO_CRITICAL_PATHS.md](../../operations/SLO_CRITICAL_PATHS.md); **PRC-G2** |

---

## DoD потока

> **Честность L3:** галочки ниже — **инженерная** готовность кода и доков. Статусы **`satisfied`** в [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) выставляет процесс LEAD + @QA_ARCH по артефактам. **Приёмка среза:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**1b-F3**, **10-Q***).

- [x] В [RELEASE_CHECKLIST.md](../../operations/RELEASE_CHECKLIST.md) отражены пункты, относящиеся к публичному периметру и биллингу (лимиты публичного SaaS, `PUBLIC_RATE_LIMIT_TRUSTED_PROXY_CIDRS`, Celery expire intents).
- [x] Строки **PRC-C***, **PRC-F***, **PRC-B7**, **PRC-G1–G2** в [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) синхронизированы с кодом/алертами (артефакты в матрице; статусы `satisfied` — только после LEAD/QA_ARCH).
- [x] Реализация согласована с **§15b** цикл 4 и [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) (метрики низкой кардинальности, негативные тесты периметра).

---

**Версия:** 2026-04-07.
