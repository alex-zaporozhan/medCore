## QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER — исполняемый трекер на 8 недель

> **Цель:** довести проект до подтвержденного уровня **8.5+** по non-functional quality.  
> **Роли:** `@ARCH` (решения/дизайн), `@QA_ARCH` (валидация/риски/DoD), `@DEV` (реализация), `@OPS` (операционка/инциденты).  
> **Формат:** каждая неделя = конкретные deliverables + метрики “до/после” + критерий приемки.

---

## 1) Operating model (как работаем, чтобы не утонуть)

1. **ARCH отвечает за “что и почему”**  
   - архитектурные решения, trade-offs, целевые инварианты, ADR.

2. **QA_ARCH отвечает за “доказать, что не бутафория”**  
   - проверка KPI, тест-покрытия рисков, failover drills, отчетность.

3. **DEV отвечает за “сделано и стабильно”**  
   - код, тесты, миграции, обратная совместимость.

4. **OPS отвечает за “работает в проде”**  
   - monitoring, alerting, backup/restore, runbooks, on-call readiness.

---

## 2) Target KPI dashboard (фиксируем на старте и трекаем еженедельно)

- API p95 latency (critical routes)
- Error rate (4xx/5xx, отдельно 5xx)
- Queue lag / oldest task age
- DB saturation (pool utilization, slow queries)
- Redis health (memory, evictions, latency)
- AI provider timeout/error/fallback rates
- Restore success rate + restore duration
- Security findings (critical/high)
- Migration safety rate (успех upgrade + отсутствие критичных совместимостей)
- Anti double-booking rate (кол-во зафиксированных конфликтов слотов/аномалий)

> В Week 1 обязателен baseline snapshot. Без baseline нельзя честно говорить про “рост качества”.

---

## 3) 8-week execution plan

## Week 1 — Baseline, risks, and hard gates

### Deliverables
- Создан `NONFUNCTIONAL_SCORECARD.md` (веса, KPI, текущее значение, цель).
- Создан `RISK_REGISTER_85_PLUS.md` (top-20 рисков с вероятностью/impact/mitigation).
- Подключены quality gates в CI:
  - backend `ruff` + `pytest`
  - frontend `build` + `vitest`
  - dependency scan + secret scan
  - fail-on-critical security findings
- Зафиксирован стартовый perf baseline (top-10 API).

### Acceptance criteria
- Есть один артефакт с baseline-метриками и датой измерения.
- CI блокирует merge при критичных security findings.

---

## Week 2 — Reliability policy for external calls and jobs

### Deliverables
- Единая policy библиотека: timeout + retry + backoff+jitter + error envelope.
- Применение policy к AI-клиенту и критичным integration call sites.
- Celery policy: retries, max attempts, retry delay, error classification.
- Идемпотентный подход для критичных write/notification flows (idempotency key/source_event_id).

### Acceptance criteria
- Для выбранных критичных jobs доля transient failures снижается.
- Появились метрики retry attempts/success/final failure.

---

## Week 3 — Transaction correctness and idempotency

### Deliverables
- Карта транзакционных границ: booking -> payment -> completion -> ERP -> tasks.
- Идемпотентность для критичных write paths (idempotency key/source_event_id).
- Тесты на rollback/partial failure для ключевых цепочек.
- Outbox/inbox (или эквивалент) для надежной цепочки event -> async job -> write.
- Anti double-booking для слотов (констрейнты/блокировки + regression test).

### Acceptance criteria
- Нет дублей в проверяемых сценариях повторной доставки/повторного вызова.
- Есть минимум 5 e2e/integration тестов на transactional invariants.
- Anti double-booking регрессия дает “нулевую” частоту аномалий в параллельном тестовом сценарии.

---

## Week 4 — Backup, restore, and DR minimum

### Deliverables
- DB-level backup strategy (`pg_dump`/snapshot policy) с retention.
- `DR_RUNBOOK.md` + пошаговый restore процесс.
- Migration safety: правила backward/forward compatibility + документированный rollout/rollback регламент.
- Первый restore drill в staging с фиксацией времени и итогов.

