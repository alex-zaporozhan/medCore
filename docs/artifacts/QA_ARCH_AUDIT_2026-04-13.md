# QA_ARCH — системный аудит резистентности, безопасности, масштаба и наблюдаемости

> **Идентификатор артефакта:** `QA_ARCH_AUDIT_2026-04-13`  
> **Версия документа:** 1.7 (волна 4: формы, админы, инвентаризация роутов, Trivy на PR, матрица OBSERVABILITY, регресс-метрики; см. **часть VI**)  
> **Роль:** @QA_ARCH (см. `docs/ROLE_QA_ARCH.md`)  
>
> **Целевой масштаб (допущение для этого прогона):** до **10 000 клиник**, в каждой до **2 000 клиентов** (пациентов) — оценка **на уровне архитектурных рисков и выборочной верификации кода**, не замена нагрузочного теста.  
> **Связанные артефакты:** `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md`, `docs/METRICS_PROTOCOL.md`, `docs/artifacts/BACKEND_AUDIT_REMEDIATION_PLAN_2026-04-11.md`, `documentation/OBSERVABILITY.md`, `docs/NONFUNCTIONAL_SCORECARD.md` (SLO/perf — по мере появления).

---

## Часть I — План построения критериев оценки

Цель: каждая находка должна маппиться на **измеримый критерий**, а не на субъективное «кажется плохо».

### I.1. Измерения (оси)

| Ось | Критерий «зелёный» (пример) | Критерий «красный» (пример) | Источник истины |
|-----|----------------------------|----------------------------|-----------------|
| **Резистентность** | Явные failure-режимы для внешних зависимостей; идемпотентность retry; outbox/Celery согласованы с ADR | Молчаливые потери событий; двойной side effect при retry | ADR-009, `DOMAIN_OUTBOX_*`, Celery settings |
| **Безопасность** | Tenant boundary на мутациях; секреты не в логах/метриках; webhook verify контракт | IDOR; утечка PII в labels; 2xx при невосможной верификации PSP | `SEC_RBAC_SPEC`, ADR-015, `METRICS_PROTOCOL` §3.3 |
| **Нагрузка / масштаб** | Списки и отчёты с пагинацией/keyset; индексы `(clinic_id, …)` на горячих фильтрах; нет неограниченного full scan в API | O(n) скан таблицы на запрос UI; метрики с взрывом кардинальности | `SAAS_STRENGTHENING_MASTER_PLAN` §31, `ENTERPRISE_SAAS_SCALE_ENVELOPE`, код репозиториев |
| **Кэш** | TTL + инвалидация документированы; нет «вечного» stale без пути обновления | Кэш отдаёт устаревшее после мутации без инвалидации | `docs/CACHE_STRATEGY.md`, `erp_dashboard_cache_*` |
| **Деплой** | Один канон CI/CD для прод-образов; миграции до трафика | Расхождение документации и фактического пайплайна | `Jenkinsfile`, `CI_CD.md`, `AGENTS.md` |
| **Метрики и алерты** | Каждая новая бизнес/техсерия в реестре; алерт с `owner`, `runbook_url`; порог согласован | Метрика без карточки; алерт без владельца; метрика до commit | `METRICS_REGISTRY.md`, `deploy/prometheus/dental_booking_alerts.yml`, тест YAML |
| **Тесты** | Критические цепочки (деньги, слоты, webhook) покрыты integration | Нет теста на новый Celery-путь или на регресс кардинальности | `tests/`, `docs/TESTING_CANON.md` |

### I.2. Шкала статуса находки

| Символ | Значение | Порог приёмки |
|--------|----------|----------------|
| 🔴 | Блокер релиза / нарушение явного контракта без waiver | Требует исправления или письменного решения @LEAD |
| 🟡 | Риск при масштабе или долг техдолга | План с датой/эпиком в этом документе или в бэклоге |
| 🟢 | Соответствует критерию или риск явно зафиксирован и принят | Можно закрыть строку при повторном аудите |
| ⚪ | Информация / наблюдение без немедленного действия | Для знания OPS/ARCH |

### I.3. Допущение по числам 10k × 2k

