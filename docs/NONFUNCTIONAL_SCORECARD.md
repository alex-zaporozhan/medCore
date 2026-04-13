# NONFUNCTIONAL_SCORECARD — живой учёт NFR (по ARCHITECTURE_EXCELLENCE_PASSPORT)

> **Назначение:** зафиксировать **факты и цели** нефункциональной зрелости конкретного проекта.  
> **Нормы и чеклисты:** `docs/ARCHITECTURE_EXCELLENCE_PASSPORT.md`.  
> **Поставка «коробки» (SME):** упрощённый обязательный минимум — `docs/artifacts/SME_BOX_NFR_CHECKLIST.md` (не заменяет этот scorecard для Enterprise).  
> **Бэклог идей по NFR после P0:** `docs/operations/BACKLOG_NFR.md`.  
> **Владелец обновлений:** @LEAD; проверка полноты доказательств — @QA_ARCH.

Обновляй таблицы после замеров, релизов, drill и аудитов. Указывай **дату** и **источник** (дашборд, отчёт CI, ручной замер).

---

## 1. Сводная оценка (веса из паспорта §3)

| Категория | Вес | Оценка 0–10 (факт) | Цель | Дата оценки | Примечание / ссылка на доказательство |
|-----------|-----|-------------------|------|-------------|----------------------------------------|
| Reliability & Resilience | 20% | | | | |
| Security & Compliance | 20% | | | | |
| Performance & Scalability | 15% | | | | |
| Data Integrity & Transactions | 10% | | | | |
| Observability & Incident Response | 10% | | | | |
| Architecture & Code Quality | 10% | | | | |
| AI Integration Quality | 10% | | | | |
| Delivery Discipline | 5% | 6 | 8 | 2026-03-24 | Backend CI `.github/workflows/backend-ci.yml`; frontend — `frontend-ci.yml` |

**Итоговая взвешенная оценка (черновик):** ___ / 10 — дата: ___

---

## 2. KPI-ориентиры (паспорт §3.1) — baseline и цели

| Метрика | Ориентир из паспорта | Baseline (факт) | Дата baseline | Цель команды | Дата замера |
|---------|----------------------|-----------------|---------------|--------------|-------------|
| Доступность API (рабочее окно) | ≥ 99,5% | | | | |
| p95 критичных API (без тяжёлого AI) | ≤ 300–500 ms | | | | |
| Доля 5xx на бизнес-критичных ручках | < 1% | | | | |
| MTTR P1/P2 | ≤ 60 мин | | | | |
| RPO | задокументирован | | | | |
| RTO | задокументирован | | | | |
| Restore drill | по регламенту @LEAD | локальный Docker OK 2026-03-24; CI `restore-drill.yml` (см. `DR_DRILL_LOG.md`) | 2026-03-24 | staging в облаке — строка в журнале | TBD |
| Security (critical в SCA/образах) | 0 на релизной ветке | pip-audit в CI без игнора; Trivy FS на PR и main (`security-trivy.yml`, fail на CRITICAL); JWT на PyJWT (CONTRIBUTING.md) | 2026-04-13 | 0 critical в слоях образа в реестре — @LEAD | 2026-03-24 |

Добавляй строки под свой продукт (очередь, AI fallback rate, error budget и т.д.).

---

## 2.1 Нагрузка — стартовый контур (QA_ARCH QA-AUDIT-003)

| Артефакт | Назначение |
|----------|------------|
| `scripts/perf_smoke.py` | Минимальный HTTP GET-smoke против `PERF_SMOKE_BASE_URL` (см. `perf/README.md`). |
| `scripts/inventory_list_scalar_all.py` | Список `scalars().all()` в `src/api/v1/routers/*.py` для приоритизации пагинации. |

**Baseline RPS / p95** для критичных сценариев (бронь, webhook, отчёт) — зафиксировать здесь после первого прогона k6/Jenkins по envelope @LEAD.

---

## 3. Решения @LEAD / ADR, влияющие на цифры

| Дата | Тема | Ссылка (ADR / PR / документ) |
|------|------|------------------------------|
| | | |

---

## 4. История снимков (кратко)

| Дата | Что изменилось | Кто |
|------|----------------|-----|
| 2026-03-24 | Ссылка на `docs/operations/BACKLOG_NFR.md` в шапке; идеи NFR вынесены из `LEAD_FIRST_RUN_OPS.md` | @DEV |
| 2026-03-24 | QA follow-up: PyJWT, pip-audit без CVE-игнора, mypy (security), README, DR staging checklist, docker-images aligned | @DEV |
| 2026-03-24 | P0: Trivy FS, restore-drill CI, tenant audit в backend-ci, PII-тесты | @DEV |
| 2026-03-24 | P0: deps bump (FastAPI 0.135, Starlette 0.49, multipart 0.0.22, black 26); full ruff; pip-audit gate; локальный restore drill | @DEV |
| 2026-04-13 | QA_ARCH: §2.1 старт perf (`perf_smoke`, инвентарь list-роутов) — см. `docs/artifacts/QA_ARCH_AUDIT_2026-04-13.md` v1.7 | @QA_ARCH |
| | Шаблон scorecard; файл в `docs/` (универсальный для проекта) | |