### Acceptance criteria
- Документально подтвержден успешный restore.
- Зафиксированы RPO/RTO и фактические значения из drill.
- Migration safety: upgrade проходит без критичных совместимостей (и есть документированный rollback/regression check).

---

## Week 5 — Observability 2.0

### Deliverables
- Structured logs стандарт (trace_id, clinic_id, actor, operation, result).
- OpenTelemetry tracing (минимум для критичных endpoint chains).
- Alert rules: error budget burn, queue lag, DB/Redis saturation, AI outages.
- SLO/SLA черновики (минимум для 3 критичных цепочек) и правила алертинга/эскалации.

### Acceptance criteria
- По P1/P2 инциденту можно пройти полный trace от API до async job.
- Есть alert test report (срабатывание и проверка маршрута эскалации).

---

## Week 6 — Performance and capacity

### Deliverables
- k6/Locust сценарии для ключевых user flows.
- Capacity report: DB pools, worker concurrency, Redis memory profile.
- Performance budgets (p95/p99) на release.
- Performance regression gate в CI (или nightly) относительно baseline.

### Acceptance criteria
- Достигнуты целевые p95 по agreed critical paths.
- Есть зафиксированный максимум безопасной нагрузки и bottleneck map.

---

## Week 7 — Security and tenant safety deep pass

### Deliverables
- RBAC matrix + негативные тесты (запреты по ролям/tenant boundaries).
- Cross-tenant leak tests для API/queries/jobs.
- Логирование и маскирование PII в logs/AI payload.
- Security headers/CORS/CSRF проверка (особенно админка) + негативные тесты.

### Acceptance criteria
- 0 critical security findings.
- Пройден набор tenant isolation regression tests.

---

## Week 8 — Interview-grade package and final 8.5+ audit

### Deliverables
- Финальный `QA_ARCH_85_PLUS_AUDIT.md` с оценкой по scorecard.
- “Evidence pack”: KPI trends, drills, outages handled, lessons learned (без акцента на собеседование, но с операционными доказательствами).
- Production readiness checklist + roadmap на следующий квартал.

### Acceptance criteria
- Итоговая оценка >= 8.5 по согласованной матрице.
- Есть подтверждение улучшений цифрами, а не описаниями.

---

## 4) Weekly reporting template (копировать каждую неделю)

### Week N Report
- **Done:**  
- **Not done / why:**  
- **Risks appeared:**  
- **KPI delta (before -> after):**  
- **Incidents and learnings:**  
- **Plan for next week:**  

---

## 5) RACI for critical streams

- **Reliability stream:** ARCH (A), DEV (R), QA_ARCH (C), OPS (R)
- **Security stream:** ARCH (C), DEV (R), QA_ARCH (A), OPS (R)
- **Performance stream:** ARCH (C), DEV (R), QA_ARCH (A), OPS (R)
- **DR/Backup stream:** ARCH (C), DEV (C), QA_ARCH (A), OPS (R)
- **AI quality stream:** ARCH (A), DEV (R), QA_ARCH (R), OPS (C)

---

## 6) Ответ на вопрос: нужен ли @ARCH?

Коротко: **да, нужен обязательно**. Но в текущей цели его нужно использовать не “как единственный источник истины”, а как часть пары:

- `@ARCH` — делает сильные решения и целевую модель.
- `@QA_ARCH` — приземляет в проверяемую реальность и выявляет самообман.

Если оставить только одну роль:
- только ARCH -> риск “красивой архитектуры без доказательств”;
- только QA_ARCH -> риск “критика без системного design direction”.

Для уровня 8.5+ нужна именно **связка ARCH + QA_ARCH + измеримые KPI**.

---

## 7) Definition of success for this tracker

Трекер считается выполненным, когда:

