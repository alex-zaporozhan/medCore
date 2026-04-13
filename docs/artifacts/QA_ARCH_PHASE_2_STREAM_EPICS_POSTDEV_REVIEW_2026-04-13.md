# QA_ARCH — повторная приёмка Phase 2 (STREAM epics 2-E1…2-E4) после @DEV

**Дата:** 2026-04-13  
**Инспектор:** @QA_ARCH  
**Контекст:** реализация по [STREAM_PHASE2_RELIABILITY_EPICS.md](../architecture/arch_plan/STREAM_PHASE2_RELIABILITY_EPICS.md), код `domain_outbox`, `bookings` router, `platform_billing_service`, тесты `tests/application/test_domain_outbox_platform_provision.py`.

---

## 1. Вердикт

**Условно принято** для интеграции в основную ветку при зелёном CI: архитектурный сдвиг (outbox для B и booking) соответствует ADR-009 и §17.1 по смыслу; остаются **средние** эксплуатационные и продуктовые зазоры, перечисленные ниже. **Критических** блокеров по целостности данных в сценарии «одна реплика API + нормальный Celery» не выявлено.

---

## 2. Что сделано хорошо (не формально)

- **Транзакционная граница:** enqueue outbox в той же сессии, что доменные изменения (booking, contour A/B).
- **Контур B:** отделение провижининга от «второй фазы» HTTP при включённом флаге; дедуп `platform_signup_provision:{intent_id}`; идемпотентность `execute_platform_provision`.
- **Booking:** единая точка `emit_booking_domain_event`; пост-commit drain на HTTP-маршрутах `bookings`.
- **Наблюдаемость:** существующие gauges outbox + в этом цикле добавлены **`domain_outbox_post_commit_dispatch_failures_total`** и алерт **`DomainOutboxPostCommitDispatchFailures`** (сбой drain после commit не должен маскироваться молча).
- **Тесты:** дедуп, второй пустой batch, симуляция повторной доставки `BookingCreated`, сквозной webhook B + outbox row published.

---

## 3. Критические риски

| Риск | Статус / смягчение |
|------|---------------------|
| **Потеря события при падении dispatch и отсутствии Celery** | Остаётся теоретически, если beat/worker выключены долго. **Смягчение:** алерты по `domain_outbox_pending_rows` / `domain_outbox_oldest_pending_age_seconds`; Celery обязателен в проде по ADR-009. |
| **Двойной путь retry (outbox + `platform_billing.retry_due_provisions`)** | Не критично: оба пути идемпотентны на уровне домена; риск — лишняя нагрузка при сбоях. Мониторить `platform_provision_*` и `domain_outbox_dispatch_total`. |

*Явного 🔴 «данные испорчены при нормальной эксплуатации» не выявлено.*

---

## 4. Средние риски

1. **Внутренние вызовы `BookingService` без `get_session_booking_domain_outbox`** (CRM, omni, AI): события попадают в outbox, но **немедленный** post-commit dispatch не выполняется — задержка до Celery (~30s). Для критичных UX-цепочек (мгновенный lead) возможен лаг.
2. **`patch_booking_admin` при смене `status`:** не эмитит доменные события в outbox/EventBus — расхождение с `cancel_booking` / `complete_booking` / completion service. Риск рассинхрона CRM, если админ массово правит статус через PATCH.
3. **U-009 / DR:** таблица §1 [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) заполнена частично; **фактические** RPO/RTO после реального staging-restore — зона OPS (не «галочка в репо»).
4. **2-F6:** текст ADR-009 не перечисляет все новые env/метрики/алерты — формальный долг до amendment или полного обновления ADR.
5. **Идемпотентность consumer’ов:** покрыта практикой и частью тестов, но **нет** матрицы тестов по каждому handler/типу события (**2-F5** partial).

---

## 5. Формальности (было «для галочки»)

- **Drill:** запись в журнале §6.1 + CI workflow ≠ полноценный PITR на staging без действия OPS.
- **Trivy на PR:** `exit-code: 0` на PR — сознательно не блокирует merge; строгость на `main` — ок; нужен процесс triage findings (**METRICS_PROTOCOL** / SEC не в этом отчёте).

---

## 6. Что сделано в этом же цикле QA_ARCH (усиление)

- Try/except вокруг post-commit `dispatch_domain_outbox_batch` в **`get_session_booking_domain_outbox`** и **`get_session_payment_webhook`** + метрика + алерт.
- Обновление **PHASE_FULL_CLOSURE_BACKLOG**, **07_PHASE_2_RELIABILITY**, **DR_RUNBOOK** §8, **1b-F12**.
- Настоящий артефакт для трассы QA_ARCH.

---

## 7. Следующие этапы (зафиксировано в документации)

| Куда | Что |
|------|-----|
| [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) | Статусы **2-F1** (done + хвост PATCH), **2-F5**, **2-F7**, **1b-F12**; остальные **2-F*** без изменений смысла |
| [07_PHASE_2_RELIABILITY.md](../architecture/arch_plan/07_PHASE_2_RELIABILITY.md) | Статус @DEV, вторая приёмка QA_ARCH, сводная таблица 2-F* |
| [DR_RUNBOOK.md](../operations/DR_RUNBOOK.md) | Строка про `domain_outbox_post_commit_dispatch_failures_total` |
| Этот файл | Полный разбор рисков и вердикт |

**Рекомендованные эпики @DEV (не закрыты в этом PR):**

1. Либо эмит событий из `patch_booking_admin` при смене статуса, либо явный запрет смены статуса через PATCH в пользу узких эндпоинтов (продуктовое решение с @LEAD).
2. Опционально: вызов `dispatch_domain_outbox_batch()` после внутренних mutation-путей `BookingService`, если отложенный Celery недопустим для сценария.
3. Расширение **2-F5:** таблица тестов по `event_type` × критичный side-effect (DB assertion).
4. **2-F6:** правка ADR-009 (env, новые метрики/алерты, семантика «processed rows» в `dispatch_domain_outbox_batch`).

---

## 8. Связанные артефакты

- Первичный обзор Phase 2: [QA_ARCH_PHASE_2_RELIABILITY_REVIEW_2026-04-06.md](./QA_ARCH_PHASE_2_RELIABILITY_REVIEW_2026-04-06.md)
- Поток epics: [STREAM_PHASE2_RELIABILITY_EPICS.md](../architecture/arch_plan/STREAM_PHASE2_RELIABILITY_EPICS.md)
