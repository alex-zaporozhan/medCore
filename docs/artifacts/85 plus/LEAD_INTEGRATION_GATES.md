# LEAD_INTEGRATION_GATES — Operational Release Gates по межмодульным стыкам

> **Роль:** @LEAD  
> **Назначение:** единый операционный документ “стык -> тесты -> алерты -> runbook -> release gate” для решения `GO / NO-GO` на релизе.  
> **Принцип:** зелёный тест без evidence и recovery-пути не считается подтверждённой зрелостью.

---

## 1) Как использовать документ

1. Заполняется на каждый релиз (staging и prod отдельно).
2. Каждая строка интеграционного стыка должна иметь:
   - тестовое доказательство (авто/ручной smoke),
   - operational signal (метрика/алерт),
   - подтверждённый runbook,
   - verdict по gate.
3. Любой `NO-GO` по L3-блоку блокирует релиз.
4. Если evidence отсутствует, это автоматически `NO-GO`.

---

## 2) Severity и политика gate

| Уровень | Класс | Политика |
|--------|-------|----------|
| L1 | Degraded (локальная деградация) | релиз допустим при workaround и owner-фиксации в ближайший спринт |
| L2 | Service incident risk | релиз только по explicit waiver @LEAD + @OPS с датой закрытия |
| L3 | Integrity/commercial breach | безусловный `NO-GO` до исправления и ретеста |

---

## 3) Gate matrix по критичным стыкам

| ID | Стык | Основной риск | Обязательные тесты | Обязательные алерты/метрики | Runbook | Release gate |
|----|------|---------------|--------------------|-------------------------------|---------|--------------|
| G1 | Booking -> Payment -> ERP | partial commit, lost event, финансовое расхождение | integration test на atomicity; replay/idempotency test; daily reconcile check | `booking_payment_erp_mismatch_rate`; `event_to_erp_latency_p95`; `reconcile_fail_count` | `RUNBOOK_RECONCILE_BOOKING_PAYMENT_ERP.md` | `NO-GO`, если mismatch > 0.5%/сутки или reconcile не выполнен |
| G2 | Omni -> Attention -> Tasks | критический сигнал не превращается в действие | e2e test: conflict/escalation -> task created; anti-dup test | `signal_to_action_latency_p95`; `escalation_without_task_count`; `notification_dedup_drop_rate` | `RUNBOOK_OMNI_ATTENTION_ESCALATION.md` | `NO-GO`, если есть потерянные critical эскалации |
| G3 | CRM/Reports -> Edition/RBAC | Box bypass и утечка enterprise-функций | negative API tests при `EDITION=box`; smoke 403 `box_forbidden` на CRM/retention/attribution | `box_forbidden_hit_rate`; `box_endpoint_200_count`; `edition_mismatch_detected` | `RUNBOOK_BOX_EDITION_SMOKE.md` | `NO-GO`, если любой запрещённый box endpoint отдаёт 200 |
| G4 | Frontend filters -> API tenant scope | несогласованность данных и tenant drift | e2e: dashboard/list consistency; contract test на clinic filter propagation | `tenant_scope_mismatch_count`; `ui_api_filter_mismatch_rate` | `RUNBOOK_TENANT_SCOPE_VALIDATION.md` | `NO-GO`, если есть подтверждённый cross-tenant drift |
| G5 | AI -> API SLA | AI деградация ломает core UX и SLA API | timeout/fallback tests; load test с AI unavailable | `ai_timeout_rate`; `ai_fallback_success_rate`; `api_p95_with_ai_degraded` | `RUNBOOK_AI_DEGRADED_MODE.md` | `NO-GO`, если fallback < floor или p95 выходит за agreed budget |
| G6 | API -> Celery/Queue -> DB write | queue lag, poison tasks, delayed side effects | job retry/idempotency tests; poison isolation test; replay test | `queue_lag_seconds`; `poison_task_count`; `job_final_failure_rate` | `RUNBOOK_QUEUE_RECOVERY_REPLAY.md` | `NO-GO`, если queue lag превышает SLA без mitigation |
| G7 | Auth/RBAC -> Admin modules | privilege escalation через неполный permission check | RBAC deny tests по admin P4-P7; regression на permission inventory | `rbac_deny_test_failures`; `unexpected_admin_2xx_count` | `RUNBOOK_RBAC_INCIDENT_RESPONSE.md` | `NO-GO`, если deny-тесты падают на релизной ветке |
| G8 | Restore -> App readiness | формальный restore без рабочей бизнес-цепочки | DR restore drill + smoke критичных flows после restore | `restore_duration`; `post_restore_smoke_pass_rate`; `data_integrity_post_restore` | `DR_RUNBOOK.md` | `NO-GO`, если restore не подтверждает работоспособность flows |

---

## 4) Единый чеклист evidence (заполнять на релиз)

| Поле | Что фиксируем |
|------|----------------|
| Release ID | версия, commit SHA, дата/время |
| Environment | staging/prod |
| Gate ID | G1..G8 |
| Test evidence | ссылка на pipeline/job/report |
| Metrics snapshot | ссылка на dashboard/график с временным окном |
| Alert status | firing/quiet + комментарий |
| Runbook readiness | ссылка на runbook + дата последней валидации |
| Verdict | GO / GO-WAIVER / NO-GO |
| Decision owner | кто подписал решение |
| Follow-up actions | что делаем после релиза и до какой даты |

---

## 5) GO / NO-GO rules (жёсткие)

1. Любой L3 дефект по G1/G3/G4/G7 = `NO-GO`.
2. Отсутствие runbook по G1/G3/G8 = `NO-GO`.
3. Отсутствие актуального smoke evidence (<24h до релиза) по G3/G4/G8 = `NO-GO`.
4. `GO-WAIVER` допускается только для L2 и только с:
   - подписанием @LEAD и @OPS,
   - планом фикса,
   - датой закрытия не позднее следующего релизного цикла.

---

## 6) Минимальный smoke pack перед продом

1. `EDITION=box` smoke:
   - `/api/v1/admin/crm/*` -> `403` + `code=box_forbidden`
   - retention/attribution enterprise routes -> ожидаемый запрет
2. Integrity smoke:
   - тестовый визит -> оплата -> ERP обновление в SLA
3. Tenant smoke:
   - запросы с токенами разных клиник не пересекают данные
4. Recovery smoke:
   - проверка runbook-ready и доступности процедур replay/reconcile
5. AI degraded smoke:
   - при искусственном timeout провайдера core API остаётся в SLA

---

## 7) Ownership и ритм пересмотра

- **Владелец документа:** @LEAD (A)
- **Операционный владелец исполнения:** @OPS (R)
- **Качество evidence и тестов:** @QA_ARCH (R)
- **Технические исправления по gate-fail:** @DEV (R), @ARCH (C)

Пересмотр:
- еженедельный на 8W треке,
- обязательный перед каждым prod релизом,
- внеочередной после любого L2/L3 инцидента.

---

## 8) Связанные артефакты

- `QA_ARCH_85_PLUS_ROADMAP.md` (разделы 12-14)
- `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md` (разделы 10-12)
- `DR_RUNBOOK.md`
- `NONFUNCTIONAL_SCORECARD.md`
- `LEAD_DB_CACHE_AUDIT.md`
- `LEAD_CICD_SUPPLY_CHAIN_GATES.md`