Пока **не утверждён** отдельный envelope-документ с RPS и профилем чтения/записи (@LEAD), числа **10 000 × 2 000** используются как **стресс-рамка для порядка величин** (до **2×10⁷** записей пациентов в БД при полном заполнении — оценка верхней границы; реальная наполняемость ниже). Любой вывод «достаточно масштабируется» без k6/JMeter — **условный** и помечается 🟡.

---

## Часть II — План маршрута аудита от точки A к точке B

**Точка A:** политика и канон (документы выше + `DOCUMENTATION_POLICY.md`).  
**Точка B:** зафиксированный реестр находок + приоритизированный бэклог повторных проходов.

### II.1. Фазы обхода (порядок выполнения аудита)

| # | Фаза | Что смотрим | Артефакты / код |
|---|------|-------------|-----------------|
| 1 | **Периметр и деплой** | Jenkins vs GHA, секреты, compose, миграции | `Jenkinsfile`, `.github/workflows/`, `docker-compose.yml`, `alembic/versions/` |
| 2 | **Аутентификация и RBAC** | JWT, founder, patient slug, rate limits | `src/core/config.py`, `src/core/security.py`, middleware |
| 3 | **Деньги A/B** | Идемпотентность, webhook verify, reconcile, outbox | `payment_service`, `platform_billing`, `payment_local_pending_reconcile_*`, `domain_outbox` |
| 4 | **Данные и конкуренция** | Слоты, partial unique, advisory lock, транзакции | `booking_slot_policy`, `booking_service`, миграции booking |
| 5 | **Async и очереди** | Celery ack/prefetch, Redis per-loop, webchat fan-out | `celery_app.py`, `redis_client.py`, `webchat_push_manager.py` |
| 6 | **Кэш и отчёты** | ERP vitrine, dashboard cache, replica | `CACHE_STRATEGY.md`, `erp_*`, `health/replica` — **доп. прогон 2** зафиксирован в §IV.2 / QA-AUDIT-009 |
| 7 | **Наблюдаемость** | Метрики, кардинальность, алерты, пробелы | `metrics.py`, `METRICS_REGISTRY.md`, `dental_booking_alerts.yml` |
| 8 | **Фронт и E2E** | CI-smoke при `FRONTEND_E2E_URL`: страницы админки/PWA + денежные/канбан сценарии (`tests/e2e/`); глубокий UX по `ROLE_QA_ARCH` — отдельные `QA_REPORT_*` | `tests/e2e/test_frontend_pages.py` и др.; Jenkins/GHA см. QA-AUDIT-015 |

Между фазами: обновление **Части IV** этого файла; при массовых находках — вынос эпика в отдельный `QA_REPORT_*` по модулю (см. `ROLE_QA_ARCH.md`).

---

## Часть III — В каком виде сохраняется отчёт по каждому пункту

Все находки ведутся в **Части IV** в единой таблице. Допускается приложение: ссылка на PR, на строку лога, на имя теста.

### III.1. Обязательные поля строки находки

| Поле | Описание |
|------|----------|
| **ID** | `QA-AUDIT-NNN` (монотонно в рамках файла) |
| **Дата** | ISO дата обнаружения |
| **Ось** | Резистентность / Безопасность / Масштаб / Кэш / Деплой / Метрики / Тесты |
| **Статус** | 🔴 🟡 🟢 ⚪ |
| **Критерий** | Ссылка на строку из Части I (например «Масштаб § индексы») |
| **Наблюдение** | Что именно увидели |
| **Доказательство** | Путь файла, имя метрики, имя алерта, команда проверки |
| **Риск при 10k×2k** | Кратко: «низкий» / «средний» / «высокий» + почему |
| **Рекомендация** | Конкретное действие или «эскалация @ARCH/@OPS» |
| **Тест-пробел** | Да/Нет + какой тест добавить |

### III.2. Правило закрытия

Строка переводится в 🟢 только если есть **ссылка на merge** или явное «принято @LEAD» в комментарии к строке.

---

## Часть IV — Реестр находок

