# LEAD — U-008: политика CI релиза и e2e/security (`workflows_disabled`)

**Дата:** 2026-04-06. **Назначение:** закрытие **2-F8** и **PRC-E4** в смысле «известная и задокументированная политика поставки», без обязательного включения всех отключённых workflow в каждый push в `main`. **Связь:** [UNRESOLVED_AND_CONFUSION_LOG.md](../architecture/UNRESOLVED_AND_CONFUSION_LOG.md) **U-008**, [STREAM_PHASE2_RELIABILITY_EPICS.md](../architecture/arch_plan/STREAM_PHASE2_RELIABILITY_EPICS.md) **2-E3**.

---

## Обязательный baseline релиза (satisfied)

1. На **теги `v*`** (и при необходимости `workflow_dispatch`) выполняется [`.github/workflows/release-gate.yml`](../../.github/workflows/release-gate.yml): проверки entitlements, сборка фронта, `scripts/phase0_governance_preflight.py all`, полный `pytest tests/`.
2. Повседневный PR-поток остаётся на [`.github/workflows/build-and-test-entitlements.yml`](../../.github/workflows/build-and-test-entitlements.yml) (как минимум зелёный backend по политике репозитория).

Пока release-gate зелёный на теге релиза и эта политика не отменена другим решением LEAD — критерий **PRC-E4** считается **выполненным (satisfied)** с точки зрения L3-чеклиста.

---

## E2E, security и прочие workflow в `.github/workflows_disabled/`

**Решение:** Перенос этих job в обязательный путь **каждого** merge в `main` — отложен: отдельная оценка длительности CI, секретов стенда и владельца (QA_ARCH + OPS). До включения:

- статус **2-F8** в [PHASE_FULL_CLOSURE_BACKLOG.md](../architecture/arch_plan/PHASE_FULL_CLOSURE_BACKLOG.md) закрывается **данным документом** (явный waiver с обязательным release-gate на тегах);
- при смене уровня готовности к продакшену (например, публичный L3 без исключений) LEAD пересматривает политику и заводит тикет на перенос конкретных workflow из `workflows_disabled/` в активные.

Инвентарь отключённых пайплайнов — в репозитории; конкретные имена файлов не дублируем здесь, чтобы не рассинхронизироваться с git.

---

## Связка с безопасностью

Security-сканы и браузерные e2e **не** заменяют ручной SEC-чеклист релиза; они дополняют его после включения в CI. До включения — ответственность за ручной/внешний прогон остаётся на процессе релиза ([RELEASE_CHECKLIST.md](../operations/RELEASE_CHECKLIST.md)).