1. Есть 8 недель отчетов с KPI delta.
2. Есть минимум 1 успешный restore drill и 1 game day.
3. Есть perf report с доказанной емкостью и bottleneck plan.
4. Есть security report без критичных дыр.
5. Финальная оценка по scorecard >= 8.5.

---

## 8) Задел: фронтенд и HTTP-мост (стыковка с неделями 1–8)

Основной объём трекера — **бэкенд, данные, очереди, DR, SLO**. Параллельно зафиксирована **база фронта** (маршруты, единый `client.ts`, корреляция): `docs/artifacts/ARCH_FRONTEND_ENTERPRISE_BASELINE.md`.

Ниже — пункты, **сознательно не смешивавшиеся** с техпаспортом в одном PR, чтобы не ломать целостность; их развитие привязано к неделям 8W и отдельным эпикам:

| Задел | Суть | Когда имеет смысл (8W / эпик) |
|-------|------|-------------------------------|
| **Таймауты `fetch` / `AbortSignal` по умолчанию** | Без согласования SLA эндпоинтов и UX — риск ложных обрывов. | Week **2** (политика вызовов) + Week **6** (бюджеты); отдельный эпик фронта. |
| **Code-splitting бандла** (снятие предупреждения Vite о крупном чанке) | Продуктовое решение, влияет на FCP/LCP и кэш. | Week **6** (performance budgets + сценарии нагрузки). |
| **Browser OTel / RUM** | Полноценная трассировка в браузере — отдельная инфраструктура и PII. | Week **5** (после structured logs/trace на API). |
| **Логирование `X-Request-Id` на бэкенде / прокси** | Фронт уже шлёт заголовок; нужен приём в логах и проброс через ingress. | Week **5** (сквозная корреляция при инцидентах). |

**Детальная карта** «неделя → фронт / мост → бэкенд» и критерии приёмки для **браузерный `X-Request-Id` → access/app logs**: `docs/artifacts/ARCH_FRONTEND_85_PLUS_ALIGNMENT.md`.

---

## 9) Презентационное наполнение и AI — backlog, привязанный к фактам кода

| Тема | Факт сейчас | Действие / эпик |
|------|-------------|------------------|
| Демо-данные | Старые `seed_demo_*` с «Демо пациент» и одной клиникой | Использовать `seed_presentation_showcase.py` + план `docs/artifacts/QA_ARCH_PRESENTATION_SEED_PLAN.md`; для сброса — пустая БД + `alembic upgrade head`. |
| RBAC на пустой БД | Глобальные роли могли не попасть без архивной миграции | Запуск `seed_rbac_baseline.py` (или вызов из презентационного сида). |
| AI не отвечает | Часто `omni_ai_settings`=DISABLED или нет `AI_PROVIDER_BASE_URL` в контейнере | Проверить `.env` для Docker; включить `SUGGEST_ONLY`/`AUTO_REPLY` на BUSINESS; см. §10.4 в `QA_ARCH_85_PLUS_ROADMAP.md`. |
| Attention vs Omni | Conflict-items из `chat_messages`, не из `omni_messages` | Продукт: единый pipeline анализа или явно разделить UX; Week 5–7 observability + AI. |
| Смены админов | Нет модели | Отдельная фича; не блокирует 8W technical track. |
| Сеть клиник в админке | Один логин — одна клиника | **Эпик:** единый логин + переключатель клиники; **дашборды:** отчёт по одной / по всем — см. §10.2 в `QA_ARCH_85_PLUS_ROADMAP.md` и backlog в `QA_ARCH_PRESENTATION_SEED_PLAN.md`. |
| Дашборд «8 записей / расписание пусто» | Разные источники: KPI «все клиники» vs брони только по JWT-клинике | **Сделано:** дефолт фильтра клиники на дашборде + якорные брони в `seed_presentation_showcase` — см. §10.8 в `QA_ARCH_85_PLUS_ROADMAP.md`. |
| CRM воронка пустая | Не был сидирован пайплайн/стадии | **Сделано:** сид воронки + семантика стадий + карточки лидов. |
| Финансы: нет касс | Не сидировались `Cashbox` | **Сделано:** три кассы + политики зарплат. |
| Один админ в UI | Один owner в демо | **Сделано:** `manager@dentapro.demo` + роль manager. |
| Абонементы «не видны» | UI только по UUID | **Backlog:** поиск по ФИО; сид печатает UUID первого пациента. |

