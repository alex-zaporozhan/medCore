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

### 3.2. Основные разрывы (gaps) до 8.5+

- **Неполная отказоустойчивость интеграций:** нет системного retry/backoff/circuit breaker паттерна.
- **Backup/DR не production-уровня:** backup есть, но restore-процесс не доведен как регулярная проверяемая практика.
- **Нагрузочная емкость не доказана:** отсутствует строгий perf baseline с SLO.
- **Мультитенанси ограничен row-level изоляцией:** нужен усиленный контроль isolation/authorization на всех путях.
- **RAG как полноценная система отсутствует:** есть AI, но нет retrieval pipeline/vector layer.

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