**Волна 1 (2026-04-13):** документы + выборочный grep/read.  
**Волна 2 (тот же день, «отдельный прогон»):** сверка **фазы 6** с `docs/CACHE_STRATEGY.md` по контуру ERP dashboard cache; **инвентарь** части admin list-эндпоинтов (приложение §IV.2); **фаза 8** — не ручной UX-разбор, а **зафиксированное наличие** Playwright-smoke в CI при поднятом фронте (см. QA-AUDIT-020).  
**Волна 3 (код / @PRINCIPLE):** пагинация маркетинга (admin + public), AI conflicts, RBAC users; бакетирование метрик CRM/waitlist/paperless/AI task manager; prod-cap outbox; логи ERP Redis-кэша; `scripts/perf_smoke.py` — см. строки **001, 003, 006, 010, 013, 019** и §IV.2.  
**Волна 4 (хвосты реестра):** `admin_forms` (templates/submissions + cap export), `admin/admins` list; `scripts/inventory_list_scalar_all.py` + тест; `perf_smoke` — тайминг max latency; Trivy FS **exit-code 1** на PR; черновик матрицы в `documentation/OBSERVABILITY.md`; §2.1 perf в `NONFUNCTIONAL_SCORECARD.md`; тест «нет `clinic_id` в `metrics.py`».

Полный перебор **каждого** HTTP-роута и ручная приёмка UI остаются разумным долгом; они **не блокируют** закрытие этой волны аудита как «методология + критические риски + хвосты в реестре».

