# ARCH_PHASE_00_FOUNDATION_2026 — фаза 0 (роль @ARCH)

> **Ссылка:** `MASTER_PRODUCT_ROADMAP_2026.md` § фаза 0.  
> **Сквозное:** `ARCH_CROSS_CUTTING_UI_I18N_2026.md`, `ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md`.

## 1. Цель фазы

Закрепить NFR-базу: CI, секреты, backup/restore runbook, RBAC-аудит критичных путей, минимальный SCA — без этого последующие фазы нестабильны.

## 2. Границы

**В scope:** пайплайны, документация операций, негативные тесты на tenant, исправление «дыр» в правах на существующих роутов.  
**Вне scope:** новый пользовательский функционал (кроме обязательных правок для прохождения гейтов).

## 3. Данные и мультитенантность

Инвентаризация таблиц без `clinic_id` где он обязателен; план миграций без downtime по возможности. См. `ARCH_DATA_MULTITENANT_AND_OPERATIONS_2026.md`.

## 4. Безопасность

Secret scanning; запрет секретов в git; политика образов; проверка JWT и scope для admin API.

## 5. UI / i18n

Подготовка: единый чеклист RU-строк для новых PR; не блокирует фазу 0 полностью, но стартует параллельно.

## 6. Переменные / конфиг

Документировать env для Box vs Enterprise (флаги позже в фазе 6); минимум — разделение dev/staging/prod.

## 7. Риски

«Тихие» 403/200 с чужим tenant — приоритет негативных тестов.

## 8. Критерий готовности

`SME_BOX_NFR_CHECKLIST.md` закрыт по части **репозитория и CI**: backend CI (`backend-ci.yml`) — ruff, mypy (`security.py`), pytest, gitleaks, pip-audit, **tenant ORM audit** (`scripts/audit_tenant_columns.py`); **Trivy FS** (`security-trivy.yml`); **restore drill** (`restore-drill.yml`); runbook и журнал — [`DR_RUNBOOK.md`](../operations/DR_RUNBOOK.md), [`DR_DRILL_LOG.md`](../operations/DR_DRILL_LOG.md); PII — [`PII_LOGGING.md`](../operations/PII_LOGGING.md); образы — теги по SHA в `docker-images.yml`. Scorecard — `docs/NONFUNCTIONAL_SCORECARD.md`.

**Вне репозитория (@LEAD):** cron backup в проде, при необходимости staging drill в журнале, prod-smoke, скан образов в реестре.

---

## 9. История

| Дата | Изменение |
|------|-----------|
| 2026-03-24 | §8: Trivy FS, restore-drill workflow, tenant audit, PII, закрытие SME в репозитории |
| 2026-03-24 | §8: PyJWT вместо python-jose; mypy на security; pip-audit без игнора |
| 2026-03-24 | Критерий §8: ссылки на CI, DR_RUNBOOK, pip-audit |
| 2026-03-24 | Первая версия |
