# SME / Box NFR checklist — минимум для коммерческой «коробки»

> **Назначение:** отделить **обязательные** нефункциональные требования поставки Salon/Dental Box от полного scorecard Enterprise (`docs/NONFUNCTIONAL_SCORECARD.md`, `docs/artifacts/85 plus/QA_ARCH_85_PLUS_ROADMAP.md`).  
> **Владелец:** @LEAD; проверка полноты — @QA_ARCH перед релизом коробки.

**Статус репозитория (2026-03):** пункты SME, которые можно закрыть кодом и CI (backup-скрипт, drill в Actions, Trivy FS, PII, tenant audit, теги образов, чеклисты smoke/drill), отражены в таблицах ниже. Операционный контур (cron backup в проде, при необходимости staging drill в журнале, prod-smoke, скан образов в реестре) остаётся у @LEAD.

Коробка **не обязана** закрывать distributed tracing, game days, полный SLO-программу и RAG в аналитике. Она **обязана** быть безопасной для данных клиентов и восстановимой после сбоя.

---

## 1. Данные и непрерывность (must)

| # | Требование | Критерий «готово» |
|---|------------|-------------------|
| 1.1 | Регулярный backup БД | В репозитории: скрипт и пример cron — [`BACKUP_SCHEDULE.md`](../operations/BACKUP_SCHEDULE.md), `scripts/ops/backup_postgres.sh`. Конкретное окно и retention — в политике деплоя @LEAD. |
| 1.2 | Документированный restore | [`DR_RUNBOOK.md`](../operations/DR_RUNBOOK.md) — шаги и проверки; ответственный — по регламенту @LEAD |
| 1.3 | Restore drill | Журнал: [`DR_DRILL_LOG.md`](../operations/DR_DRILL_LOG.md). Минимум: успешный **CI** job `.github/workflows/restore-drill.yml` (еженедельно + `workflow_dispatch`) + локальный Docker в `DR_RUNBOOK.md` §4. Staging в облаке — строка в журнале при появлении контура. |
| 1.4 | Миграции | `alembic upgrade head` из чистой БД — воспроизводимая схема; нет «висящих» ревизий |

---

## 2. Безопасность и доступ (must)

| # | Требование | Критерий «готово» |
|---|------------|-------------------|
| 2.1 | Секреты | Нет секретов в git; `.env.example` без реальных ключей; ротация по регламенту |
| 2.2 | RBAC | Матрица ролей для коробки задокументирована; негативные сценарии (нет доступа к чужому tenant) проверены вручную или тестами |
| 2.3 | Supply chain | CI: `pip-audit` без игнора (`.github/workflows/backend-ci.yml`) + **Trivy FS** `.github/workflows/security-trivy.yml` (CRITICAL в lock). Образы: теги по `github.sha` в `.github/workflows/docker-images.yml`; скан **слоёв образа в реестре** — по политике @LEAD, первый прогон: [`LEAD_FIRST_RUN_OPS.md`](../operations/LEAD_FIRST_RUN_OPS.md) §2 |
| 2.4 | PII | Реализация и env: [`PII_LOGGING.md`](../operations/PII_LOGGING.md); `LOG_MASK_PII` в `.env.example`. |

---

## 3. Поставка и качество (must, упрощённо)

| # | Требование | Критерий «готово» |
|---|------------|-------------------|
| 3.1 | CI | Backend: lint + tests + tenant ORM audit (`scripts/audit_tenant_columns.py` в CI); Frontend: build + tests — зелёные на релизной ветке |
| 3.2 | Версионирование образов | `moircreator/dental-booking-*:${{ github.sha }}` + `:main` + `:latest` в `docker-images.yml` |
| 3.3 | Smoke после деплоя | Чеклист: [`DEPLOY_SMOKE.md`](../operations/DEPLOY_SMOKE.md); prod-smoke — шаг оператора после выката; **первый прогон:** [`LEAD_FIRST_RUN_OPS.md`](../operations/LEAD_FIRST_RUN_OPS.md) §1 |

---

## 4. Первый прогон @LEAD / ops (не закрывается коммитом)

То, что требует живого контура и учётных данных реестра/прода, вынесено в пошаговый документ: **[`LEAD_FIRST_RUN_OPS.md`](../operations/LEAD_FIRST_RUN_OPS.md)** — prod-smoke с edge, скан **слоёв образа** в реестре (дополнение к Trivy FS в CI), backup/staging по мере появления контуров.

**Бэклог** последующих улучшений NFR (не смешивать с первым прогоном): [`BACKLOG_NFR.md`](../operations/BACKLOG_NFR.md).

---

## 5. Что **явно вне scope** коробки v1 (в Enterprise / позже)

Зафиксировать в релизных нотах, чтобы не путать с NFR:

- LTV, ROI, AI-гиперперсонализация маркетинга, «Smart Retention Engine» как в отдельной странице `/admin/retention`.
- Полный RAG pipeline для аналитики; RAG **только** в контуре бизнес-ассистента чата с клиентом — см. `MASTER_PRODUCT_ROADMAP_2026.md`.
- Распределённая трассировка, error budget burn alerts, полный набор game days — по мере движения к 8.5+.

---

## 6. Связь с полным scorecard

- Живая взвешенная оценка и KPI: `docs/NONFUNCTIONAL_SCORECARD.md`.
- Целевой уровень Enterprise: `docs/artifacts/85 plus/QA_ARCH_85_PLUS_ROADMAP.md` (программа 8.5+; актуальная работа по фазам также в `MASTER_PRODUCT_ROADMAP_2026.md`).

---

## 7. История

| Дата | Изменение |
|------|-----------|
| 2026-03-24 | Ссылка на `BACKLOG_NFR.md`; §4 SME: первый прогон + бэклог разделены |
| 2026-03-24 | §4: `LEAD_FIRST_RUN_OPS.md` — первый прогон prod-smoke и скан образов в реестре |
| 2026-03-24 | Закрытие P0 в репозитории: ссылки на backup, DR drill log, Trivy, PII, deploy smoke, docker tags, tenant audit |
| 2026-03-24 | §1.2: ссылка на `docs/operations/DR_RUNBOOK.md` |
| 2026-03-24 | Первая версия чеклиста для Salon/Dental Box |
