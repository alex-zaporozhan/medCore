# Отчёт: исполнение усилений 1a-E2 (platform founder) и консолидация артефактов QA_ARCH

**Дата:** 2026-04-06  
**Исходный разбор:** пост-срезовый обзор 1a-E2 (вердикт, риски, усиления кода и доков).  
**Роль процесса:** @QA_ARCH / приёмка среза **1a-E2**; строка **1a-F1** в [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) — **done**.

## Вердикт (без изменения смысла)

Минимальный DoD **1a-E2** выполнен: таблица `platform_founder_users`, `POST /api/v1/platform/auth/login`, резолв `sub` в БД на Bearer-маршрутах, негативы для чужих JWT и неизвестного `sub`, seed в pytest, bootstrap-скрипт. Продуктовый путь доступа — **логин**; mint JWT в тестах — не штатная выдача в эксплуатации.

## Код (зафиксировано в репозитории)

| Требование из разбора | Реализация |
|------------------------|------------|
| **503** при `APP_ENV=production` и пустом `PLATFORM_FOUNDER_JWT_SECRET` на логине | `is_platform_founder_jwt_configured()` + `HTTP 503` в `platform_founder_login` / `platform_founder_login_mfa` ([`src/core/security.py`](../../src/core/security.py) `resolve_platform_founder_jwt_signing_key`). |
| Сквозной тест **login → Bearer →** `GET .../platform/internal/health` | `test_platform_founder_login_token_valid_for_internal_health` в [`tests/api/test_platform_internal.py`](../../tests/api/test_platform_internal.py). |
| Тест 503 на **internal health** при том же условии | `test_platform_internal_503_in_production_when_founder_secret_unset`. |
| Rate limit на логине | Per-IP: FastAPI-dependency [`require_platform_founder_login_ip_rate_limit`](../../src/api/v1/dependencies.py). Per-email: после разбора тела в [`platform_founder_auth.py`](../../src/api/v1/routers/platform_founder_auth.py) (`RATE_PLATFORM_FOUNDER_LOGIN_*` в [`settings`](../../src/core/config.py)). |
| OpenAPI | Для `POST /platform/auth/login` и `POST /platform/auth/login/mfa` добавлены `responses` **401 / 429 / 503**. |

## Документы (навигация после удаления scratch `QA_ARCH_*.md`)

- Блок **1a-E2 / усиления** и закрытие потока **1a** — [STREAM_1A_PLATFORM_EPICS.md](../architecture/arch_plan/STREAM_1A_PLATFORM_EPICS.md), [02_PHASE_1A_PLATFORM_CORE.md](../architecture/arch_plan/02_PHASE_1A_PLATFORM_CORE.md), [SAAS_EPIC_TRACEABILITY_INDEX.md](../architecture/SAAS_EPIC_TRACEABILITY_INDEX.md).
- Справочно для фронта: [STREAM_FRONTEND_SAAS_EPICS.md](../architecture/arch_plan/STREAM_FRONTEND_SAAS_EPICS.md) (контракт `login` / `login/mfa` / `totp/*`).
- Отчёт приёмки среза (тесты, границы API): [QA_REPORT_1a_E2_platform_user.md](./QA_REPORT_1a_E2_platform_user.md).

## Приложение A — шаблон evidence L3 (staging)

Использовать после [OPS_L3_PRODUCTION_GATE_CHECKLIST.md](../operations/OPS_L3_PRODUCTION_GATE_CHECKLIST.md). Ссылки на тикеты OPS/LEAD обязательны для перевода строк PRC в `satisfied`.

**Среда:** staging  
**Дата прогона:** YYYY-MM-DD  
**Исполнитель @QA_ARCH:** _имя_

### OPS (ссылки)

| Пункт | Тикет / заметка | OK |
|-------|-----------------|----|
| ASM / секреты | | ☐ |
| Edge WAF webhook B | | ☐ |
| §17.1 (если replicas≥2) | | ☐ |
| Grafana auth / сеть | | ☐ |
| DR RPO/RTO §1 (если обновляли) | | ☐ |

### Публичный контур B / SaaS

| Сценарий | Результат (кратко) | OK |
|----------|-------------------|----|
| `GET /api/v1/public/platform/catalog/plans` — 200, валидный JSON | | ☐ |
| `POST /api/v1/public/platform/signup/checkout` — happy path или ожидаемая 503 без YooKassa | | ☐ |
| При включённом Turnstile — 403 `captcha_required` без токена | | ☐ |

### Кабинет Основателя / MFA

Чеклист: [LEAD_PLATFORM_FOUNDER_MFA_UX_CHECKLIST.md](./LEAD_PLATFORM_FOUNDER_MFA_UX_CHECKLIST.md).

| Сценарий | OK |
|----------|----|
| H2-1 … | ☐ |
| H2-2 … | ☐ |

### Алерты (1d)

| Сигнал | Доставка (Alertmanager / Telegram / webhook) | OK |
|--------|-----------------------------------------------|----|
| Тестовое срабатывание или реальный порог на staging | | ☐ |

