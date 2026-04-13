# PRINCIPLE: глубинный разбор мастер-плана SaaS vs код vs документация

> **Дата:** 2026-04-03  
> **Методология:** [FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md](../architecture/FUNDAMENTAL_CODE_REVIEW_PRINCIPLE.md)  
> **Объект плана:** [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md)  
> **Корпус:** `docs/architecture/**/*.md`, `docs/adr/` (ADR-007…010 и README)  
> **Актуализация 2026-04-05:** слой D (биллинг SaaS / webhook платформы) **документально** дополнен [ADR-011](../adr/ADR-011-platform-subscription-webhook-provisioning.md) и [platform_subscription_billing.md](../architecture/modules/platform_subscription_billing.md); сводный PRINCIPLE-проход корпуса — [PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md](./PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md).

---

## 1. Шаги анализа (выполнено)

1. Извлечь из мастер-плана **обязательные утверждения** (фазы, модули, гейты, ADR).
2. Сопоставить с **фактическим кодом** (`src/`: API, `edition`, сущности, события).
3. Сопоставить с **ADR и TARGET** на предмет пробелов и двусмысленностей.
4. Зафиксировать **логические дыры** (противоречия плана с собой, план ↔ код).
5. Сформировать **рекомендации по усилению** мастер-плана (без расширения scope кода в этом артефакте).

---

## 2. Слой A — Фаза 1 (platform, self-service, entitlements)

| Утверждение плана / ADR-007 | Документ | Факт в коде | Зазор | Критичность |
|----------------------------|----------|-------------|-------|-------------|
| Отдельный контур platform-operator, `/platform/*` | ADR-007, §6.1 | Нет совпадений по `platform` в `src/api` (маршрутов нет) | Platform MVP **не начат** в API | **P0** для честного SaaS |
| Self-service регистрация организации | §1 таблица, ADR-007 §3 | `admin_auth`: только логин существующего админа; нет публичного создания `Organization` | Нет онбординга SaaS-клиента | **P0** |
| JWT platform vs tenant | §9 п.3, ADR-007 §2 | Один контур JWT для клиники (`admin_auth`); `AdminSessionResponse` уже несёт `organization_id`, `accessible_clinic_ids` — задел под сеть, **не** под platform issuer | Нужна явная спека двух realm до миграций | **P0** дизайн |
| Entitlements в БД | §2, §5 Фаза 1 | Только `EDITION` env и `is_box_edition()` | Нет таблиц планов/entitlements | **P0** |

**Якоря кода:** `src/api/v1/routers/admin_auth.py`, `src/core/edition.py`, `src/domain/entities/organization.py` (минимальная сущность: `id`, `name`, `created_at`).

**Дыра док ↔ код:** ADR-007 перечисляет platform powers (suspend, export, audit). В репозитории нет ни таблиц audit platform, ни роутеров — это ожидаемо для Proposed ADR, но в плане стоит **явно пометить**: «§6.1 шаги 3–4 = нулевая реализация в коде».

---

## 3. Слой B — «Коробка» vs конструктор модулей (§2, §6.5)

| Механизм | Где в коде | Соответствие плану |
|----------|------------|-------------------|
| `is_box_edition()` | `src/core/edition.py` | Совпадает с §1 таблицей («глобальный EDITION»). |
| `require_crm_enterprise_edition` | `src/api/v1/dependencies.py` | CRM закрыт в box — согласуется с идеей «Enterprise-only фича». |
| Прямые проверки `is_box_edition()` | `src/api/v1/routers/admin_retention.py` | Retention только Enterprise — согласуется. |
| Задачи (Kanban) | `src/api/v1/routers/admin_tasks.py` | **Нет** вызова `is_box_edition` / entitlement. |
| Маркетинг / атрибуция | `admin_marketing.py`, `admin_marketing_attribution.py` | **Нет** edition-gate в этих файлах (по grep). |

**Критическая логическая дыра:** мастер-план в §3.1 называет **Kanban** и **маркетинг** *опциональными* entitlements после базы, но в коде они **не привязаны** к `EDITION` так же, как CRM и retention. Итог для проектирования:

- либо план должен говорить: «сегодня модульность **частично** выражена только через env (CRM/retention)»;
- либо эпик entitlements должен включать **полный инвентарь** роутеров и унифицированный helper `require_entitlement("tasks.kanban")` и т.д.

**Риск:** после ввода `organization_entitlements` команда может забыть задачи/маркетинг и оставить их «всегда on» — это расходится с §3.1/§6.5.

---

## 4. Слой C — Базовый пакет §3.1 vs факт модулей

План декларирует базовый пакет (орг, RBAC, услуги, календарь, пациент, оплата, кассы, чат, лента, уведомления). В коде эти области **есть** в виде доменов и роутеров, но:

| Тема плана | Зазор |
|------------|--------|
| «Чат клиента / omni» | Объём omnichannel в коде большой; план смешивает «минимальный канал» и полноценный omni. **Уточнить в плане:** базовый entitlement = *канал записи минимум*, не весь модуль ADR omni. |
| Кассы / ERP | Зависимость от RBAC и клиники; нет связи с **платформенной** подпиской — план это признаёт в §3.2, но не разделяет **платёж пациента** (YooKassa) и **подписку организации**. |

---

## 5. Слой D — Биллинг SaaS (§3.2)

| Утверждение | Код |
|-------------|-----|
| Webhook подписки → `organization_entitlements` | Нет Stripe/YooKassa-контура **подписки платформы** (есть платежи **пациента** в `payment_service` и т.д.). |
| P0 эпик «параллельно ADR-007» | §5a перечисляет U-001, U-006, B-4, U-008 — **не** содержит явного пункта «контур подписки SaaS». |

**Логическое противоречие внутри плана:** §3.2 называет биллинг SaaS **P0 параллельно ADR-007**, а §5a фиксирует P0 только как «безопасность и доверие». Нужна **явная классификация:** либо вынести биллинг в отдельный «P0 коммерция» с воротами, либо понизить формулировку §3.2 до «проектирование параллельно, релиз с Фазой 3».

---

## 6. Слой E — Фаза 2 (outbox, CI, BCP)

| Тема | Документ | Код / репо |
|------|----------|------------|
| Outbox | ADR-009, PRINCIPLE §2.1 | In-process `EventBus`, хендлеры с отдельными сессиями — как в FUNDAMENTAL | Согласовано с планом; приоритет outbox обоснован. |
| U-008 CI | §5a | Проверять актуальное состояние `.github/workflows` отдельным тикетом | План корректен как политика. |
| BCP | ADR-008 | Исполнение OPS | План не дырявый; риск только «документ без drill». |

---

## 7. Слой F — Вертикаль (§4)

План предлагает `industry_profile` на `Organization`. Сейчас у `Organization` **нет** такого поля — ожидаемо до Фазы 4. **Дыра проектирования:** связь vertical с **копирайтом/i18n** и с **скрытием полей** должна попасть в чеклист Фазы 1/4 в мастер-плане (одна строка: «не ломать API для dental при добавлении generic»), иначе vertical останется только в БД без UX-контракта.

---

## 8. Прочие логические дыры

1. **Порядок работ:** при мультиреплике API outbox критичен для целостности **раньше**, чем «красивый» SaaS onboarding; мастер-план допускает параллель Фазы 1 и P0 — стоит в §8/§9 добавить рекомендацию: «оценить hot-path цепочки (платёж → бронь → ERP) для решения, не переносить ли минимальный outbox **до** публичного self-service».
2. **U-005 `/owner/*`:** план в §7 предупреждает; в коде owner-роль уже фигурирует в `admin_auth` — хорошо трассировать в спеке API первый шаг Фазы 1.
3. **ADR-010 импорт:** без кода — план честен; усиление: «v1 коннектор не заменяет entitlement на импорт» (отдельный ключ модуля).

---

## 9. Рекомендуемые усиления `SAAS_STRENGTHENING_MASTER_PLAN.md` (кратко)

**Статус 2026-04-05 (LEAD):** перечень ниже **встроен** в мастер-план: **§2b**, **§12.1–12.2** (`ENTITLEMENT_ROUTER_INVENTORY.md`), **§13.1–13.2**, **§14** чеклист, **§15c** (P0 коммерция vs §15a), **§16.1** факт кода, **§16.4**, **§17.1**, **§19** п.17, **§23** п.22.

Исходный перечень (история трассировки):

1. Таблица **«план vs код: стартовая точка»** (platform, entitlements, signup).
2. Подпункт **«частичная модульность сегодня»**: CRM/retention vs tasks/marketing.
3. Синхронизация **§13.2 P0 коммерции** с **§15a** — через отдельный поток **§15c**.
4. Чеклист **entitlement inventory**: grep по роутерам перед миграцией → §12.2.
5. **Outbox vs onboarding** / multi-replica → **§17.1**.

---

## 10. Ссылки

- [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md)  
- [TARGET_PLATFORM_MULTITENANCY_REFERENCE.md](../architecture/TARGET_PLATFORM_MULTITENANCY_REFERENCE.md)  
- [ADR-007](../adr/ADR-007-platform-multitenancy-super-admin.md) … [ADR-010](../adr/ADR-010-external-crm-import-scope.md)  
- GAP-scan 2026-04-03 не хранится отдельным файлом в git; см. [QA_ARCH_PHASE0_GOVERNANCE_DEV_REVIEW_2026-04-06.md](./QA_ARCH_PHASE0_GOVERNANCE_DEV_REVIEW_2026-04-06.md) и последующие `QA_ARCH_*.md` в этом каталоге.  
- [PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md](./PRINCIPLE_SAAS_MASTER_PLAN_AND_LINKED_CORPUS_REVIEW_2026-04-05.md)
