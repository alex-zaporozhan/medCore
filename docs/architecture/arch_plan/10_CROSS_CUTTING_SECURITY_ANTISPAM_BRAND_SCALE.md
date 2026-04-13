# Сквозные темы: антиспам, security UX, бренд, монолит, envelope (§27–§31)

**PRC (L3):** [STREAM_PRODUCTION_READINESS.md](./STREAM_PRODUCTION_READINESS.md) — **PRC-B7**, **PRC-C***, **PRC-F***, **PRC-G1**; оглавление go-live: [STREAM_CROSS_CUTTING_GO_LIVE.md](./STREAM_CROSS_CUTTING_GO_LIVE.md).

## QA_ARCH: префлайт для @ARCH и приёмка

**Инспектор:** [ROLE_QA_ARCH.md](../../ROLE_QA_ARCH.md). **Playbook:** [LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md](../LEAD_SAAS_PHASE_EXECUTION_PLAYBOOK.md). **Пример приёмки:** [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (строки **10-Q***).

| Этап | Ожидание |
|------|----------|
| **@ARCH до @DEV** | На каждый подпараграф §27–§31: **контракт** (API, edge, конфиг), **метрика** из реестра §11 или явный **ADR риска**; для OpenAPI — план провязки `responses` к операциям (см. **1c-Q4**, **10-Q7** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md)). |
| **@QA_ARCH после @DEV** | Нет «схема в components без operations»; prod-ошибки сверять с [API_PUBLIC_ERROR_CODES.md](../API_PUBLIC_ERROR_CODES.md); JSON дашбордов — с тестом валидности при наличии в CI. |
| **Красные флаги** | Объявление §27/§28 закрытыми без негативных тестов и метрик злоупотреблений; смешение стиля `code` в Python без учёта нормализации ответа; Grafana в репозитории = «мониторинг в проде» без OPS. |

**В МП:** отдельного прямоугольника на mermaid для §27–§28 нет — это **сквозные** требования к §5, §15a, §11 (МП §15b усиление цикл 4).

## §27 — Антиспам (auth, чаты, omni)

**Архитектурные требования**

- Rate limit по IP, учётке, организации; капча на чувствительных шагах (МП §27).
- Раздельные политики staff-chat vs клиентский канал.
- Метрики низкой cardinality: `spam_blocked_total` и аналоги — через **реестр §11**.

**Когда внедрять @DEV**

- Одновременно с публичным **signup** (§5) и с ростом публичных чатов.
- Не откладывать до «после 1b» без явного ADR риска.

## §28 — DevTools, ошибки API, вторжение

**Архитектурные требования**

- Стабильные коды ошибок в prod без стеков/внутренних путей; образец дисциплины — [PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md); **нормализация `code` в JSON** — [API_PUBLIC_ERROR_CODES.md](../API_PUBLIC_ERROR_CODES.md) (**1c-Q2** закрыт на уровне `main.py`).
- **1c-Q4 (частично закрыто):** общие схемы + **глобальная** провязка `responses` для всех операций `api_router` (`STANDARD_OPENAPI_ERROR_RESPONSES`, `main.py`); опционально — примеры 403 гейтов в OpenAPI — [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).
- Security events: серии 401/403, подозрительные пути, превышение rate limit.
- Метрики: `security_auth_failure_total`, `security_suspicious_request_total` с лейблами `reason` / `path_class`, **без** сырого `organization_id` в алертах (МП §28, §11 M1).

**Когда внедрять @DEV**

- При любом расширении публичного API и embed (§24).
- Вместе с ужесточением логирования на фронте (маскирование).

## §29 — Бренд «МойКлиент» / MyClient

**Архитектурные требования**

- Публичное имя RU vs кодовое имя латиницей; `clinic_id` сохраняется как технический якорь (МП §29).
- Глоссарий «пациент → клиент» в API и логах, согласованный с каталогом ошибок (PRINCIPLE цикл 2).

**Когда внедрять @DEV**

- Постепенно: i18n ключи, новые маршруты с нейтральными именами; без ломки контрактов.

**Черновик глоссария (RU ↔ код; URL не ломаем):**

| Публично (RU) | В API / коде |
|----------------|--------------|
| Клиент | префиксы `/patient/...`, сущность Patient |
| Точка / клиника | `clinic_id` как технический якорь тенанта |

## §30 — Монолит vs сервисы

**Архитектурные решения**

- Модульный монолит + Celery + outbox + кэш + read-replicas до доказанных узких мест (МП §30).
- Точечный вынос: webhook-worker платежей, batch-import, тяжёлые отчёты — при готовности SLO.

**Документ до маркетинга «10k+»**

- Ориентиры данных: [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md).
- Шаблон прогона нагрузки и чеклист: [LOAD_SCENARIO_MARKETING_10K.md](../../operations/LOAD_SCENARIO_MARKETING_10K.md) (МП §30 честность маркетинга).

## §31 — Envelope масштаба 10k+ бизнесов

**Обязанности @ARCH (ШАГ 0A [ROLE_ARCH.md](../../ROLE_ARCH.md))**

