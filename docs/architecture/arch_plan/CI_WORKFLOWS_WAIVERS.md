# CI: активные workflow и долг по `workflows_disabled` (WP5.2)

Цель: не оставлять критичные проверки «молча выключенными» без записи владельца, срока пересмотра и замещающего гейта.

## Активные workflow (`.github/workflows/`)

| Workflow | Назначение | Заметка |
|----------|------------|---------|
| `build-and-test-entitlements.yml` | PR/push: Poetry, `check_admin_entitlement_routers.py`, **frontend `npm run build`**, узкий pytest + full-backend-tests на main | Основной PR-гейт backend+entitlements; включает `test_payment_webhook_governance`, `test_platform_billing`. |
| `release-gate.yml` | Тег `v*`, ручной dispatch: governance preflight + полный `pytest tests/` | U-008 / PRC-E4. |
| `security-trivy.yml` | Trivy FS по lock/Dockerfile | PR: не блокирует merge при CRITICAL; push main — строже. |
| `documentation-markdown-links.yml` | Проверка относительных ссылок в `docs/` | |
| `dr-restore-drill.yml` | Только `workflow_dispatch`: pg_dump/restore + сверка `alembic_version` | PRC-E2 / U-009; OPS запускает вручную или по расписанию в форке политики. |

## Отключённые копии / заготовки (`.github/workflows_disabled/`)

Все ниже **не исполняются** в GitHub Actions, пока файл лежит вне `workflows/` или пока на job стоит `if: false`.

| Файл | Состояние | Политика (waiver) | Пересмотр |
|------|-----------|-------------------|-----------|
| `backend-ci.yml` | `if: false` | Полный backend-only гейт **частично замещён** job `full-backend-tests` в `build-and-test-entitlements.yml` и `release-gate.yml`. Отдельный ruff/pip-audit/gitleaks — через локальный pre-push / Jenkins по политике команды. | Квартально или при смене CI |
| `frontend-ci.yml` | `if: false` | **Замещено:** `npm ci` + `npm run build` в `build-and-test-entitlements.yml` (verify). | При выделении отдельного FE-only pipeline |
| `e2e.yml` | `if: false` | E2E Playwright — см. [LEAD_CI_U008_E2E_SECURITY_POLICY](../../artifacts/LEAD_CI_U008_E2E_SECURITY_POLICY_2026-04-06.md); включение после стабилизации staging. | По тикету QA_ARCH |
| `docker-images.yml` | отключён | Публикация образов — **Jenkins** (`Jenkinsfile`) по политике репозитория. | — |
| `load-tests-k6-optional.yml` | отключён | Нагрузочные сценарии вне обязательного PR; запуск вручную/в отдельной ветке. | По необходимости |
| `nightly-regression-disabled.yml` | отключён | Ночной регресс — опционально; не блокирует merge. | — |
| `security-trivy.yml` (копия) | дубликат | **Суперсед:** активный `.github/workflows/security-trivy.yml`. Копию в `workflows_disabled` не синхронизировать с прод-гейтом — удалить при уборке или оставить как архив с пометкой «не использовать». | При уборке репозитория |

**Владелец записи:** LEAD + DevEx; дата шаблона: 2026-04-08.

## Критерий снижения долга (WP5.2 satisfied для команды)

- Либо workflow перенесён в `workflows/` и включён,
- Либо строка в этой таблице + замещающий гейт задокументирован,
- Либо явный **waived** в `STREAM_PRODUCTION_READINESS.md` (блок I / внутренний шаблон) с датой пересмотра.
