# QA_ARCH — ревью исполнения Phase 0 / governance после @DEV (2026-04-06)

> **Поток:** [STREAM_PHASE0_AND_GOVERNANCE.md](../architecture/arch_plan/STREAM_PHASE0_AND_GOVERNANCE.md)  
> **Роль:** [ROLE_QA_ARCH.md](../ROLE_QA_ARCH.md)  
> **Исполнение @DEV (база ревью):** секрет контура A, `payment_webhook_governance`, `enterprise_scale_envelope`, `scripts/phase0_governance_preflight.py`, workflows `release-gate.yml` / `dr-restore-drill.yml`, вынесение `unified_http_exception_handler`, `ENTERPRISE_SAAS_TARGET.md`, изоляция `domain_outbox` в pytest.

## Вердикт

**Принято** для инженерного контура Phase 0: автоматизация и код закрывают риски U-006 / U-008 / U-009 и снимают регрессию тестов (ранний импорт `main` vs outbox).  
**Процессные артефакты LEAD (2026-04-06):** [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](./LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md) (0-Q1…0-Q3, 0-F2, 0-F3 §2b), [LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md](./LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md) (**2-F8** / **PRC-E4**); журнал drill — [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) §6.1 (**2-F2** partial до RPO/RTO §1). **Вне среза:** **PRC-G1** / **0-F1** (утверждение чисел envelope).

---

## Что сделано хорошо

1. **U-006 (разведение A/B):** отдельный секрет и заголовок для контура A, `secrets.compare_digest`, жёсткий `RuntimeError` при совпадении секретов A и B, предупреждения в prod при «дырявом» контуре A при включённой YooKassa.
2. **Надёжность тестов:** `DELETE FROM domain_outbox` autouse в `test_domain_outbox_payment.py` устраняет зависимость от порядка модулей и лимита батча dispatch.
3. **Архитектурная гигиена:** `unified_http_exception_handler` вынесен из `main` — коллекция pytest не тянет полный роутер ради §28-тестов; снижен риск скрытых побочных эффектов при импорте.
4. **CI:** явный **release gate** на тег + `workflow_dispatch`; **DR restore drill** в активных workflows с ручным запуском (без скрытого cron).
5. **0-F1 в коде:** константы envelope в одном модуле + smoke-тест.
6. **0-F3 (частично):** появился файл `ENTERPRISE_SAAS_TARGET.md`, скрипт проверяет наличие цепочки путей; ссылка из `INDEX.md`.

---

## Критические риски (🔴)

| ID | Риск | Статус после усиления QA_ARCH |
|----|------|--------------------------------|
| R-C1 | **Контур A без секрета в prod** — endpoint остаётся без shared-secret, только предупреждение в лог | **Открыто.** Нормативно: для prod с YooKassa задать `PATIENT_PAYMENT_WEBHOOK_SECRET` + edge ACL; опционально жёсткий fail в будущем — согласовать с SEC/LEAD (может сломать старые интеграции). |
| R-C2 | **PRC-G1 / LEAD** не подкреплён кодом | **Вне репо:** без подписи LEAD по envelope заявлять L3 нельзя — см. [STREAM_PRODUCTION_READINESS.md](../architecture/arch_plan/STREAM_PRODUCTION_READINESS.md). |

---

## Средние риски (🟡)

| ID | Риск | Что сделано в этом цикле | Хвост |
|----|------|---------------------------|--------|
| R-M1 | OpenAPI / §28 для webhook A не документировал специфику 403/400/500 | Добавлены `response_model`, `summary`, `responses` на маршруте; раздел в [API_PUBLIC_ERROR_CODES.md](../architecture/API_PUBLIC_ERROR_CODES.md) | При необходимости — примеры `content` в OpenAPI (сейчас усилены описания + глобальные схемы роутера) |
| R-M2 | Метрика `payment_webhook_failures_total` не была в реестре | Строка **M-A1** в [METRICS_REGISTRY.md](./METRICS_REGISTRY.md); уточнён help в `metrics.py` | Карточка M-A1 по METRICS_PROTOCOL — **1b-F11** / @PRINCIPLE |
| R-M3 | Нет per-IP rate limit на **контур A** (у B есть) | **Закрыто:** `RATE_PATIENT_PAYMENT_WEBHOOK_*`, см. [payments.py](../../src/api/v1/routers/payments.py) | Edge/nginx — по желанию (**10-Q4**) |
| R-M4 | **U-008:** release-gate не заменяет полное включение e2e/security из `workflows_disabled` | **Закрыто политикой LEAD:** [LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md](./LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md) | Физическое включение workflow — отдельный тикет |
| R-M5 | **U-009:** CI drill ≠ staging drill с датой в DR_RUNBOOK | **Частично:** §6.1 в [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) с датой | Staging PITR + RPO/RTO §1 — OPS |

---

## Формально / поверхностно

- **`ENTERPRISE_SAAS_TARGET.md`** — якорь 0-F3 + таблица **§2b** (2026-04-06); детальный TARGET-текст по разделам МП по-прежнему у LEAD/ARCH.
- **`enterprise_scale_envelope.py`** — константы не пронизывают все list-endpoints (не было задачи на массовый рефакторинг пагинации).
- **Crash-review (0-F2):** pytest-бандл + решение LEAD §0-F2 в [LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md](./LEAD_PHASE0_GOVERNANCE_DECISIONS_2026-04-06.md).

---

## Недоделано (зафиксировано в бэклоге)

См. [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) — **0-F1** / **PRC-G1** (envelope); **2-F2** хвост (RPO/RTO §1 DR_RUNBOOK).

---

## Трассировка артефактов

| Артефакт | Назначение |
|-----------|------------|
| `scripts/phase0_governance_preflight.py` | 0-F1 print / 0-F3 paths / 0-F2 pytest bundle |
| `.github/workflows/release-gate.yml` | U-008 — gate на тег `v*` |
| `.github/workflows/dr-restore-drill.yml` | U-009 — воспроизводимость restore в CI |
| [QA_ARCH_PHASE0_GOVERNANCE_DEV_REVIEW_2026-04-06.md](./QA_ARCH_PHASE0_GOVERNANCE_DEV_REVIEW_2026-04-06.md) | этот отчёт |

---

**Подпись процесса:** QA_ARCH (инженерная приёмка кода и документов репозитория). **PRC-E4** / **PRC-E2** обновлены в [STREAM_PRODUCTION_READINESS.md](../architecture/arch_plan/STREAM_PRODUCTION_READINESS.md) по артефактам LEAD выше.