| ID | Дата | Ось | Статус | Критерий | Наблюдение | Доказательство | Риск при 10k×2k | Рекомендация | Тест-пробел |
|----|------|-----|--------|----------|------------|----------------|-----------------|--------------|-------------|
| QA-AUDIT-001 | 2026-04-13 | Масштаб / Метрики | 🟡 | METRICS_PROTOCOL §3.3 кардинальность | **Сейчас:** в `src/core/metrics.py` **нет** строки `clinic_id` (CI: `tests/core/test_metrics_prometheus_no_clinic_id_label.py`); горячие контуры на **`clinic_bucket`**. **Остаётся 🟡:** новые серии вне этого файла; Grafana уже на `clinic_bucket` в репозитории | `src/core/metrics.py`; `tests/core/test_metrics_prometheus_no_clinic_id_label.py` | Низкий для TSDB по текущему модулю | Чеклист PR на новые `_total` | Частично — тест + ревью |
| QA-AUDIT-002 | 2026-04-13 | Тесты | 🟢 | Критические цепочки покрыты | Добавлены тесты: patient/platform reconcile + Celery task; моки `YooKassaClient` / `PaymentService` / `_checkout_return_url` | `tests/application/test_payment_local_pending_reconcile.py` | Низкий | Расширить при появлении новых веток reconcile (другие провайдеры) | Нет |
| QA-AUDIT-003 | 2026-04-13 | Нагрузка | 🟡 | Нет неограниченного сканирования | **Сейчас:** `perf_smoke` печатает max latency; `PERF_SMOKE_TIMEOUT_SECONDS`; зачаток зафиксирован в **`docs/NONFUNCTIONAL_SCORECARD.md` §2.1**. k6/Jenkins + цифры RPS/p95 — **впереди** | `scripts/perf_smoke.py`, `perf/README.md`, `docs/NONFUNCTIONAL_SCORECARD.md` | Высокий для маркетинговых утверждений без цифр | Сценарии бронь/webhook/отчёт + заполнить baseline в scorecard | Да — по решению @LEAD |
| QA-AUDIT-004 | 2026-04-13 | Наблюдаемость | 🟢 | Алерты с owner и runbook | В `dental_booking_alerts.yml` правила содержат `labels.owner`, `severity`, `annotations.runbook_url` | `tests/deploy/test_prometheus_alert_rules_yaml.py` (регресс в CI) | Низкий | Поддерживать при добавлении правил | Нет (есть тест YAML) |
| QA-AUDIT-005 | 2026-04-13 | Наблюдаемость | 🟡 | Покрытие метрик ↔ алерты | ~**36** named alerts; **частично закрыто:** черновик матрицы (якорные пары + указание на YAML) в **`documentation/OBSERVABILITY.md`**. Полная машинно-читаемая матрица «все метрики → алерты» — **впереди** | `documentation/OBSERVABILITY.md`; `deploy/prometheus/dental_booking_alerts.yml` | Средний без расширения матрицы | Дополнять таблицу при новых `alert:`; опционально codegen из YAML | Частично |
| QA-AUDIT-006 | 2026-04-13 | Масштаб | 🟡 | Пагинация списков | Закрыто: всё из волны 3 + **forms** (templates/submissions `skip`/`limit` 2000/5000, export `submission_limit` 5000/10000) + **`GET /admin/admins`** (500/2000). **Остаток:** omni/tasks/platform и др. — `scripts/inventory_list_scalar_all.py` + §IV.2 | `admin_forms.py`, `admin_admins.py`; `scripts/inventory_list_scalar_all.py`; `tests/scripts/test_inventory_list_scalar_all.py` | Средний для непокрытых list-роутов | Пройти инвентарь; пагинация по приоритету объёма данных | Частично |
| QA-AUDIT-007 | 2026-04-13 | Резистентность | 🟢 | Webchat Redis fan-out | Исправлен риск дубликатов при таймауте long-poll (возврат `[]` без DB-replay окна) | `src/application/services/webchat_push_manager.py`, `tests/core/test_webchat_poll_redis_fanout.py` | Низкий после фикса | Мониторить `webchat_redis_fanout_total`; при росте подписок — пул соединений Redis | Нет для таймаута; 🟡 для нагрузки на Redis SUB |
| QA-AUDIT-008 | 2026-04-13 | Деплой | 🟢 | Канон CI/CD | Прод-образы и deploy — Jenkins + GHCR; GHA — дополнение; задокументировано в корне | `AGENTS.md`, `CI_CD.md` | Низкий при соблюдении | Не объявлять GHA единственным gate для релизного образа | Нет |
| QA-AUDIT-009 | 2026-04-13 | Кэш | 🟢 | TTL + инвалидация (`CACHE_STRATEGY` §5–§7, §9) | **Ключ** включает `clinic_id` (`erp_report_cache.dashboard_cache_key`). **TTL:** `erp_dashboard_cache_ttl_seconds` (дефолт 60). **Инвалидация:** `invalidate_clinic_erp_report_cache` — `SCAN`+`DEL` по префиксу `erp:rpt:v1:{clinic_id}:*` после refresh витрин (`admin_reports` → `background_tasks`). **Деградация:** при ошибке Redis GET — `None` → промах, запрос к БД. **Метрики:** `erp_dashboard_cache_requests_total`, `invalidations_total` | `src/application/services/erp_report_cache.py`, `src/api/v1/routers/admin_reports.py`, `src/core/config.py` | Низкий при штатном Redis | Прочие кэши (`staff_directory_cache` и т.д.) — по мере изменения кода | Нет для ERP-слоя |
| QA-AUDIT-010 | 2026-04-13 | Резистентность | 🟢 | Явные failure-режимы / retry | **Dev/staging:** по умолчанию **0** (без лимита). **Production:** если `DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS` **не задан** в env, `Settings._apply_production_outbox_dispatch_cap` выставляет **50**; явный `0` в env = без лимита | `src/core/config.py`; `tests/test_settings_outbox_prod_defaults.py` | Низкий при соблюдении runbook на «застрявшие» строки | Runbook: карантин строк с `attempts >= cap`; мониторинг `domain_outbox_blocked_by_attempt_cap_rows` | Частично — outbox-тесты |
| QA-AUDIT-011 | 2026-04-13 | Масштаб | 🟢 | Пагинация списков | Было: полная выборка. **Сейчас:** `skip`/`limit` с дефолтом **2000**, макс. **5000** на визиты, диагнозы, файлы | `admin_patient_medical.py`; тесты `tests/api/test_admin_patient_medical.py` | Низкий при соблюдении лимита; >5k — догрузка страницами | При необходимости поднять max через @ARCH + версионирование API | Нет |
| QA-AUDIT-012 | 2026-04-13 | Масштаб | 🟢 | Пагинация списков | Было: все логи. **Сейчас:** `skip`/`limit` (2000 / 5000), сортировка `created_at desc` | `admin_recall.py`; `tests/api/test_admin_recall_list_limits.py` | Низкий | То же | Нет |
| QA-AUDIT-013 | 2026-04-13 | Безопасность / Наблюдемость | 🟢 | Секреты/PII не в логах | При ошибке Redis GET/SET кэша дашборда в лог уходит **`cache_key_sha256_16`** (укороченный SHA-256), без полного ключа | `src/application/services/erp_report_cache.py` | Низкий | При необходимости — sample rate логов в prod | Нет |
| QA-AUDIT-014 | 2026-04-13 | Безопасность | 🟢 | Supply chain | Trivy FS: **`exit-code: 1`** на **PR и main** при CRITICAL (блок merge до triage/bump) | `.github/workflows/security-trivy.yml` | Низкий при процессе triage в PR | При ложных срабатываниях — `.trivyignore` / bump зависимостей по политике команды | Нет |
| QA-AUDIT-015 | 2026-04-13 | Деплой / Тесты | 🟢 | Канон CI/CD + критические цепочки | `Jenkinsfile` описывает стадию тестов с **ruff + полный pytest + vite preview** (паритет с GHA backend-ci) при `RUN_TESTS` | `Jenkinsfile` (комментарий и stage «Tests…» ~стр. 59+) | Низкий при включённых credentials БД/Redis | OPS: не отключать `RUN_TESTS` на main без waiver | Нет |
| QA-AUDIT-016 | 2026-04-13 | Масштаб | 🟢 | Пагинация (контрпример) | Список пациентов админки: `limit` по умолчанию **100**, `skip` | `src/api/v1/routers/patients.py` (`get_patients`) | Низкий | Зафиксировать в чеклисте фазы 6 как эталон для остальных списков | Нет |
| QA-AUDIT-017 | 2026-04-13 | Наблюдаемость | 🟢 | Метрика ↔ алерт (частичное закрытие QA-AUDIT-005) | Для серий **M-R1–R3** из ремедиации есть именованные правила в Prometheus | `deploy/prometheus/dental_booking_alerts.yml` (`ERP_NightlyRunPartialFailures`, reconcile `payment_local_pending_*`, `WebchatRedisFanoutPublishErrors`) | Низкий | Расширить матрицу на все `_total` из `METRICS_REGISTRY.md` | Частично (`test_prometheus_alert_rules_yaml`) |
| QA-AUDIT-018 | 2026-04-13 | Масштаб | 🟢 | Пагинация списков | Было: неограниченные recall lists + N+1 по сегментам. **Сейчас:** `skip`/`limit` (2000/5000) на segments/templates/campaigns/automations; сортировка `created_at desc`. **Остаётся:** по одному `get_segment_patient_count` на строку **страницы** (не полный cartesian) | `admin_recall.py`; `tests/api/test_admin_recall_list_limits.py` | Низкий для ответа API; 🟡 при сотнях сегментов на странице — кэш/батч счётчиков | Опционально: батч-подсчёт пациентов по segment_id | Частично |
| QA-AUDIT-019 | 2026-04-13 | Масштаб | 🟢 | Пагинация списков | **Admin:** `skip`/`limit` (2000/5000) на posts/stories; AI conflicts — агрегаты summary по полному диапазону + **страница** `items` с SQL `LIMIT`. **Public PWA:** `feed` (default 100, max 500) и `stories` (default 50, max 200) | `admin_marketing.py`, `admin_ai_reports.py`, `public_marketing.py`; тесты `test_admin_marketing_list_limits`, `test_admin_ai_conflicts_pagination`, `test_public_marketing_limits` | Низкий для перечисленных эндпоинтов | Фронт: догрузка страниц при > лимита | Нет для контура 019 |
| QA-AUDIT-020 | 2026-04-13 | Тесты / Деплой | 🟢 | Фаза 8 (минимальный контур) | Playwright: обход маршрутов админки/PWA (`test_frontend_pages.py`), сценарии денег/брони/канбана в `tests/e2e/`; в CI при `FRONTEND_E2E_URL` + vite preview (**QA-AUDIT-015**) | `tests/e2e/` | Низкий как gate «нет белого экрана»; не заменяет UX-приёмку | Отдельные `QA_REPORT_*` по экранам из `ROLE_QA_ARCH.md` | Частично (E2E есть; UX-рубрики вне этого файла) |

