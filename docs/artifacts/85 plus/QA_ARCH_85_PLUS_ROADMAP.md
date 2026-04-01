## QA_ARCH_85_PLUS_ROADMAP — как вывести Dental Booking на 8.5+

> **Роль:** QA_ARCH  
> **Цель:** довести проект до уровня, который уверенно выдерживает собеседование с сильным Team Lead и ближе к real commercial readiness.  
> **Принцип:** не “косметика”, а измеримые улучшения по reliability, security, performance, operability и product integrity.

---

## 1. Целевой портрет проекта на 8.5+

На уровне 8.5+ проект должен демонстрировать:

- **Архитектурную целостность:** понятные границы слоёв, четкие инварианты домена, отсутствие “магии” в критичных цепочках.
- **Надежность в проде:** контролируемые отказы, предсказуемое поведение под нагрузкой, неразрушаемые критичные сценарии.
- **Безопасность по умолчанию:** защита PII, минимизация blast radius, доказуемые практики доступа и секретов.
- **Наблюдаемость:** метрики, трассировка, alerting и runbook’и для инцидентов.
- **Операционную зрелость:** backup/restore, DR-стратегия, проверяемые SLO/SLA.
- **Инженерную дисциплину:** тест-пирамида, quality gates, perf/security regression checks.
- **Согласованность UI админки с каноном:** токены Swiss Slate / Ink (`DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6) — spot-check при приёмке крупных PR фронта (не блокер всей программы 8W, но критерий зрелости продукта).

---

## 2. Расширенные критерии оценки (scorecard)

### 2.1. Шкала (0..10)

- **0-3:** proto/MVP, много непредсказуемости.
- **4-6:** рабочий продукт, но рискованный для роста.
- **7-8:** production-готовность для умеренной нагрузки.
- **8.5+:** управляемая система с доказуемой надежностью и безопасностью.
- **9+:** высокий уровень операционной зрелости и эволюционной архитектуры.

### 2.2. Весовые категории для итоговой оценки

1. **Reliability & Resilience — 20%**
2. **Security & Compliance — 20%**
3. **Performance & Scalability — 15%**
4. **Data Integrity & Transactional Correctness — 10%**
5. **Observability & Incident Response — 10%**
6. **Architecture & Code Quality — 10%**
7. **AI Integration Quality (не бутафория) — 10%**
8. **Delivery Discipline (CI/CD, tests, release safety) — 5%**

### 2.3. Минимальные “проходные” KPI на 8.5+

- **Availability:** >= 99.5% для API в рабочем окне.
- **p95 latency (ключевые API):** <= 300-500ms (без тяжелых AI операций).
- **Error rate:** < 1% на бизнес-критичных эндпоинтах.
- **MTTR:** <= 60 минут на P1/P2 инциденты.
- **RPO/RTO:** формально определены и протестированы (например RPO <= 15 мин, RTO <= 2 часа).
- **Restore test:** минимум 1 успешный проверенный restore в месяц.
- **Security:** 0 критических уязвимостей в зависимостях/контейнерах; включенные secret scanning и dependency scanning.
- **AI reliability:** измеримый fallback rate, timeout rate, provider error rate, retry success rate.

---

## 3. Где проект сейчас (срез) и что мешает 8.5+

### 3.1. Сильные стороны (база уже хорошая)

- Async backend на PostgreSQL + SQLAlchemy + Alembic.
- Redis + Celery + периодические задачи.
- Есть observability foundation (метрики, trace_id, сервисные счетчики).
- AI интеграция не фейковая: реальные вызовы, конфиги, fallback.
- Закрыты P0–P3 contract/gate дыры по критичным контурам: `get_request_context` fallback без token’ов, `AiSanitizer` сохраняет стабильные AI-токены при маскировании PII, обновлён RBAC permission inventory и устранена legacy-аварийность `ErpVisitNodeService` на unit-level.

### 3.2. Основные разрывы (gaps) до 8.5+

- **Неполная отказоустойчивость интеграций:** нет системного retry/backoff/circuit breaker паттерна.
- **Backup/DR не production-уровня:** backup есть, но restore-процесс не доведен как регулярная проверяемая практика.
- **Нагрузочная емкость не доказана:** отсутствует строгий perf baseline с SLO.
- **Мультитенанси ограничен row-level изоляцией:** нужен усиленный контроль isolation/authorization на всех путях.
- **RAG как полноценная система отсутствует:** есть AI, но нет retrieval pipeline/vector layer.
- **RBAC/Box cuts неполные на ряде admin P4–P7 endpoints:** часть роутов защищает только по токену/`clinic_id`, но не требует `require_permissions(...)` и/или не имеет enterprise/Box-ограничений на сервере.
- **Box vs Enterprise на границе P5 (аналитика):** в UI коробки могут быть скрыты ROI/LTV-блоки, но **API** маркетинговой атрибуции и части ERP/отчётов с ROI **пока не завернуты** в тот же server-side edition-gate, что retention/CRM — при наличии прав (`erp.owner_reports.read`, `attribution.reports.read` и т.д.) данные теоретически доступны в обход «продуктового» обещания коробки. Для 8.5+ нужен **либо** `is_box_edition()` на соответствующих роутерах, **либо** отдельный RBAC-профиль коробки без этих permission codes в `seed_rbac_baseline`.
- **Синхронизация издания фронт/бэк:** два независимых переключателя — `VITE_EDITION` (фронт) и `EDITION` (API). Расхождение даёт «UI как коробка, API как Enterprise» или наоборот; в docker-compose переменные задаются через `.env` без автопроверки пары.
- **Единый error contract не везде соблюдён:** HTTPException часто возвращает только `detail` без `code`, а глобальный обработчик формирует структурированный envelope только для `Exception`, не для HTTP ошибок. *(Уточнение: для `HTTPException` в `main.py` уже есть handler с полем `code` в теле ответа — см. §10.10.)*

---

## 4. План повышения до 8.5+ (30/60/90 дней)

## Phase 1 (0-30 дней): “Стабильный фундамент”

1. **Reliability hardening**
   - Ввести единый policy для внешних вызовов: timeout + retry (exponential backoff + jitter) + circuit breaker.
   - Для Celery задач внедрить `autoretry_for`, лимиты повторов, dead-letter подход (или отдельная fail-queue стратегия).
   - Ввести idempotency keys для всех критичных write/notification flow.

2. **Backup/Restore и DR basics**
   - Перейти на регулярный DB-level backup (`pg_dump` + policy хранения).
   - Добавить документированный restore runbook.
   - Провести и зафиксировать первый restore drill в staging.

3. **Performance baseline**
   - Выбрать топ-10 критичных API и зафиксировать p50/p95/p99 baseline.
   - Настроить нагрузочный сценарий (k6/Locust) и nightly smoke perf.
   - Создать performance budget на каждый релиз.

4. **Security minimum bar**
   - Включить SAST + dependency scan + secret scan в CI.
   - Ротация секретов и запрет хранения чувствительных значений в репозитории.
   - Проверить RBAC на административных endpoint’ах через negative tests.
   - **Box cut на сервере (P5/P6):** закрыть разрыв «UI без ROI / API с ROI» — см. §3.2 и §10.11; добавить negative-тесты для `EDITION=box` на маркетинговую атрибуцию и тяжёлые owner-отчёты при необходимости.

5. **CI/CD quality gates для “не выпускаем сломанное”**
   - Разделить pipeline на `pull_request` (test/lint/security gates) и `push main` (build+scan+publish).
   - До пуша docker images прогонять: backend `pytest` + `ruff` + `mypy` (если применимо) и frontend `vitest` + `build`.
   - Вводить release блокеры: `critical` security findings = fail; unstable tests = fail.
   - Отказаться от `:latest` как единственного тега: публиковать как минимум `${GIT_SHA}` и `${branch}` (например `main`), плюс `latest` только по ручному промо/регламенту.

## Phase 2 (31-60 дней): “Коммерческая зрелость”

1. **Data correctness & transactions**
   - Карта транзакционных границ для Booking -> ERP -> Tasks/Attention -> Notifications.
   - Добавить контрактные тесты на atomicity и rollback в межсервисных цепочках.
   - Внедрить outbox/inbox паттерн для надежной публикации событий.

2. **Observability 2.0**
   - Стандартизировать structured logs (trace_id, clinic_id, actor_id, operation, result).
   - Добавить distributed tracing (OpenTelemetry).
   - Набор алертов: error budget burn, queue lag, DB saturation, Redis saturation, AI provider errors.

3. **Tenant safety**
   - Ввести audit-проверку всех запросов на обязательный tenant filter.
   - Добавить integration tests на cross-tenant data leak.
   - Ужесточить policy доступа по ролям + клиникам.

4. **AI quality uplift**
   - Единый eval-suite (качество, latency, hallucination risk, safety filters).
   - Метрики AI: success/fallback/error/timeout/retry distribution.
   - Стабилизировать tool-calling: schema validation, deterministic error envelopes.

5. **Release safety: миграции и откаты без “дата-даун”**
   - Ввести правило “backward/forward compatible migrations”: expand/contract для схемы и данных.
   - Убедиться, что старый backend может работать с новой схемой (или наоборот) на период rollout’а.
   - Разнести “run alembic upgrade head” и “app start” на контролируемую стадию релиза (один исполнитель/one-shot).
   - Зафиксировать rollback план миграций (вплоть до “временно откатить код” при невозможности отката схемы).

## Phase 3 (61-90 дней): “8.5+ подтверждено фактами”

1. **RAG (если это позиционируется в продукте)**
   - Внедрить retrieval pipeline: ingestion -> chunking -> embedding -> vector index -> rerank -> grounded response.
   - Набор guardrails: citation-required mode, confidence threshold, fallback без выдумок.
   - E2E тесты качества ответов на доменных сценариях.

2. **Scalability path**
   - Тесты нагрузки до целевого concurrency (например 200-500 одновременных активных user flows в зависимости от профиля клиентов).
   - Capacity planning: DB pool, worker concurrency, Redis memory policy, autoscaling strategy.
   - Runbook для peak-hours и деградационных режимов.

3. **Operational readiness**
   - Формализовать SLO/SLI + еженедельные отчеты.
   - Регулярные game day упражнения (отказ БД, отказ Redis, деградация AI provider, перегрузка очереди).
   - Регламент релизов: canary/rollback checklist.

---

## 5. Дополнительные критерии именно для Performance (чтобы “пройти тимлида”)

1. **API latency budgets**
   - p95/p99 по каждому бизнес-критичному роуту.
   - Раздельно: read-path, write-path, AI-path.

2. **Database performance**
   - Slow query budget (доля запросов > 250ms).
   - Индексный аудит: coverage по топовым WHERE/JOIN.
   - Connection saturation и wait time.

3. **Queue performance**
   - Queue lag, task age distribution, retry ratio.
   - Время от события до эффекта (event-to-action latency).
   - Доля “poison tasks” и время их изоляции.

4. **Cache effectiveness**
   - Hit ratio по ключевым кэшам.
   - TTL hygiene (слишком короткие/длинные TTL).
   - Cache stampede protection для горячих ключей.

5. **AI performance**
   - Model response p95/p99.
   - Token usage per scenario.
   - Стоимость на 1000 пользовательских сценариев.
   - Fallback latency vs normal latency.

6. **Frontend perceived performance**
   - TTFB/LCP/INP по админке и PWA.
   - Доля тяжелых экранов и размер бандла.
   - UX under degraded backend (graceful UI states).

---

## 6. Security uplift checklist (must-have для 8.5+)

1. **Access control**
   - Полная матрица RBAC + тесты запретов.
   - Cross-tenant access tests (обязательные).
   - **Издание продукта (Box):** сервер — источник правды; UI-скрытие без API-гейта недостаточно для обещаний «коробка без Enterprise-CRM / без ROI». CRM (`/admin/crm`) и retention на бэке уже режутся по `EDITION`; остаётся выровнять **маркетинговую атрибуцию** и **ROI-слой отчётов** (см. §10.10–10.11).

2. **Data protection**
   - Классификация данных (PII/финансы/медицинские).
   - Шифрование in transit и at rest (по возможностям окружения).
   - Политика маскирования в логах и AI payload.

3. **Application security**
   - Input validation, safe error envelopes, rate limit на чувствительных ручках.
   - Защита от replay для критичных операций.
   - Security headers, CSRF/CORS review.

4. **Supply chain security**
   - Pin/monitor зависимостей.
   - Container scan + base image обновления.
   - Secret management policy.

5. **Auditability**
   - Неизменяемые audit trails для админских действий.
   - Экспортируемые отчеты для расследований.

---

## 6.1. Профессиональные рекомендации по CI/CD и релизу (под текущий репозиторий)

### 6.1.1. Как улучшить текущий `docker-images.yml` (build+push)

Сейчас workflow делает только `build and push` при `push main` и публикует теги `:latest`, не проверяя тесты/линт/сканы.

Минимальный апгрейд на 8.5+:

- Добавить отдельные job’ы:
  - `backend-tests` (install poetry deps -> run `ruff` -> run `pytest`)
  - `frontend-tests` (npm ci -> `npm run build` -> `npm run test`)
- Добавить security supply-chain scanning:
  - после сборки образов: scan image (например Trivy/Grype) и fail на `CRITICAL/HIGH`
  - scan Dockerfile base images и зависимости (SCA)
- Добавить tagging стратегию:
  - `:git-sha` (обязательный)
  - `:main` (опциональный, для простого указания на ветку)
  - `:latest` только по ручному подтверждению (или после успешной smoke/perf стадии)
- Включить build caching:
  - `docker/build-push-action` с cache-from/cache-to, чтобы ускорить релизы
- Ввести artifact labels:
  - метки `org.opencontainers.image.revision`, build time, версию приложения

### 6.1.2. CD (деплой) “по-взрослому”

Поскольку в репозитории нет прод/стейдж CD workflow, для коммерческого уровня нужен хотя бы простой CD в 2 шага:

1) автоматика: публикуем образа (и фиксируем теги)  
2) ручной gate: оператор/OPS выбирает теги и запускает deploy в staging/prod

Практически (в рамках docker-compose) это обычно выглядит как:

- staging: `pull image:${GIT_SHA}` -> `docker compose up -d` -> выполнить `smoke checks` (`/health`, 1-2 “read-only” endpoint’а)
- prod: то же, но только после успешного staging smoke и manual approval

--- 

## 7. Что еще критически важно (не было полноценно закрыто выше)

1. **Конкурентность записи (anti double-booking)**
   - Нужны гарантии от race condition при одновременном бронировании одного слота: транзакционные ограничения/уникальные констрейнты на уровне БД + правильные блокировки.

2. **Надежность событий/доставки (exactly-once не гарантируется “само”)**
   - Для цепочек “event -> job -> write” без outbox/inbox паттерна есть риск дублей/потерь при падениях.
   - Обязательно: идемпотентность write-path + идемпотентность publish/consume на уровне задач/handlers.

3. **Безопасность секретов и окружения**
   - В workflow/CI нельзя хранить секреты в коде; важно secret rotation, и отдельные env для staging/prod.
   - Плюс проверка, что `SECRET_KEY`, JWT key, provider keys не попадают в логи.

4. **Безопасность миграций и backward compatibility**
   - Миграции должны быть безопасны при rolling update.
   - Нужны правила о том, какие изменения можно делать без downtime.

5. **Data governance**
   - Политика retention’а (логи, backup JSON, экспорт в файлы).
   - Права и обработки PII (включая удаления/анонимизацию где применимо).

6. **Операционная DR-готовность “не на бумаге”**
   - restore drill + проверка качества данных (не только “вернулось”, но “сценарии работают”).
   - игра “сломался Redis / Celery broker / AI provider” с описанием деградации.

7. **Внешние входы**
   - если есть вебхуки (Telegram/платежи) — нужна валидация подписи и защита от replay.
   - file upload/attachments (если появятся) — антивирус/скан и изоляция.

8. **Профиль издания (Box) в эксплуатации**
   - Чеклист выката: в одном runbook’е явно выставить **и** `VITE_EDITION` (фронт), **и** `EDITION` (бэкенд); smoke: 403 `box_forbidden` на защищённых Enterprise-маршрутах (например `/api/v1/admin/crm/*`, retention) при коробке.
   - Опционально: предупреждение в логе при старте API, если задан только один из контуров (если введёте общий `deployment profile`).
   - **Dev UX:** в `frontend/.env.example` по умолчанию часто не сценарий коробки (`premium` и т.д.) — регрессии Box в dev ловятся хуже; для приёмки коробки иметь отдельный профиль env или документированный пресет.

---

## 8. Как подготовиться к собеседованию по этому проекту

### 8.1. Обязательная карта знаний (что надо знать “до винтика”)

1. End-to-end flow: `Patient booking -> payment -> completion -> ERP -> CRM -> tasks/attention`.
2. Где начинаются и заканчиваются транзакции, где гарантии атомарности.
3. Какие очереди есть, что гарантирует delivery, где риск дублей.
4. Что кэшируется, с каким TTL и как инвалидируется.
5. Что происходит при отказе AI/Redis/Postgres.
6. Где границы tenant isolation и как предотвращается data leak.
7. Как выполняются миграции и rollback plan.
8. Как подтверждается качество: тесты, метрики, алерты, runbook.

### 8.2. “Сильные” ответы тимлиду (шаблон)

- **Что хорошо сейчас:** “У нас уже есть async-архитектура, миграционная дисциплина, очереди, кэш, метрики, частичный graceful degradation.”
- **Что мы осознанно улучшаем:** “Я закрыл reliability и DR-гепы: retries/backoff/circuit breaker, restore drills, perf baseline и SLO.”
- **Почему это не бутафория:** “Каждое улучшение подтверждено KPI и тестами, а не только архитектурными словами.”

---

## 8. Definition of Done для оценки 8.5+

Считаем цель достигнутой, если одновременно выполнены условия:

1. Есть formal scorecard и фактическая оценка >= 8.5.
2. Есть подтвержденные perf-отчеты по целевым сценариям.
3. Есть рабочий backup + документированный и проверенный restore.
4. Есть incident playbook и минимум один проведенный game day.
5. AI-поток имеет измеримые quality/reliability метрики и безопасный fallback.
6. Нет критичных security findings в CI на релизной ветке.

---

## 9. Предложение по практической реализации в этом репозитории

1. Создать единый `NONFUNCTIONAL_SCORECARD.md` с KPI/весами/фактом/планом.
2. Добавить `PERF_BUDGETS.md` + `k6` профили ключевых API/flows.
3. Добавить `DR_RUNBOOK.md` + задачу ежемесячного restore drill.
4. Добавить `AI_RELIABILITY.md` (timeouts/retries/fallbacks/evals/cost).
5. В CI включить security scanning и quality gates.
6. В `DEV_EXECUTION_TRACKER_NEXT.md` вести прогресс по 30/60/90 и фактические метрики.

Этот набор даст не просто “красивый рассказ”, а доказуемую инженерную зрелость, которую реально ценят на собеседованиях и в коммерческой разработке.

---

## 10. QA_ARCH — факт-ревизия по презентационному контуру и «пробелам» (март 2026)

### 10.1. Миграции vs демо-данные

- Цепочка Alembic после baseline (`schema_v2_initial` + последующие ревизии) задаёт **только схему** и системные `INSERT` (permissions/roles в отдельных миграциях).  
- «Грязные» демо-имена и одна клиника исторически приходили из **скриптов** (`seed_demo_data.py`, `seed_omnichannel_demo.py`), а не из DDL.  
- Для показа клиенту добавлен **презентационный сид**: `src/scripts/seed_presentation_showcase.py` + план `docs/artifacts/QA_ARCH_PRESENTATION_SEED_PLAN.md`. Сквош всех миграций в один файл **не требуется** для чистого демо — достаточно пустой БД + `alembic upgrade head` + этот сид.

### 10.2. Мультифилиальность в админке и дашбордах (backlog)

- **Факт сейчас:** один `AdminUser` привязан к **одному** `clinic_id` (JWT содержит клинику). Презентационный сид (`seed_presentation_showcase`) создаёт **одну** клинику и одну учётку `admin@dentapro.demo`, чтобы поведение демо совпадало с продуктом и PWA.  
- **Требуется в продукте (доработка):**  
  1. **Единый логин** владельца/админа сети с выбором активной клиники (или мультиконтекст в JWT/сессии) вместо N учёток на N филиалов.  
  2. **Отчёты и дашборды** (выручка, задачи, омниканал, ERP-витрины): явный фильтр **«одна клиника | все клиники сети | подмножество»** с проверкой RBAC и tenant isolation.  
- До появления этих возможностей мультиклинический демо-набор в БД не является целевым — см. `QA_ARCH_PRESENTATION_SEED_PLAN.md`.

### 10.3. Лента внимания (Attention) и омниканал

- **Конфликты/жалобы** в `AttentionFeedService` для блока `conflict` строятся по **`chat_messages`** (внутренний чат пациент–клиника) с эвристикой по **ключевым словам** в тексте (`жалоб`, `недовол`, …), а не по AI-классификации.  
- **Омниканал** (`omni_messages`) в этой цепочке **не** является источником conflict-items в V1.  
- **AI-анализ тональности/конфликтов** в чате в реальном времени **не продуктовый end-to-end**: сводки/подсказки идут через `ChatAiService` / `SafeAiClient` при наличии `AI_PROVIDER_BASE_URL` и настроек; автоматическая разметка «конфликт» без ключевых слов — **не сделана**.

### 10.4. AI (Deepseek и др.) — почему может «не работать»

- Провайдер считается подключённым, если задан **`AI_PROVIDER_BASE_URL`** (и при вызовах — ключ в `AI_PROVIDER_API_KEY`). `AiClient.is_configured()` проверяет только base URL.  
- Для омниканала по умолчанию в БД часто **`omni_ai_settings.ai_mode = DISABLED`**; сид презентации выставляет **`SUGGEST_ONLY`** на scope `BUSINESS`.  
- В Docker Compose сервисы `backend`/`celery` используют `env_file: .env` — если ключи только в IDE, а не в `.env` контейнера, AI в контейнере будет отключён.  
- **Rate limits**: `rate_ai_clinic_*` / `rate_ai_heavy_*` могут давать 429 при частых тестах.  
- Дальнейшая зрелость: см. п. 9 выше и отдельный артефакт `AI_RELIABILITY.md` (ещё не создан).

### 10.5. Смены администраторов

- Отдельной сущности «смены администраторов» в модели **нет** — в презентационном плане не сидируем выдуманные смены. Это отдельная фича (график, календарь смен, отчёты).

### 10.6. ERP / аналитика

- Витрины и агрегаты ERP могут требовать **фоновых задач Celery** и настроек `erp_*_read_from_aggregate`; презентационный сид создаёт оплаченные визиты и флаги `erp_processed`, но «полная» витрина без прогона воркеров может быть неполной — это ожидаемо для демо без production-пайплайна.
- **@LEAD (2026-03):** для редакции **Box** по продукту (P5: без LTV/ROI) недостаточно скрыть виджеты на фронте: эндпоинты `admin_marketing_attribution`, часть `admin_reports` (attribution/ROI vitrine) должны быть согласованы с **server-side** edition-gate или с RBAC-профилем коробки — иначе обход через прямой вызов API при валидном токене остаётся продуктовым разрывом, а не только «security для анонима».

### 10.7. RBAC на пустой базе

- Исторический `rbac_tasks_0001_init` лежит в `alembic/versions_archive`; на новой БД глобальные роли/permissions могли не попасть. Скрипт **`src/scripts/seed_rbac_baseline.py`** выравнивает матрицу из `rbac_matrix.py`.

### 10.8. Презентация (март 2026): сводка «что исправлено в коде» и оставшиеся UX-пробелы

**Исправлено / усилено в коде и сиде**

- **Дашборд vs расписание:** KPI по умолчанию больше не считаются по «всем клиникам» при пустом мультиселекте — при первом открытии выставляется **текущая клиника** админа (`AdminDashboardPage`), чтобы цифры совпадали с `GET /v1/admin/bookings` по `clinic_id` JWT. Пользователь по-прежнему может очистить фильтр и запросить агрегат по сети (если в будущем появится мультиконтекст).
- **`seed_presentation_showcase.py`:** якорные записи на **сегодня и завтра** (включая воскресенье), с частью **completed + Payment** (выручка за день) и частью **confirmed**; график врачей **пн–вс**, чтобы сетка расписания на воскресенье строилась и записи были видны; воронка CRM (пайплайн, стадии, `LeadStageSemanticMap`, лиды); **кассы** и **`PayrollPolicy`** по врачам (35% от услуг, 15% от товаров — демо-коэффициенты); источники трафика, кампания, `VisitAttribution`; **второй пользователь** `manager@dentapro.demo` с ролью **manager**; **6-сообщений** диалог Telegram: клиент ↔ `HUMAN_ADMIN` в отдельном чате (`tg_demo_admin_thread`).
- **Омниканал «один клиент — несколько каналов»:** в одном чате демонстрируется **Королёв** (Telegram + Email в `external_ids` одного контакта, `primary_phone` = телефон карточки пациента для блока лояльности); отдельные демо-входы по Email и Telegram для одного имени **удалены** (раньше давали два окна в списке). Реальное объединение разных контактов в проде — отдельная фича (merge по телефону/пациенту).

**Зарплаты (как задумано в модели, не полный расчёт в сиде)**

- `PayrollPolicy` задаёт **фикс за смену** (`fixed_per_shift`) и **проценты** от выручки по услугам/товарам. Фактическое начисление в проде ожидается от **ERP/воркеров** (агрегаты, проводки) — сид только заполняет политики для UI и проверок.

**Оставшиеся продуктовые пробелы (честно)**

- **Лояльность → Абонементы:** список по-прежнему завязан на **UUID пациента** — без поиска по ФИО/телефону это трение; в консоли сида печатается пример UUID.
- **Публичный веб-чат без авторизации:** зависит от публичного API виджета и политики токена/сессии; анонимный заход обычно ограничен rate-limit и привязкой к `session_id` — нужна явная спецификация в продукте.
- **E2E «все возможности»:** полный прогон — отдельный чеклист; сид закрывает демо **данными**, а не **покрытием** всех веток UI.

**Полный сброс данных**

- **Мягко:** `DROP SCHEMA public CASCADE` + `CREATE SCHEMA public` + GRANT — схема пересоздаётся в том же кластере Postgres.
- **Жёстко (Docker Compose, том `./pgdata`):** остановить зависящие сервисы и контейнер БД (`docker compose stop backend celery celery-beat` и `docker compose stop db`), удалить каталог **`pgdata`** в корне репозитория, снова `docker compose up -d db redis`, дождаться `healthy`, затем с хоста **`alembic upgrade head`** и сиды — получается полностью новый data directory без остатков WAL/старых настроек кластера.
- Дублирующая ревизия `c3d4e5f6g7h8_erp_finance_inventory` **удалена из активной цепочки** (ERP-таблицы уже в `schema_v2_initial`); дальше идёт сразу `a1b2c3d4e5f6_form_link_tokens` после `expand_alembic_ver_64`. Достаточно **`alembic upgrade head`**, затем `seed_rbac_baseline` и `seed_presentation_showcase`.
- Копия удалённой ревизии по-прежнему лежит в **`alembic/versions_archive/`** как архив (не участвует в `upgrade`).
- Редкий случай: если в `alembic_version` осталось значение `c3d4e5f6g7h8_erp_finance_inventory` (после старого `stamp`), выполните `UPDATE alembic_version SET version_num = 'expand_alembic_ver_64';` и снова `alembic upgrade head` (или сразу выставьте актуальный `head`, если схема уже полная).
- После сброса БД полезно выполнить **`redis-cli FLUSHALL`** (или очистить ключи `schedule:*`), чтобы не осталось кэша расписания от старой клиники.

### 10.9. Telegram-оповещения и Owner Brief (качество, anti-spam, UX)

**Наблюдение (по факту):**

- Уведомление `omni_ai_suggestion` отправлялось на каждый AI-черновик в `SUGGEST_ONLY`, что при активном чате могло давать серию однотипных сообщений в Telegram.
- Утренний бриф был слишком «плоским» (только базовые цифры), без метрик качества дня и фокуса действий.

**Что должно быть нормой (85+):**

1. **Anti-spam policy:** дедуп/троттлинг событий по ключу `clinic_id + chat_id + event_type` (Redis NX+TTL), чтобы в Telegram уходил не «дождь», а управляемый сигнал.
2. **Severity-модель:** разделение уведомлений на:
   - `critical` (падения интеграций, массовые ошибки),
   - `warning` (эскалации/рост no-show),
   - `info` (AI suggestions, сервисные события).
3. **Digest вместо спама:** для `info`-событий — батчирование в окно 5–15 минут.
4. **Owner Brief v2:** кроме абсолютных чисел показывать:
   - `completion_rate`, `no_show_rate`,
   - `chat_writers_count`,
   - `day_pulse_score`,
   - блок «Риски» + 2–3 «Фокуса на сегодня».
5. **Маршрутизация адресатов:** owner-канал отдельно от админ-дежурного канала, чтобы операционные сообщения не смешивались с руководительской сводкой.

**Статус на март 2026 (обновление):**

- В оркестраторе омниканала введён дедуп Telegram-уведомлений по AI-черновикам и эскалациям (Redis TTL окна).
- Утренний бриф расширен до формата v2 (конверсия, no-show rate, пульс дня, риски, actionable focus).
- Следующий шаг: ввести batched digest и severity-routing как отдельный технический эпик.

---
### 10.10 RBAC/Box cuts и error contract на admin P4–P7

**Факт (по коду):**
- `admin_recall` (`src/api/v1/routers/admin_recall.py`) теперь использует `require_permissions(...)` на всех admin endpoints Recall и делает tenant-isolation по `clinic_id` из RBAC контекста.
- `admin_marketing`, `admin_waitlist`, `admin_prepayment`, `admin_discounts` теперь используют гранулярные `require_permissions(...)` (read/write) вместо «только валидного JWT».
- `admin_retention` (backend) реализует server-side Box cut по `EDITION=box|basic` и требует `require_permissions(...)` для enterprise/owner-level доступа.
- **CRM / Sales pipeline** (`src/api/v1/routers/admin_crm.py`): на роутере добавлена зависимость `require_crm_enterprise_edition` — при `EDITION=box|basic` ответ **403** с `detail.code == box_forbidden` (тест: `tests/api/test_admin_rbac_box_cuts.py`).
- **Единый модуль издания:** `src/core/edition.py` — `is_box_edition()` (чтение `EDITION` в рантайме; согласовано с pytest `monkeypatch.setenv`).
- В `main.py` глобальный handler для `HTTPException` возвращает единый envelope с полем **`code`** (и `trace_id` при наличии); клиенты могут различать `box_forbidden` и общий `forbidden`.

**Что сделано хорошо (@LEAD-ревизия, 2026-03):**
- Централизация edition на бэке, явный router-level gate для CRM, тесты на retention/CRM в режиме коробки, комментарии в `.env.example` про `EDITION`.
- На фронте: `VITE_EDITION` → скрытие Enterprise-навигации и упрощение экрана отчётов в коробке (`frontend/src/config/edition.ts`, `App.tsx`, `AdminLayout`, `AdminReportsPage`).

**Пробелы и упущения (не «критическая уязвимость для анонима», а продуктовая целостность и 8.5+):**

| Зона | Статус | Комментарий @LEAD |
|------|--------|-------------------|
| Retention API | Закрыто на сервере | `EDITION=box` → 403 |
| CRM API | Закрыто на сервере | `/api/v1/admin/crm/*` → 403 в коробке |
| Маркетинговая атрибуция / ROI в отчётах | **Разрыв** | UI в коробке может скрывать ROI; **API** (`admin_marketing_attribution`, часть ERP/attribution в `admin_reports`) пока **не** за тем же server-side gate — при наличии прав владельца данные доступны по API. Нужен gate **или** урезанный RBAC-профиль коробки в `seed_rbac_baseline`. |
| Омниканал + обогащение лида | На усмотрение продукта | В `admin_omni_chat` может отдаваться CRM-контекст лида при открытом чате; если в коробке «нет CRM», продукт должен явно решить: скрывать/резать поля или оставить read-only подсказку. |
| Синхронизация env | Риск эксплуатации | Две переменные: `VITE_EDITION` и `EDITION`; рассинхрон ломает смысл «коробки». |
| Пример фронта | Риск dev | `frontend/.env.example` часто не профиль `box` — регрессии коробки визуально реже ловятся до прода. |

**Следствие для 8.5+:**
- P0–P3 contract/gate закрыт и покрывается тестами; для 8.5+ добить **серверный** Box cut для **P5-аналитики с ROI/LTV-семантикой** (см. §10.11) и по желанию — единый ops-чеклист пары env.
- Error-contract для HTTP: глобальный handler уже отдаёт `code`; локальные `HTTPException` с `detail: { "code": "..." }` дают предсказуемый `code` в теле.

### 10.11 Чеклист @LEAD: Box edition (операции и доработки кода)

1. **Выкат:** в одном чеклисте задать **`EDITION=box`** (или `basic`) для API и **`VITE_EDITION=box`** (или `basic`) для сборки фронта.
2. **Smoke после деплоя:** запросы с валидным admin-токеном → **403** + `code: box_forbidden` на `/api/v1/admin/crm/pipelines` и на retention-сегментах; **200** на recall/marketing box-модули (если остаются в коробке по продукту).
3. **Код (backlog 8.5+):** добавить `require_*_not_box_edition` или аналог на роутеры **`admin_marketing_attribution`** и согласовать с продуктом **ERP attribution refresh / GET с ROI** в `admin_reports`; либо выдать отдельный набор permissions для «коробки» без `attribution.reports.read` / без owner-attribution.
4. **Тесты:** расширить `tests/api/test_admin_rbac_box_cuts.py` (или соседний модуль) на отказ attribution-summary при `EDITION=box`, когда появится gate.
5. **Документация:** корневой `.env.example` уже комментирует `EDITION`; держать в паре с `frontend/.env.example` и `DEV_EXECUTION_PLAYBOOK` §8.

## 11. Роль @LEAD: коммерческая критика (строже QA_ARCH)

Для решений о **коммерческой зрелости** и жёсткой критики «по факту» используется отдельный нормативный документ — он **жёстче** обычных критериев из этого roadmap по требованиям к E2E-доказательствам и вердикту **L0–L3**:

- **`../../LEAD_PRODUCT_GATE_PROTOCOL.md`** (раздел **GATE-6**) — коммерческая критика, L-вердикт L0–L3, метод разборки (шесть блоков), строгая E2E-сетка, шаблон отчёта, DoD релиза; для ассистента при запросе «критическая оценка зрелости» — сначала GATE-6 этого файла.

@QA_ARCH задаёт план улучшений до 8.5+; @LEAD по протоколу отвечает на вопрос «можно ли честно продавать / в каком ограничении», без замены формальным аудитом.

### 11.1 История фиксаций roadmap (фрагмент)

| Дата | Изменение |
|------|-----------|
| 2026-03-26 | §3.2, §4 Phase 1, §6, §7, §10.6, §10.10–**10.11**: внесены замечания **@LEAD** по Box/P5 (сервер vs UI для ROI/атрибуции), синхронизации `EDITION`/`VITE_EDITION`, чеклисту выката и backlog до 8.5+. |

---

## 12. @LEAD — строгий модульный анализ (система целиком, не по частям)

Ниже — не “список хотелок”, а критический разбор как единой коммерческой системы, где важна не только зрелость модулей, но и качество **стыков**.

### 12.1. Модульная карта и зона ответственности

| Модуль | Ответственность | Ключевой риск | Что усиливаем до 8.5+ |
|--------|------------------|---------------|------------------------|
| Booking & Scheduling | запись, слоттинг, календарь, anti double-booking | race condition и овербукинг | DB constraints + транзакционные блокировки + concurrency tests |
| Billing/Payments | оплата, статусы, финансовые события | разрыв “визит завершён / оплаты нет” | transaction map + idempotent handlers + compensating actions |
| ERP Aggregates | витрины, owner-отчёты, ROI/LTV | устаревшие агрегаты и разные источники истины | freshness SLA + source-of-truth policy + reconciliation jobs |
| CRM / Sales Pipeline | лиды, стадии, конверсия | edition drift и частичные box cuts | server-side edition-gates + negative tests + permission profiling |
| Omni Chat & Attention | коммуникации, сигналы риска, AI-подсказки | spam/noise и ложные/пропущенные эскалации | severity routing + digest windows + quality metrics signal-to-noise |
| Tasks/Workstation | операционные задачи, SLA внутри команды | lost updates / reorder conflicts | optimistic concurrency + reorder conflict tests + audit events |
| AI Orchestration | inference, fallback, safety, cost | непрогнозируемый latency/cost и деградация UX | policy timeout/retry/circuit + eval suite + budget guardrails |
| Auth/RBAC/Tenant | доступ, изоляция, edition contracts | горизонтальный обход через “серые” ручки | full permission inventory + deny-by-default + cross-tenant tests |
| API/HTTP Contract | единый error envelope и request context | несовместимость клиентов и “тихие” ошибки | uniform `code`/`trace_id` + contract tests + versioning discipline |
| Data/Infra (Postgres/Redis/Celery) | хранилище, очередь, кэш, фоновые задачи | data loss, queue poison, stale cache | DR drills + queue isolation + cache hygiene + capacity limits |

### 12.2. Критические межмодульные стыки (где ломается коммерческое качество)

1. **Booking -> Payment -> ERP**
   - Инвариант: “финансово завершённый визит” должен быть воспроизводим из событий и агрегатов без ручной коррекции.
   - Риск: partial failure между commit в booking и публикацией события в ERP/job.
   - Усиление: outbox + deterministic replay + reconciliation report “visits vs payments vs erp rows”.

2. **Omni Chat -> Attention -> Tasks**
   - Инвариант: критический сигнал (жалоба, конфликт, no-show риск) не должен теряться и должен превращаться в действие.
   - Риск: информационный шум Telegram/AI скрывает реальные инциденты.
   - Усиление: severity-policy, escalation SLA, метрика “signal-to-action latency”.

3. **CRM/Reports -> Edition/RBAC**
   - Инвариант: Box-ограничения enforce’ятся сервером независимо от UI.
   - Риск: API отдаёт ROI/LTV при прямом вызове с валидным токеном.
   - Усиление: server-side gate на attribution/owner reports + тесты `EDITION=box` на запрет.

4. **Frontend filters -> Backend tenant scope**
   - Инвариант: агрегаты и списки строятся на одном tenant/clinic scope.
   - Риск: “дашборд одно, расписание другое”, если фильтры/контекст расходятся.
   - Усиление: единый контракт контекста клиники + smoke tests “UI filter -> API params -> data consistency”.

5. **AI layer -> HTTP/API SLA**
   - Инвариант: AI-деградация не должна ронять критичные user flows.
   - Риск: длинные таймауты/ретраи блокируют response path.
   - Усиление: bounded latency policy + fallback class + endpoint-level AI budget.

### 12.3. Failure-mode анализ (L1/L2/L3)

| Уровень | Определение | Пример | Ожидаемая реакция системы |
|---------|-------------|--------|---------------------------|
| L1 (degraded) | локальная деградация без потери инвариантов | AI provider timeout | fast fallback + warning metric + no blocker for core CRUD |
| L2 (service incident) | срыв бизнес-функции в одном контуре | queue lag и задержка ERP агрегаций | alert + backlog shedding + recovery runbook |
| L3 (integrity breach) | риск коммерческой/договорной несостоятельности | Box API отдаёт ROI, cross-tenant leak, lost payment event | release stop + incident command + postmortem + hard gate fix |

---

## 13. Усиление стратегии: обязательные контракты между модулями

Для уровня 8.5+ каждый межмодульный поток должен иметь явный контракт:

1. **Data contract**
   - схема payload/version, обязательные поля (`clinic_id`, `trace_id`, `source_event_id`, `occurred_at`).
2. **Reliability contract**
   - timeout budget, retry policy, max attempts, idempotency requirements.
3. **Security contract**
   - permission codes, edition policy, tenant boundary rules.
4. **Observability contract**
   - какие метрики/логи/трейсы считаются “обязательными доказательствами” корректности.
5. **Recovery contract**
   - как сделать replay/backfill/reconcile без ручного SQL и без нарушения инвариантов.

Минимальный DoD для каждого нового/изменённого стыка:
- есть контракт в docs (owner + версия + rollback policy),
- есть минимум 1 negative test и 1 recovery test,
- есть алерт на деградацию стыка,
- есть runbook “как восстановить без data corruption”.

---

## 14. Усиленный backlog @LEAD по всем модулям (приоритет P0–P3)

### P0 (блокирует честный commercial verdict)

1. Закрыть server-side Box gap для `admin_marketing_attribution` и ROI-слоя `admin_reports`.
2. Ввести cross-module reconciliation для цепочки Booking/Payment/ERP (ежедневный отчёт расхождений).
3. Зафиксировать единый deployment contract для пары `EDITION` + `VITE_EDITION` с проверкой на старте и в smoke.

### P1 (блокирует операционную устойчивость)

1. Outbox/inbox + idempotency для event-driven контуров (ERP, Tasks, Notifications).
2. Ввести severity routing + digest batching для Omni/Attention уведомлений.
3. Добавить tenant leak regression suite на API + jobs + aggregates.

### P2 (блокирует масштаб и предсказуемость)

1. Capacity envelope: DB pool, Celery concurrency, Redis memory policy c guardrail-алертами.
2. AI budget governance: p95 latency ceiling + cost per 1k scenarios + fallback success floor.
3. Frontend-backend correlation: обязательный `X-Request-Id` roundtrip в логах и трейсах.

### P3 (улучшает управляемость, но не стоппер релиза)

1. Unified module scorecard: weekly score по каждому модулю и каждому критичному стыку.
2. ADR-пакет по ключевым trade-offs (edition model, tenant model, event consistency model).
3. Game day сценарии не только по инфраструктуре, но и по product integrity (например, “Box bypass attempt”).

---

## 15. Операционный gate-профиль релиза

Для практического `GO / NO-GO` по межмодульным стыкам использовать:

**Режим исполнения roadmap:** dual-track (`BOX` + `ENTERPRISE`) с раздельными критериями готовности и продажности.

- `LEAD_INTEGRATION_GATES.md` — единая матрица `стык -> тесты -> алерты -> runbook -> release gate` с L1/L2/L3 политикой.
- `LEAD_DB_CACHE_AUDIT.md` — специализированный аудит DB/Cache/Celery: контур, риск L1/L2/L3, hardening, owner, срок.
- `LEAD_CICD_SUPPLY_CHAIN_GATES.md` — обязательные security-gates для CI/CD и Docker Hub (scan/sign/provenance/immutable deploy).
  - Для исполнения использовать только mandatory workflow blueprint и anti-bypass policy (без “минимальной” урезанной реализации).
  - Compliance-вердикт фиксировать по шкале `C0..C3` (Definition of Compliance).
- `LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md` — ТЗ на полный аудит экранов и единую дизайн-концепцию Enterprise уровня (типографика, цвета, тени, states, accessibility, P0/P1/P2).
- Результаты исполнения:
  - `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`
  - `DESIGN_SCREEN_AUDIT_MATRIX.csv`
  - `DESIGN_TOKENS_85_PLUS.json`
  - `DESIGN_COMPONENT_MAPPING.md`
  - `DESIGN_P0_P1_BACKLOG.md`
  - `LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md` (поэтапная реализация, delivery gates D1..D6, compliance verdict D0..D3).
  - `LEAD_85_PLUS_RUNWAY_PLAN.md` (единая “взлётная полоса” от pre-flight до финального GO).
  - `LEAD_85_PLUS_RUNWAY_STATUS_V1.md` (фактический статус готовности полосы по доказательствам, без “галочек по умолчанию”).
  - `LEAD_85_PLUS_RUNWAY_STATUS_V1_1_7D.md` (операционный 7-дневный план закрытия критических блокеров).
  - `LEAD_PRODUCT_CRITIQUE_GAP_VS_ENTERPRISE.md` (жёсткая buyer-side критика и требования к коммерческой покупаемости).
  - `LEAD_DUAL_TRACK_BOX_ENTERPRISE_SELLABILITY_PLAN.md` (аудит и стратегия двух пакетов: BOX и ENTERPRISE с отдельными критериями “точно куплю”).
  - `DEV_A_TO_B_EXECUTION_PATH_85_PLUS.md` (единый линейный execution-файл для @DEV: от стабилизации до launch).
  - `BOX_PACKAGE_CONTRACT.md` (контракт продаваемой коробки: входит/не входит, SLA/SLO, evidence, stop-claims).
  - `ENTERPRISE_PACKAGE_CONTRACT.md` (контракт enterprise-пакета: входит/не входит, SLA/SLO, governance evidence, stop-claims).
  - `BOX_SALES_CALL_SCRIPT.md` (скрипт продаж BOX в рамках подтверждённого scope и evidence).
  - `ENTERPRISE_SALES_CALL_SCRIPT.md` (скрипт продаж ENTERPRISE с упором на governance и доказуемость).
  - `SALES_CHEAT_SHEET_BOX_1P.md` (короткая 1-page шпаргалка для BOX-пресейла).
  - `SALES_CHEAT_SHEET_ENTERPRISE_1P.md` (короткая 1-page шпаргалка для ENTERPRISE-пресейла).
  - `SALES_OBJECTION_LIBRARY.md` (единая библиотека возражений и безопасных ответов с привязкой к evidence).