---

## 10) @LEAD upgrade: модульно-стыковой трек (обязательно для 8.5+)

Этот блок добавляет к недельному плану контроль не только модулей, но и **межмодульных контрактов**, потому что именно там чаще всего рождаются коммерческие инциденты.

**Dual-track execution mode (обязательно):**
- Каждую неделю фиксируются **2 отдельных статуса**: `BOX sellability` и `ENTERPRISE sellability`.
- Нельзя закрывать недельный этап как “успешный”, если есть только один общий статус без разделения по пакетам.

### 10.1. Критичные стыки, которые трекаются каждую неделю

| Стык | KPI | Failure signal | Owner |
|------|-----|----------------|-------|
| Booking -> Payment -> ERP | mismatch rate (визиты/оплаты/агрегаты) | расхождение > 0.5% за сутки | DEV + QA_ARCH |
| Omni -> Attention -> Tasks | signal-to-action latency p95 | эскалации без созданной задачи > SLA | DEV + OPS |
| CRM/Reports -> Edition/RBAC | box bypass attempts | 200 там, где должен быть `403 box_forbidden` | QA_ARCH |
| Frontend filters -> API tenant scope | data consistency pass rate | dashboard/list inconsistency | DEV |
| AI -> API latency/SLA | AI timeout/fallback rate | p95 вылетает за budget или fallback < floor | DEV + OPS |

### 10.2. Gate policy по стыкам (merge/release)

1. **PR gate:** без negative test на изменённый стык PR не merge’ится.
2. **Release gate:** любой L3 breach по стыку (tenant leak, box bypass, payment integrity gap) = stop release.
3. **Ops gate:** без runbook для recovery/reconcile стык считается “непринятым” даже при зелёных тестах.

---

## 11) Усиление недель 1–8: что добавить к уже запланированному

### Week 1 (добавить)
- Инвентаризация всех критичных стыков и назначение owner’ов.
- Стартовый “integration integrity baseline” (не только API perf baseline).

### Week 2 (добавить)
- Reliability policy распространяется на **межсервисные стыки**, а не только на внешние вызовы.
- Метрики retries/failures публикуются с разрезом по business-flow (`booking_flow`, `erp_flow`, `omni_flow`).

### Week 3 (добавить)
- Reconciliation test suite для цепочки Booking/Payment/ERP (дубли/потери/partial commit).
- Контракт идемпотентности для jobs (источник ключа, TTL, поведение при replay).

### Week 4 (добавить)
- DR drill включает не только restore БД, но и проверку “ключевые стыки реально работают после restore”.
- Отдельный сценарий “queue replay после restore” с оценкой side effects.

### Week 5 (добавить)
- Трейс от frontend request до Celery job completion обязателен для 2 бизнес-цепочек.
- Alert на “stuck integration” (событие создано, downstream эффект не наступил в SLA).

### Week 6 (добавить)
- Performance budgets на стыки: event-to-action latency и freshness latency для ERP/отчётов.
- Capacity test включает деградационные режимы (AI unavailable, Redis pressure).

### Week 7 (добавить)
- Security deep pass включает Box/P5 API bypass suite.
- Tenant safety тестируется и на async jobs/aggregates, не только на REST-ручках.

### Week 8 (добавить)
- Финальный аудит включает “module + integration maturity map” с вердиктом по каждому стыку.
- Evidence pack содержит post-incident replay: как система восстановилась без data corruption.

---

## 12) Definition of Done v2 (строго для @LEAD)

К исходным критериям трекера добавляются обязательные:

