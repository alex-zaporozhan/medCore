# Фаза 1c — entitlements в продукте (Phase_1c_Entitlements)

**Узлы МП mermaid:** `Replace_box_gates`, `Menu_by_entitlement`.  
**Связь МП:** §12–§13, §16.5, §19 п.17, [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md).

## Архитектурный целевой образ

1. **`organization_entitlements`** (или эквивалент) — источник истины для купленных опций; `EDITION` остаётся override для dev/stage (МП §12 фаза B).
2. **Единый механизм гейта** — `require_entitlement` / аналог на всех опциональных маршрутах; выровнять **tasks**, **marketing** с CRM/retention (МП §12.1, §2b слой B).
3. **Меню админки** — строится по entitlements, а не по «всё видно» (МП §15 1c).
4. **Базовый пакет §13.1** — явно отделить «минимальный чат» от `omni.extended` / `omni.embed.bundle` в гейтах и копирайте (МП §13.1).

## Ворота перед merge кода 1c

- Файл [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md) **принят ARCH+LEAD** без незакрытых «уточнить Product» (МП §12.2 усиление).
- Сверка ключей с МП **§4** и **§16.5**.

## Порядок работ @DEV

1. Миграции таблиц каталога опций / связей org↔option (если ещё нет — согласовать с @ARCH).
2. Рефакторинг `is_box_edition()` → проверка entitlement + env override.
3. Пройти инвентарь роутеров сверху вниз; для каждой строки — PR или ссылка на тикет с датой.
4. **CI или скрипт** «маршрут без гейта» для опциональных модулей (DoD §15b 1c).
5. Frontend: скрытие пунктов меню по данным entitlements с сервера (не только клиентский хак).

## DoD

- Матрица маршрут ↔ entitlement + доказательство в CI/скрипте.
- Нет расхождения «в каталоге опция платная, в роутере всегда on».

## Ссылки

- [backend/api_layer.md](../backend/api_layer.md)
- [backend/core_crosscutting.md](../backend/core_crosscutting.md) (edition / config)

## Статус @DEV (2026-04-05)

- **Бэкенд:** `organization_entitlement_access` (один SELECT по ключам org; enforcement при наличии строк; legacy без строк); `entitlement_dependencies.require_entitlement`; гейты на tasks / marketing / crm / retention / recall; **lead-logs без SKU** (QA_ARCH); `GET /admin/auth/session` — `entitlement_enforced`, `entitlement_keys`.
- **Фронт:** `adminEntitlementNav` + сайдбар + редирект сегментов; **ожидание сессии** (Loader) для сегментов с entitlement-ключом до ответа `/admin/auth/session`.
- **Контроль:** `scripts/check_admin_entitlement_routers.py`; тесты `tests/application/test_organization_entitlement_access.py`, `tests/api/test_admin_entitlement_api.py`, `tests/api/test_admin_session.py`; workflow `.github/workflows/build-and-test-entitlements.yml`.

## Бэклог после merge 1c (QA_ARCH — не блокер отдельного PR)

Зафиксировано для @DEV / @ARCH / @SEC / CI; при закрытии — обновить этот раздел, строки в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) §1c и тикет.

### Почему это не обязано попадать в один PR с телом 1c

Это **не технический запрет**: пункты ниже можно закрыть отдельными PR, когда сняты перечисленные ограничения. В одном PR с гейтами 1c их не смешивают, чтобы не раздувать дифф и не смешивать продуктовую политику ошибок с функциональными гейтами.

