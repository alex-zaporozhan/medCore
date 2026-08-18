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

## 8) Фронт и HTTP-мост (артефакты)

Не блокирует недели 1–8 по бэкенду; фиксирует связь с кодом и отложенные эпики.

- **Выравнивание с 8W (отложенное):** `./ARCH_FRONTEND_85_PLUS_ALIGNMENT.md` — таймауты `fetch`, code-splitting, OTel RUM, приём `X-Request-Id` на бэкенде/ingress; таблица и списки перформанса «на потом» (§6–§8).
- **База прод-фронта (зафиксировано по техпаспорту / @QA_ARCH):** `./ARCH_FRONTEND_ENTERPRISE_BASELINE.md` — маршруты, guard’ы, клиент `client.ts`, TanStack Query; закрытие фаз **0–5** `ARCH_FRONTEND_TECH_PASSPORT_DEV_IMPLEMENTATION_PLAN.md`: фазы **0–4** (API-слой — техпаспорт **v1.5.3**; структура §4 — **v1.5.4**, баррели + `hooksBarrelParity.test.ts`); **фаза 5** — §5 техпаспорта (**v1.5.5–v1.5.6**): `queryKeys.ts`, доменные хуки, CRM/adminAi ключи, `useAdminAiSettings`, guards attention-feed, тест `queryKeys.test.ts`; план **v1.6.5**.

