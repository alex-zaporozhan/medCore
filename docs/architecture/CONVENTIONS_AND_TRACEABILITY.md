# Соглашения и трассируемость

## Как это работает в контексте репозитория

Документы в `docs/architecture/` описывают **фактическую** цепочку: файлы Python/TypeScript перечислены как якоря, а не как желаемая «чистая» архитектура. На практике граница API — это **FastAPI-функции** с `Depends`: сессия БД, текущий пользователь, `require_permissions`, иногда `get_reporting_session` для чтения с реплики. Граница application — **классы и функции в `application/services`**, которые вызывают `get_event_bus().publish(...)` (пример: `src/application/services/booking_service.py`). Domain — **SQLAlchemy-модели** в `domain/entities` и **Protocol/ABC** репозиториев; перенос данных наружу — **Pydantic DTO** в `application/dto`. Любое расхождение (например запросы в роутере без сервиса) отмечается как **частичное** соответствие слою, а не скрывается.

## Цель

Каждый абзац в `docs/architecture/` должен быть **проверяемым**: либо ссылка на путь в репозитории, либо явная пометка, что утверждение не проверялось в рантайме / остаётся гипотезой.

## Обязательные элементы описания подсистемы

Для каждой крупной подсистемы (или группы файлов) по возможности указывай:

| Поле | Смысл |
|------|--------|
| **Назначение** | зачем существует модуль в продукте. |
| **Точки входа** | файлы с `router`, `main`, `App`, фасады. |
| **Поток** | 1–2 предложения или mermaid: кто кого вызывает. |
| **Зависимости** | БД, Redis, S3, внешние HTTP, другие пакеты `src/`. |
| **Статус** | Реализовано / Частично / Формально (UI или API есть, сценарий сырой) / Неясно без доп. чтения. |
| **Непонятное** | вынести дублирующую формулировку в [UNRESOLVED_AND_CONFUSION_LOG.md](./UNRESOLVED_AND_CONFUSION_LOG.md) с якорями «что уже прочитали». |

## Формат ссылок на код

- Путь от корня репозитория: `` `src/api/v1/router.py` ``, `` `frontend/src/api/client.ts` ``.
- Для перечисления больших каталогов допустима фраза «N файлов в `…`» с указанием glob или одного типичного файла-примера.

## Запрещено без пометки

- Утверждения о production-SLA, нагрузке, сертификации — только если есть отдельный документ или конфиг в репо.
- Догадки о намерениях автора без цитаты комментария или теста — перенос в UNRESOLVED или формулировка «не подтверждено».

## Новые префиксы API (`/platform/*`, публичный лендинг)

- Любой новый префикс **platform** или публичный маркетинговый маршрут — в том же изменении обновлять [backend/api_layer.md](./backend/api_layer.md), при необходимости [CONVENTIONS_AND_TRACEABILITY.md](./CONVENTIONS_AND_TRACEABILITY.md) (этот файл) и шапку [INDEX.md](./INDEX.md); критичные денежные пути — ворота МП **§18–§19** и [DEV_EXECUTION_SEQUENCE.md](./arch_plan/DEV_EXECUTION_SEQUENCE.md).
- Уже существующий контур **B:** `/api/v1/platform/billing/...` — см. [modules/platform_subscription_billing.md](./modules/platform_subscription_billing.md), ADR-011.

## Фронтенд: паспорта экранов и манифест API

- Изменения в `frontend/src/App.tsx` или `frontend/src/routePaths.ts`: обновлять [FRONTEND_PASSPORT.md](../product_state/FRONTEND_PASSPORT.md); пер-страничные описания — каталог [frontend/pages/README.md](../frontend/pages/README.md) и критерии [PAGE_PASSPORT_CRITERIA.md](../frontend/PAGE_PASSPORT_CRITERIA.md); слои и чеклист фронта — [FRONTEND_ENGINEERING_CONVENTIONS.md](../frontend/FRONTEND_ENGINEERING_CONVENTIONS.md).
- Сверка поверхности HTTP с прозой: [documentation/API_V1_ROUTER_MANIFEST.md](../../documentation/API_V1_ROUTER_MANIFEST.md) и `src/api/v1/router.py` (процесс команды).

## Обновление

При крупном рефакторинге слоя — обновить соответствующий файл в `docs/architecture/` в том же PR или следующим шагом; иначе документ становится историческим артефактом (это нормально, если статус помечен).

**Приёмка LEAD:** если формулировка в модульном файле противоречит актуальной версии [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md) (дата в шапке LEAD-документа), до явной синхронизации **приоритет у LEAD-документа** как у операционного списка пробелов приёмки; затем исправить модульный текст или закрыть пункт бэклога в коде.

Связь с Enterprise-оценкой: [ENTERPRISE_SAAS_RUBRIC.md](./ENTERPRISE_SAAS_RUBRIC.md). В новых и существующих файлах каталога — секции **Enterprise-аудит** и **Соответствие фактам** (см. [INDEX.md](./INDEX.md)).

### Enterprise-аудит (честная оценка)

- **Критические риски:** сами соглашения не устраняют отсутствие platform-tenant; см. [INDEX.md](./INDEX.md) и рубрику.
- **Средние риски:** при несоблюдении шаблона документы снова станут «маркетингом без якорей».
- **Формально / недоделано:** нет автоматического линтера на наличие якорей в markdown.
- **Рекомендуемые доработки:** PR-чеклист с пунктом «якорь или UNRESOLVED»; при major-приёмке сверять с [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).

### Соответствие фактам (проверка)

- Текст согласован с практикой репозитория; машинная проверка не выполнялась.

### Углубление (PRINCIPLE — фундаментальный обзор)

- **Сильные логические риски:** без якоря документы скрывают расхождение транзакций и событий (см. §2.1 фундаментального обзора).
- **Что усилить:** шаблон PR: «изменение логики → обновлён путь в docs/architecture или UNRESOLVED».
- **С нуля:** опционально pre-commit напоминание (не реализовано в этом PR).
- **БД:** любая рекомендация по схеме — только с миграцией и ссылкой на ADR.
- **Полный разбор:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](./FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md); приёмка: [LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md](./LEAD_ACCEPTANCE_CRITIQUE_AND_GAPS.md).