*Примечание к QA-AUDIT-005:* строка **QA-AUDIT-017** и раздел в **`documentation/OBSERVABILITY.md`** не отменяют потребность в полной таблице «все метрики → алерты → панели», но фиксируют якоря и процесс расширения.

### IV.2 — Приложение А: инвентарь list-ответов (прогоны 2–4, выборочно)

Критерий колонки **«Ограничен»:** явный `limit`/`skip` в query или жёсткий cap в SQL / заведомо малая кардинальность (справочник).

| Область | Эндпоинт / файл | Ограничен | Примечание |
|---------|----------------|------------|-------------|
| Пациенты | `GET /patients` | Да | `limit`≤100 по умолчанию, `patients.py` |
| Поиск | admin patient search | Да | `limit`≤50, `admin_search.py` |
| Услуги | `admin_services` list | Да | cap 1000 |
| Медицина | визиты / диагнозы / файлы | Да | skip/limit 2000/5000 |
| Recall | segments, templates, campaigns, automations, logs | Да | skip/limit 2000/5000 |
| Маркетинг (admin) | posts, stories | Да | `skip`/`limit` 2000/5000, `admin_marketing.py` |
| Маркетинг (public PWA) | `feed`, `stories` | Да | default 100 / max 500 (feed); 50 / 200 (stories), `public_marketing.py` |
| AI отчёты | conflicts за период | Да | summary агрегатами; `items` с `skip`/`limit` 2000/5000 |
| RBAC | `GET …/rbac/users` | Да | `skip`/`limit` default 500, max 2000, `admin_rbac_management.py` |
| Админы клиники | `GET /admin/admins` | Да | default 500, max 2000, `admin_admins.py` |
| Формы | `GET …/forms/templates`, `…/submissions` | Да | skip/limit 2000/5000; export: `submission_limit` 5000 default, 10000 max |
| CRM | `GET …/crm/leads` | Да | page/page_size + cursor (канбан), `admin_crm.py` |
| Публичный каталог SaaS | plans/options | Да | мало строк, `public_platform_catalog.py` |
| Омни / задачи / прочее | множество `scalars().all()` | Инвентарь | `poetry run python scripts/inventory_list_scalar_all.py` (`--markdown` для таблицы) |