- Индексы, пагинация, витрины, фоновые конвейеры — от envelope; при спорном экране — явный блок в DEV_PROMPTS.
- Не утверждать новые публичные денежные пути при `replicas ≥ 2` без §17.1.
- Импорт — §25.3.

**Артефакт**

- Короткий `ENTERPRISE_SAAS_SCALE_ENVELOPE.md` или раздел в [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../TARGET_PLATFORM_MULTITENANCY_REFERENCE.md) (МП §31).

**Якоря @QA_ARCH (§27–§31)**

- [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md) (§31 / envelope)
- [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (**10-Q***; Grafana SOC, OpenAPI, **10-Q7**)

## Сводка для @DEV: «не забыть в каждой фазе»

| Фаза | Сквозное действие |
|------|---------------------|
| 1b | Rate limit signup + webhook B; privacy чеклист |
| 1c | Не плодить высокую cardinality в метриках гейтов |
| 1d | Реестр имён перед новыми `security_*` / spam |
| 1e | Rate limit embed/API keys |
| 2 | Outbox снижает класс атак «повторная доставка» при конкурирующих воркерах — всё равно идемпотентность |
| 3+ | Импорт — батчи и квоты (антидудос) |

## Статус @DEV + QA_ARCH (2026-04-06, обновлено после итерации 2)

- **§27:** единый счётчик `spam_blocked_total{channel}` на каждый HTTP **429**; канал **`public_signup`** для `/api/v1/auth/send-code` и `/api/v1/auth/verify-code` (остальной `/api/v1/auth` — `public_auth`); **`public_platform`** для `POST /api/v1/public/platform/signup/checkout`, `GET /api/v1/public/platform/catalog/*` и родственных путей `/public/platform/...`; дашборд Grafana — `deploy/grafana/dashboards/dental_booking_security_soc_w10.json`.
- **§28:** `security_*` метрики как выше; **машинные `code` в ответах** — lowercase `snake_case` (`normalize_api_error_code`, опционально `details` для `site_key` / `field`); для `detail["code"]` типа **`Enum`** используется **`.value`** (не `str(Enum)`); **`trace_id`** не дублируется в `details` — см. [API_PUBLIC_ERROR_CODES.md](../API_PUBLIC_ERROR_CODES.md).
- **§31:** черновик envelope — [ENTERPRISE_SAAS_SCALE_ENVELOPE.md](../ENTERPRISE_SAAS_SCALE_ENVELOPE.md) (ранее ссылка в INDEX без файла).
- **§29:** черновик глоссария — в этой странице; полная i18n-унификация без ломки URL — бэклог продукт/LEAD.
- **§30:** шаблон сценария нагрузки — [LOAD_SCENARIO_MARKETING_10K.md](../../operations/LOAD_SCENARIO_MARKETING_10K.md); утверждение чисел — **10-Q5** / LEAD в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md).

**Тесты:** `tests/core/test_security_observability.py`, `tests/api/test_security_soc_metrics.py`, `tests/core/test_api_error_codes.py`, `tests/core/test_http_exception_envelope.py`, **`tests/core/test_openapi_error_schemas.py`**, `tests/api/test_public_platform_checkout.py`, `tests/api/test_public_platform_catalog_rate_limit.py`, `tests/core/test_request_ip_public_rate_limit.py`.

**Доки процесса:** [TEST_HTTP_EXCEPTION_BOUNDARY.md](../TEST_HTTP_EXCEPTION_BOUNDARY.md) (граница сырого `detail`), [RBAC_MANUAL_PATHS_CHECKLIST.md](../../operations/RBAC_MANUAL_PATHS_CHECKLIST.md) (SSE/webhook).

**Приёмка @QA_ARCH:** статусы и хвосты — [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) (секция **Сквозное arch_plan/10**, строки **10-Q***).

**10-Q4 (частично, webhook B / 1b-E6):** на приложении — per-IP rate limit для `POST /api/v1/platform/billing/webhooks/yookassa` (`RATE_PLATFORM_BILLING_WEBHOOK_IP_LIMIT`, `RATE_PLATFORM_BILLING_WEBHOOK_IP_WINDOW_SECONDS`, Redis). На edge — усилить WAF/лимиты по пути провайдера; ориентир и пример `limit_req` для nginx: [deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md](../../../deploy/nginx/README_PLATFORM_BILLING_WEBHOOK.md). Отчёт приёмки: [QA_REPORT_1b_E3b_webhook_contract.md](../../artifacts/QA_REPORT_1b_E3b_webhook_contract.md).

**Остаётся:** полноценный WAF на edge для всего публичного контура (**10-Q4**), дожим **1c-Q4** (примеры/уточнения в OpenAPI при необходимости), подпись LEAD по **10-Q5** (фактический прогон «10k+»). **10-Q7** закрыт: стандартные `responses` на всех v1-операциях. Опционально: выровнять оставшиеся литералы `code` в Python (например `CHAT_RATE_LIMITED`) к `snake_case` в источнике — клиент уже получает нормализованный JSON.