1. Нет открытых L3 рисков по критичным стыкам.
2. Для каждого P0/P1 стыка есть owner, runbook и monitoring signal.
3. Box/edition инварианты проверены серверными тестами и post-deploy smoke.
4. Есть регулярный reconciliation report для цепочки Booking/Payment/ERP.
5. Финальный вердикт формируется по двум осям: **качество модулей** + **качество взаимодействий**.

---

## 13) Артефакт релизного решения (GO / NO-GO)

Операционный шаблон и политика решения по межмодульным стыкам:

- `LEAD_INTEGRATION_GATES.md`
- `LEAD_DB_CACHE_AUDIT.md` (фактический аудит DB/Redis/Celery для мультиклиники и Enterprise)
- `LEAD_CICD_SUPPLY_CHAIN_GATES.md` (security-gates по CI/CD и Docker Hub для release `GO / NO-GO`)
  - Включает **mandatory workflow blueprint** и anti-bypass rules (build-only/push-only не допускаются).
  - Включает `Definition of Compliance (C0..C3)` для формального релизного вердикта.
  - Включает `Release Compliance Report` шаблон (обязательное заполнение на каждый релиз).
- `LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md` (ТЗ для полного UI audit + unified enterprise design concept в логике 85+)
- `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` (единая дизайн-концепция Enterprise уровня)
- `DESIGN_SCREEN_AUDIT_MATRIX.csv` (аудит экранов и ключевых UI контуров)
- `DESIGN_TOKENS_85_PLUS.json` (дизайн-токены для внедрения во frontend theme/design system)
- `DESIGN_COMPONENT_MAPPING.md` (legacy -> canonical component mapping)
- `DESIGN_P0_P1_BACKLOG.md` (дизайн-backlog внедрения)
- `LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md` (пошаговый execution-план внедрения дизайн-пакета с gates D1..D6 и итоговым verdict D0..D3)
- `LEAD_85_PLUS_RUNWAY_PLAN.md` (линейный сценарий запуска A->B->GO с pre-flight, stop-lines и Definition of Successful Takeoff)
- `LEAD_85_PLUS_RUNWAY_STATUS_V1.md` (честный evidence-based статус полосы: GREEN/YELLOW/RED/UNKNOWN без фиктивных “done”)
- `LEAD_85_PLUS_RUNWAY_STATUS_V1_1_7D.md` (7-дневный day-by-day план закрытия красных зон runway)
- `LEAD_PRODUCT_CRITIQUE_GAP_VS_ENTERPRISE.md` (сверх-строгая бизнес-критика продукта и gap-анализ до enterprise-покупаемости)
- `LEAD_DUAL_TRACK_BOX_ENTERPRISE_SELLABILITY_PLAN.md` (двухпутевой план: BOX “продаём сейчас” + ENTERPRISE “доращиваем без паузы”)
- `DEV_A_TO_B_EXECUTION_PATH_85_PLUS.md` (единый пошаговый путь для @DEV от A до B без переключения между множеством файлов)
- `BOX_PACKAGE_CONTRACT.md` (жёсткий коммерческий контракт BOX: scope/SLA/evidence/stop-claims)
- `ENTERPRISE_PACKAGE_CONTRACT.md` (жёсткий коммерческий контракт ENTERPRISE: scope/SLA/evidence/stop-claims)
- `BOX_SALES_CALL_SCRIPT.md` (пресейл-скрипт BOX: discovery -> fit -> value -> commit, без ложных claims)
- `ENTERPRISE_SALES_CALL_SCRIPT.md` (пресейл-скрипт ENTERPRISE: governance discovery + evidence-based продажа)
- `SALES_CHEAT_SHEET_BOX_1P.md` (1-page шпаргалка BOX: 10 вопросов, 10 stop-фраз, 10 safe claims)
- `SALES_CHEAT_SHEET_ENTERPRISE_1P.md` (1-page шпаргалка ENTERPRISE: 10 вопросов, 10 stop-фраз, 10 safe claims)
- `SALES_OBJECTION_LIBRARY.md` (библиотека возражений: safe responses + evidence links + stop answers)