---

## Часть V — Бэклог следующих проходов (A→B продолжение)

Приоритизация «одной дорожкой» и принципы масштаба — **часть VII**; ниже — расширенный чеклист с привязкой к строкам реестра.

1. **Инвентарь HTTP-роутов** — §**IV.2** + `scripts/inventory_list_scalar_all.py`; закрывать хвосты **006** по приоритету (omni inbox messages, tasks board, …); новые list — **limit/skip или keyset** (эталон: **QA-AUDIT-016**).
2. **Метрики и кардинальность** — регресс **001**: тест на отсутствие `clinic_id` в `metrics.py`; новые серии — только с бакетами/низкой кардинальностью.
3. **Матрица метрика → алерт → дашборд** — расширять **`documentation/OBSERVABILITY.md`** и **§V.1** (**QA-AUDIT-005**).
4. **Нагрузочный контур и SLO** — `perf_smoke` + **§2.1** scorecard; далее k6/Jenkins и заполнение baseline (**QA-AUDIT-003**).
5. **Плоскость чтения БД** — операционная политика: тяжёлые отчётные GET при наличии `DATABASE_REPLICA_URL` — с **reporting session** и `DB_REPORTING_STATEMENT_TIMEOUT_MS`; периодический `EXPLAIN` на роуты из инвентаря §IV.2 (**связь с I.1 «Масштаб»**).
6. **Security pass:** `pip-audit` + Trivy FS на PR (**014** 🟢); секреты, CORS, rate limits — периодический проход.
7. **Фронт (сверх E2E):** векторы из `ROLE_QA_ARCH.md` — `QA_REPORT_*` по экранам (**QA-AUDIT-020** не заменяет это).
8. **Outbox ops:** runbook для строк за cap и ручного карантина (**QA-AUDIT-010** — prod default cap **50** при отсутствии env).
9. **N+1 на странице recall** — при росте числа сегментов на странице: батч-подсчёт пациентов по `segment_id` или кэш (**QA-AUDIT-018**, опционально).

### V.1 — Черновик матрицы (новые серии ремедиации)