| # | Почему отдельно от «ядра» 1c | Когда делать |
|---|------------------------------|--------------|
| **B1** | У **FastAPI** (в т.ч. `^0.135`) один и тот же sub-dependency (`Depends(get_current_admin)`) на запрос обычно **резолвится один раз** в общем дереве зависимостей; двойной SELECT в БД — гипотеза до профилирования. `request.state` имеет смысл только после **подтверждения** лишнего hit или если появятся разные фабрики dependency. | Микро-PR после метрик/профайла или при рефакторе auth. |
| **B2** | Регистр кодов — **контракт для клиентов и SEC** (нижний регистр, единый словарь); затрагивает не только entitlement, а **все** публичные `code` → нужны согласование Product/SEC и поэтапная миграция потребителей, иначе риск «тихой» поломки интеграций. | **Сделано в коде:** `normalize_api_error_code` + envelope в `src/main.py`; реестр-описание — [API_PUBLIC_ERROR_CODES.md](../API_PUBLIC_ERROR_CODES.md). OpenAPI/полный словарь — **1c-Q4**. |
| **B3** | Полный `pytest tests/` на GitHub runner — **время**, **флаки**, сервисы (Postgres, Redis, иногда больше) и квоты; узкий workflow 1c осознанно даёт быстрый сигнал по entitlements. | **Закрыто:** job `full-backend-tests` в [build-and-test-entitlements.yml](../../../.github/workflows/build-and-test-entitlements.yml) — см. [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md). |
| **B4** | Документирование/OpenAPI для формы 403 — пересекается с **публичным** API и embed (**1e**); не блокирует корректность гейтов 1c. | Волна «контракт ошибок» с B2 или раньше по согласованию. |
| **B5** | Документация для авторов тестов; **сделано в корпусе** — см. [08_tests_matrix.md](../08_tests_matrix.md) («Изоляция seed…»). | Поддерживать при добавлении SaaS-тестов. |

### Куда отнесено в плане фаз (чтобы не потерять)

| # | Якорь в `arch_plan` / корпусе |
|---|-------------------------------|
| B1 | [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q1**; при отсутствии двойного hit — закрыть как `wontfix` с заметкой про кэш FastAPI. |
| B2 | [10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md](./10_CROSS_CUTTING_SECURITY_ANTISPAM_BRAND_SCALE.md) §28; [03_PHASE_1B_COMMERCE_AND_UX.md](./03_PHASE_1B_COMMERCE_AND_UX.md) (связка каталога/клиентских сообщений); [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q2**. |
| B3 | [07_PHASE_2_RELIABILITY.md](./07_PHASE_2_RELIABILITY.md); [08_tests_matrix.md](../08_tests_matrix.md); [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) **1c-Q3**. |
| B4 | [06_PHASE_1E_LIFECYCLE_EMBED.md](./06_PHASE_1E_LIFECYCLE_EMBED.md) (публичные/embed пути); [backend/api_layer.md](../backend/api_layer.md); **1c-Q4** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md). |
| B5 | [08_tests_matrix.md](../08_tests_matrix.md); **1c-Q5** в [PHASE_FULL_CLOSURE_BACKLOG.md](./PHASE_FULL_CLOSURE_BACKLOG.md) → статус `done` при приёмке текста. |

### Список работ (кратко)

| # | Тема | Суть |
|---|------|------|
| **B1** | `get_current_admin` | При подтверждённом лишнем резолве: один раз на запрос через `request.state` или общий dependency-граф без смены 401/403. |
| **B2** | Стабильные коды ошибок API | Единый регистр машинных `code` (предпочтительно **нижний регистр** в JSON) для `entitlement_required`, `box_forbidden` и остальных публичных ответов; SEC + Product; [PLATFORM_BILLING_ERROR_CATALOG.md](../PLATFORM_BILLING_ERROR_CATALOG.md), МП §29. |
| **B3** | CI: полный pytest | Расширить [`.github/workflows/build-and-test-entitlements.yml`](../../../.github/workflows/build-and-test-entitlements.yml) до **`poetry run pytest tests/`** (или по маркерам). |
| **B4** | Контракт 403 для гейтов | OpenAPI или фрагмент в `docs/architecture`: форма `detail` (dict vs string); выравнивание регистра `code` на сервере. |
| **B5** | Изоляция seed в тестах | Паттерн autouse cleanup при мутации `AdminUser.organization_id` — в [08_tests_matrix.md](../08_tests_matrix.md). |

Продуктовый бэклог 1c (вне таблицы выше): замена оставшихся `is_box_edition`-only гейтов по [ENTITLEMENT_ROUTER_INVENTORY.md](../ENTITLEMENT_ROUTER_INVENTORY.md); omni «base vs extended» — МП §13.1 отдельным эпиком.