### Итог

- **Готово к обновлению матрицы PRC:** да / нет  
- **Замечания:** _текст_

---

## Приложение B — замена удалённых файлов `docs/artifacts/QA_ARCH_*.md`

Одноимённые scratch-отчёты удалены как устаревшая история; якоря перенесены на планы, `QA_REPORT_*`, ADR и код.

| Удалённый файл | Куда смотреть вместо него |
|----------------|---------------------------|
| QA_ARCH_1a_E2_EXECUTION_REVIEW_* | Этот отчёт; [QA_REPORT_1a_E2_platform_user.md](./QA_REPORT_1a_E2_platform_user.md) |
| QA_ARCH_STREAM_1A_CLOSURE_* / QA_ARCH_STREAM_1A_REVIEW_* | [STREAM_1A_PLATFORM_EPICS.md](../architecture/arch_plan/STREAM_1A_PLATFORM_EPICS.md), [ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md](../architecture/arch_model/ARCH_MODEL_STREAM_1A_PLATFORM_E1_E6_FULL_STACK.md), QA_REPORT 1a-E* |
| QA_ARCH_PHASE_1A_PLATFORM_CORE_REVIEW_* | [02_PHASE_1A_PLATFORM_CORE.md](../architecture/arch_plan/02_PHASE_1A_PLATFORM_CORE.md) |
| QA_ARCH_PHASE0_GOVERNANCE_* | [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](./LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md), [STREAM_PHASE0_AND_GOVERNANCE.md](../architecture/arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md) |
| QA_ARCH_1B_CONTOUR_B_* | [QA_REPORT_1b_E3b_webhook_contract.md](./QA_REPORT_1b_E3b_webhook_contract.md), [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md) |
| QA_ARCH_CROSS_CUTTING_GO_LIVE_* | [STREAM_CROSS_CUTTING_GO_LIVE.md](../architecture/arch_plan/STREAM_CROSS_CUTTING_GO_LIVE.md), [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](../architecture/arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md), [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) |
| QA_ARCH_STREAM_FRONTEND_SAAS_* | [STREAM_FRONTEND_SAAS_EPICS.md](../architecture/arch_plan/STREAM_FRONTEND_SAAS_EPICS.md) |
| QA_ARCH_PHASE_10_* | [10_CROSS_CUTTING_*.md](../architecture/arch_plan/10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md), [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) (строки **10-Q***), [ROLE_QA_ARCH.md](../ROLE_QA_ARCH.md) |
| QA_ARCH_PHASE_2_* / ADR-009 ссылка | [07_PHASE_2_RELIABILITY.md](../architecture/arch_plan/07_PHASE_2_RELIABILITY.md), [STREAM_PHASE2_RELIABILITY_EPICS.md](../architecture/arch_plan/STREAM_PHASE2_RELIABILITY_EPICS.md), ADR-008/009 |
| QA_ARCH_PHASE_3_PLUS_* | [08_PHASE_3_PLUS.md](../architecture/arch_plan/08_PHASE_3_PLUS.md) |
| QA_ARCH_PHASE_4_COMMERCE_* | [09_PHASE_4_OPTIONAL_COMMERCE.md](../architecture/arch_plan/09_PHASE_4_OPTIONAL_COMMERCE.md) |
| QA_ARCH_PHASE_1E_EMBED_* / QA_ARCH_STREAM_1E_PHASE3_* | [06_PHASE_1E_LIFECYCLE_EMBED.md](../architecture/arch_plan/06_PHASE_1E_LIFECYCLE_EMBED.md) |
| QA_ARCH_RAG_24_* / ADR-014 | [STREAM_PRODUCT_RAG_24_EPIC.md](../architecture/arch_plan/STREAM_PRODUCT_RAG_24_EPIC.md), [ADR-014](../adr/ADR-014-rag-retrieval-vectors-and-stores.md), `tests/api/test_rag_*.py` |
| QA_ARCH_ENTERPRISE_SCALE_* | [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../architecture/ENTERPRISE_SAAS_SCALE_ENVELOPE.md) |
| QA_ARCH_L3_STAGING_EVIDENCE_TEMPLATE_* | **Приложение A** этого файла |
| QA_ARCH_GAP_SCAN_* | [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md), [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) |
| QA_ARCH_LEAD_SAAS_MASTER_PLAN_REVIEW_* | [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) (встроенные циклы §2a–§2e, §9) |
| QA_ARCH_85_PLUS_* (roadmap / tracker) | [STREAM_PRODUCTION_READINESS.md](../architecture/arch_plan/STREAM_PRODUCTION_READINESS.md), [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md), ADR-008 |
| Прочие `QA_ARCH_*` в artifacts | [ROLE_QA_ARCH.md](../ROLE_QA_ARCH.md), соответствующий `STREAM_*_EPICS.md` или `QA_REPORT_*` |

**Версия отчёта:** 2026-04-06