| Метрика | Алерт (имя в YAML) | Примечание |
|---------|-------------------|------------|
| `erp_aggregate_nightly_run_total{result="partial_failures"}` | `ERP_NightlyRunPartialFailures` | Окно 30h — покрывает суточный beat |
| `payment_local_pending_reconcile_total{result="error"}` | `PaymentLocalPendingReconcileErrors` | Порог: `sum(rate(...[1h])) > 0` |
| `webchat_redis_fanout_total{op="publish",result="error"}` | `WebchatRedisFanoutPublishErrors` | Порог по `rate` 5m |

---

## Часть VI — Закрытие волны: «аудит закончен?»

**Для волны 1–2 (артефакт `QA_ARCH_AUDIT_2026-04-13`, до **v1.4** включительно) — да по заявленному охвату:** выполнены обещанные отложенные шаги: **фаза 6** (сверка ERP dashboard cache с `CACHE_STRATEGY.md`), **частичный инвентарь списков** (§IV.2), **фаза 8 в объёме CI-smoke** (**QA-AUDIT-020**), обновлены вводные к **части IV** и **части II**.

**Как процесс живой продукт — нет:** в реестре остаются 🟡 (**001, 003, 005, 006**) — полный perf, полная матрица метрик, обход omni/tasks. **Волна 4 (v1.7)** закрыла **014**; сдвинула **005** (док), **006** (формы, админы, скрипт), **003** (scorecard §2.1 + тайминг smoke), **001** (тест регресса).

**Версии 1.5–1.7:** **1.5** — @PRINCIPLE (**§VII**); **1.6** — волна 3 код/реестр; **1.7** — хвосты 005/006/014/003/001 и операционные артефакты.

---

## Часть VII — Синтез @PRINCIPLE: «свободная» масштабируемость

Цель раздела: зафиксировать **архитектурный смысл** масштаба для этого репозитория — не как маркетинговый лозунг, а как набор **снимаемых потолков**, согласованных с реестром (часть IV) и бэклогом (часть V).

### VII.1. Определение (критерий принципа)

Масштабируемость здесь означает: **ограниченная работа на один HTTP-запрос**, **предсказуемые побочные эффекты при retry** (Celery/outbox), **наблюдаемость с ограниченной кардинальностью** TSDB и **доказуемый** (хотя бы smoke) профиль нагрузки при утверждённом envelope @LEAD. Добавление только реплик API без этих свойств переносит узкое место в БД, Redis или Prometheus.

### VII.2. Семь рычагов (карта к находкам)

| # | Рычаг | Суть | Якоря в реестре / коде |
|---|--------|------|-------------------------|
| 1 | **Граница ответа API** | Пагинация (`skip`/`limit` или keyset), жёсткий max, стабильная сортировка; нет неограниченного `scalars().all()` на UI-контурах | **006, 011–012, 016–019**; эталон пагинации — пациенты |
| 2 | **Метрики** | High-frequency: **не** размножать ряды по `clinic_id`; использовать **`clinic_bucket_label`** (`src/core/prometheus_labels.py`) или агрегаты без идентификатора тенанта в labels | **001**; `METRICS_PROTOCOL` |
| 3 | **Плоскость данных** | Read replica для тяжёлых GET, `DB_REPORTING_STATEMENT_TIMEOUT_MS`, индексы `(clinic_id, …)`, пулы и лимиты соединений согласованы с профилем нагрузки | `Settings` / `admin_reports`; **I.1 Масштаб** |
| 4 | **Асинхронность** | Конечное число попыток dispatch outbox + карантин/runbook; идемпотентность задач при `acks_late` | **010**; ADR-009 |
| 5 | **Кэш и логи** | TTL + инвалидация по канону; при ошибках кэша — **не** писать в лог полный ключ Redis с tenant-идентификатором | **009, 013**; `CACHE_STRATEGY.md` |
| 6 | **Горизонталь API** | Stateless инстансы + общий Redis (rate limit, webchat, кэш); при росте подписок — мониторинг и пулы к Redis | **007** (fan-out); **008, 015** (деплой) |
| 7 | **Доказуемость** | Минимальный perf-smoke (k6/Locust или стадия Jenkins) + зафиксированные SLO/допущения, иначе выводы при 10k×2k остаются **условными** | **003**; `NONFUNCTIONAL_SCORECARD` |

### VII.3. Приоритет исполнения (одна дорожка)

Порядок согласован с убыванием «удара по потолку» при фиксированном объёме разработки:

1. **Остатки списков** — инвентарь `inventory_list_scalar_all.py`; закрытие **006** по приоритету.  
2. **Метрики** — **001**: тест + ревью новых серий.  
3. **Outbox** — **010** закрыт; runbook впереди.  
4. **Perf** — **003**: smoke + scorecard §2.1; k6/Jenkins + baseline.  
5. **Матрица метрика → алерт → панель** — **005**: расширять `OBSERVABILITY.md` (и **017**).  
6. **Логи кэша** — **013** закрыт; **014** — Trivy строгий на PR.

### VII.4. Анти-паттерны (явно не масштаб)

- Объявлять систему «готовой к 10k клиник» без **артефакта нагрузки** и без ограничений на list-эндпоинтах.  
- Вводить новую высокочастотную метрику с лейблом `clinic_id` «для удобства дебага» без waiver в реестре.  
- Оставлять **неограниченный retry** outbox в проде: явный `DOMAIN_OUTBOX_MAX_DISPATCH_ATTEMPTS=0` без runbook карантина (дефолт без env — cap **50**, см. **010**).  
- Путать **E2E-smoke** (**020**) с приёмкой UX и с нагрузочным профилем.

---

## История версий документа

| Версия | Дата | Изменение |
|--------|------|-----------|
| 1.0 | 2026-04-13 | Первичная методология + базовый реестр находок (QA-AUDIT-001…009) |
| 1.1 | 2026-04-13 | Продолжение аудита: outbox cap, неограниченные списки (медицина, recall logs), лог Redis-ключа, Trivy на PR, контрпример пагинации пациентов, черновик матрицы метрика↔алерт (QA-AUDIT-010…017) |
| 1.2 | 2026-04-13 | Код: `skip`/`limit` (default 2000, max 5000) для медицинских списков и recall logs; тесты; **QA-AUDIT-011/012** → 🟢; новая строка **QA-AUDIT-018** (recall segments) |
| 1.3 | 2026-04-13 | Recall: пагинация для segments/templates/campaigns/automations; тесты reconcile + Celery; **QA-AUDIT-002** 🟢, **QA-AUDIT-018** 🟢 (с примечанием про N+1 на странице) |
| 1.4 | 2026-04-13 | **Закрытие «отдельного прогона»:** фаза 6 — **QA-AUDIT-009** 🟢 (ERP cache vs `CACHE_STRATEGY.md`); §**IV.2** инвентарь списков; фаза 8 — **QA-AUDIT-020** 🟢 (Playwright в CI); новые строки **019** (хвосты пагинации), уточнён **006**; границы волны описаны во введении к ч. IV |
| 1.5 | 2026-04-13 | **@PRINCIPLE:** часть **VII** (семь рычагов, приоритет, анти-паттерны); усилен **§V** (реплика/reporting, метрики, N+1 recall, ссылка на `NONFUNCTIONAL_SCORECARD`); уточнена строка **QA-AUDIT-001** (`prometheus_labels.py`); примечание в **ч. VI** о границах v1.5 |
| 1.6 | 2026-04-13 | **Волна 3 / код:** синхронизация реестра с реализацией — **001** (бакеты), **003** (`scripts/perf_smoke.py`, `perf/README.md`), **006** (уже́), **010** (prod cap), **013** (fingerprint ключа), **019** (admin+public маркетинг, AI conflicts); пагинация **RBAC users**; обновлены **§IV.2**, **§V**, **§VI**, **§VII.3** |
| 1.7 | 2026-04-13 | **Волна 4 / хвосты:** **006** — forms + admins + `inventory_list_scalar_all.py`; **005** — матрица в `documentation/OBSERVABILITY.md`; **014** — Trivy `exit-code: 1` на PR; **003** — `NONFUNCTIONAL_SCORECARD` §2.1, тайминг `perf_smoke`; **001** — `test_metrics_prometheus_no_clinic_id_label.py`; тесты лимитов; обновлены **§IV.2**, **§V**, **§VI**, **§VII.3** |
