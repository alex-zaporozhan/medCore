# OSS Public Readiness — план публикации на GitHub

> **Дата:** 2026-08-17  
> **Роли:** @LEAD (маршрут) · @ARCH (канон и тенантность) · @QA_ARCH (красные тряпки) · дальше: @SCRIBE · @DEV · @FRONTEND · @SEC · @LAWYER  
> **Цель волны:** открытый репозиторий международного уровня как **доказательство**, что ИИ собирает сложный **модульный монолит** без фантазий. Не «переписать продукт», не «закрыть все волны 2026».  
> **Критерий стыда:** человек с GitHub, CTO или инженер, за 3 минуты понимает *что это*, *какой стек*, *что мульти-тенант*, и не видит MVP-коробку / хаос документации на первом экране.

**Приоритет истины:** код и тесты → этот файл → остальной `docs/`. Расхождение с кодом = баг документа.

---

## 0. Вердикт (не слайд)

| Утверждение | Статус | Доказательство |
|-------------|--------|----------------|
| Это **не** коробка «одна клиника» | **Верно в коде** | `Organization` / `Clinic` / `clinic_id` / `organization_id`, `src/application/multitenancy.py`, ADR-007, сид `seed_multi_tenant_showcase` (5 клиник), контур основателя `/platform/*` |
| Это **модульный монолит** (не микросервисы) | **Верно** | `src/api` → `application` → `domain` → `infrastructure`; Celery как воркеры того же продукта |
| Это **уже** ближе к Enterprise SaaS, чем к MVP записи | **Частично** | Код: RBAC, entitlements, outbox, replica, Prometheus. Фасад README/LICENSE выровнен. Admin chrome EN default (A0–A12); patient/маркетинг ещё RU literals |
| Английский уже «в тени флагом» | **Админ chrome: да (A0–A12)** | Login/шелл/nav + все экраны админки + shared chrome на ключах, default `en`. Patient PWA / маркетинг body / `index.html` ещё RU. Контракт: [`ADMIN_I18N_EN_ROADMAP.md`](./ADMIN_I18N_EN_ROADMAP.md) |
| Документация готова к GitHub | **Частично** | English README + overview + LICENSE. `documentation/` больше не игнорируется целиком. Остальной `docs/` и user docs ещё на русском |
| LICENSE | **PolyForm Shield** | MIT отвергнут: разрешал бы конкурентный SaaS. ADR-017 |

**Честная формулировка для GitHub (победитель @ARCH):**  
*Multi-tenant clinic operating system (dental vertical), shipped as a modular monolith.*  
Не писать «Enterprise-grade» в бейджах. Писать фактами: слои, тенантность, RBAC, очереди, тесты. Лицензия — source-available, не OSI.

---

## 1. LPA (Law 24)

⊕ **L3 Elimination:** не переводить 500+ внутренних `.md` и не делать из архива волн витрину. Публичный контур = тонкий английский слой (`README` + `documentation/` уровень 1–2). Архив `docs/archive/erp-vnext-2026-wave-planning/` остаётся **историческим доказательством процесса**, не входом.

⊕ **L1 Technology:** i18next + react-i18next (MIT) — это смена класса задачи (словари + default `en`), не search-replace литералов. Детектор языка браузера **не** берём: он подерётся с продуктовым default `en`.

⊕ **L5 Automation:** английский UI — ключи i18n с **EN default**. Иначе следующая волна снова разъедется.

Линзы L2/L4/L6 на публикацию GitHub не стреляют (не новый bounded context, не outbox, не метрика волны). Контракт исполнения: [`ADMIN_I18N_EN_ROADMAP.md`](./ADMIN_I18N_EN_ROADMAP.md).

---

## 2. Роли и ответственность

| Роль | Что делает в этой волне | Что не делает |
|------|-------------------------|---------------|
| **@LEAD** | Этот план, гейты, порядок волн, отказ от «назовём Enterprise и запушим» | Не публикует git (Law 40) |
| **@ARCH** | Канон: мульти-тенант ≠ коробка; SPDX лицензии; что считать публичным контрактом | Не переписывает схему БД |
| **@QA_ARCH** | Инвентарь красных тряпок с файлами; календарь как P0; честный gap-list в README | Не выдаёт 🟢 на «красивый README при мёртвом слоте» |
| **@SCRIBE** | Английский публичный слой: overview, contributing, user-facing указатели | Не трогает `roles/` |
| **@FRONTEND** | Контракт i18n в `ADMIN_I18N_EN_ROADMAP.md` (провайдер в `main.tsx`, ns, harness тестов) | Не изобретает второй дизайн-систему |
| **@DESIGN** | Переключатель locale: существующий `SegmentedControl` EN/RU в login+header (instrument) | Не глобус, не отдельный экран, не второй остров на RBAC |
| **@DEV** | P0 календарь; default edition = platform; вычистить «MVP/box» из манифестов; i18n **только** батчами A0–A12 | Не переводит 300 экранов в одном PR |
| **@SEC** | Скан секретов, демо-пароли явно DEMO, `.env.example` без боевых ключей | Не «прячет» демо-логины — помечает |
| **@LAWYER** | SPDX: PolyForm Shield (не MIT). Текст в `LICENSE` + ADR-017 | Не ставит MIT «потому что GitHub» |
| **@OPS** | Один путь «clone → compose up → demo login» в README | Не меняет Jenkins канон |

**@MOTION / @SEO / @PENTEST S-Global:** вне волны публикации. Переключатель языка — не новый экран: SPEC закрыт в roadmap §2, отдельный `DESIGN_SPEC_*.md` не требуется. Календарный баг — @DEV + точечный @QA_ARCH, не рескин.

---

## 3. Что уже сделано в этом проходе (2026-08-17)

Зафиксировано в git working tree (коммит — человек, Law 40):

- Корневой **`README.md`** — английский вход: продукт как multi-tenant OS, стек, дерево, requirements, честный Known limitations.
- **`documentation/PRODUCT_OVERVIEW.md`** — английский обзор, не «одна клиника».
- **`pyproject.toml`** — убрано «MVP системы записи».
- Default `VITE_EDITION` в `resolveProductFeatures` выровнен с полным продуктом (`premium`), а не `basic`.
- Комментарии edition: legacy SKU gate, не позиционирование продукта.
- **Проход 2 (2026-08-17):** LICENSE PolyForm Shield + ADR-017; `.gitignore` больше не глотает новые файлы `documentation/`; курсы → `local/intern-courses/` (gitignore); календарь: клик по пустой ячейке, ошибки формы, double-submit guard; SECURITY.md.  
- **Проход 3:** Required Notice / автор **Alexandr Zaporozhan** (email `zaporojan` не трогать).  
- **Проход 4 (ревью решений):** контракт i18n закрыт в [`ADMIN_I18N_EN_ROADMAP.md`](./ADMIN_I18N_EN_ROADMAP.md) — провайдер в `main.tsx`, login-switcher, dayjs clock, владельцы e2e, гейт chrome≠комментарии. **В коде A0–A12** (гейт 2026-08-18): admin chrome на ключах; маркетинг/patient/`index.html` — вне волны.

---

## 4. Красные тряпки (только то, что стыдно на GitHub)

Класс **P0** — блокеры публикации как «серьёзный репозиторий».  
Класс **P1** — закрыть в первой публичной волне.  
Класс **P2** — после публикации, не держать релиз.

### 4.1. Документация и позиционирование

| ID | Класс | Факт | Что сделать | Роль |
|----|-------|------|-------------|------|
| D1 | P0 | Корневой README был по-русски и про «запись в стоматологию» | Английский README (этот проход) | @LEAD / @SCRIBE |
| D2 | P0 | Автор в манифестах | `pyproject.toml` / `frontend/package.json` authors = Alexandr Zaporozhan; `LICENSE` Required Notice — тот же правообладатель. Email `alexandr.zaporojan@gmail.com` не менять (адрес ≠ транскрипция паспорта). | сделано |
| D3 | P0 | **LICENSE** | PolyForm Shield (не MIT) — сделано, ADR-017 | @LAWYER |
| D4 | P1 | Стажёрские курсы в публичном дереве | Перенесены в `local/intern-courses/` + gitignore | @LEAD |
| D8 | P0 | `.gitignore` содержал `/documentation/` — **новые** публичные docs не попадали в git (tracked файлы жили, untracked — нет). Проверено: `git check-ignore --no-index documentation/brand-new-file.md` | Строка `/documentation/` снята; политика = documentation в git | @ARCH |
| D5 | P1 | Публичный `documentation/` почти весь на русском | Волна @SCRIBE: уровень 1 (overview, pitch, KB intro) на EN; RU как `*.ru.md` или позже | @SCRIBE |
| D6 | P1 | `docs/RUN_SERVICES.md` пишет «тарифы отключены, EDITION не нужны», код edition-гейтов живой | Одна фраза: default = full platform; `EDITION=box\|basic` — legacy SKU | @ARCH |
| D7 | P2 | `docs/handover/public/` дублирует стек по-русски | Ссылка из English README на один канон, handover не рекламировать | @SCRIBE |

### 4.2. Коробка vs multi-tenant

| ID | Класс | Факт | Что сделать | Роль |
|----|-------|------|-------------|------|
| T1 | P0 | Код — Organization → Clinic → staff/patient + platform founder | Публичные тексты говорят **SaaS / multi-tenant**, не «box install» | @ARCH / @SCRIBE |
| T2 | P1 | `is_box_edition()` / `VITE_EDITION=basic\|box` скрывают sales/retention/embed/rag-kb/commerce | Оставить как **SKU switch**, в README: default is full platform; box is a compatibility cut | @ARCH |
| T3 | P1 | `resolveProductFeatures`: unset edition раньше → `"basic"` | Выровнено на полный продукт (`premium`); backend unset → enterprise | сделано |
| T4 | P2 | Комментарии «коробка» в `src/api/v1/routers/admin_admins.py` и entity docstrings | Точечно: «clinic staff» / «platform SKU», не «box product» | @DEV |
| T5 | P2 | `get_default_clinic` в dependencies — legacy single-row helper | Не удалять в этой волне; в каноне: helper для пустых/legacy DB, не модель продукта | @ARCH |

**Не делать:** миграцию на database-per-tenant, полный RLS на все таблицы, ребренд MyClient. Это другие эпики (ADR-007 fork уже зафиксирован: application-layer isolation + негативные тесты).

### 4.3. Язык UI (международный GitHub)

| ID | Класс | Факт | Что сделать | Роль |
|----|-------|------|-------------|------|
| L1 | P0 | ~~Экраны A9–A12 ещё RU~~ | **Закрыто A12** (гейт grep: живой chrome без кириллицы; comment/data/R10 в отчёте). Default `en`, RU полный второй. Маркетинг/patient — не этот ряд. | @FRONTEND → @DEV |
| L2 | P1 | ~~`dayjs.locale("ru")` на импорте~~ | **Закрыто A0-audit.** A2 не возвращать module-scope locale на staff calendar | @DEV |
| L3 | P1 | Формы: «+7», «₽», YooKassa — региональный контур РФ | В README честно: payments/SMS/OAuth — pluggable; demo may use RU providers | @ARCH |
| L4 | P2 | Полный перевод user docs | После словарей UI | @SCRIBE |

**Решение @LEAD (зафиксировано):** публичный GitHub и ценные документы — **English**. Продуктовый UI для OSS-демо — **English default**. Русский — второй locale, не удалять (РФ-клиенты). Это продуктовое решение, не «тень флага».

### 4.4. Календарь: нельзя добавить запись (P0 продукта)

Два разных экрана. Пользователь мог попасть в любой.

**A. Расписание клиники** `/admin/schedule` — **исправлено в проходе 2**

Было:

- Клик только при `slot.is_available`; dummy-слот с `is_available: false` → мёртвый клик.
- `findBooking` требовал `slot.booking_id` — запись в сетке могла не найтись.
- Сабмит без `clinicId` — тишина.
- EmptyState на всю ширину **над** сеткой (ложный empty, кнопка «ниже» при CTA на себе).

Стало:

- Пустая ячейка открывает create (занятость решает бэкенд: advisory lock + `_ensure_slot_available`).
- Форма: явные ошибки, `loading` на кнопке (гонка double-click).
- CTA «Новая запись» в панели даты; сетка не прячется за EmptyState.
- Регрессия: `frontend/src/admin/components/__tests__/ScheduleCalendarGrid.test.tsx`.

**B. Календарь персонала** `/admin/calendar` (`AdminStaffCalendarPage.tsx`)

- Это **staff events**, не визиты пациентов. Кнопка «+ Добавить событие» есть. Баг «не создаётся запись» здесь — другой контракт (событие vs booking).

Пункты 1–3 и 5 по расписанию клиники — **сделаны** (vitest сетки). Пункт 4: тост/`QueryErrorAlert` ещё на русских литералах и `getBookingErrorMessage`; маппинг `code` → ключ — батч **A2** i18n-roadmap, не отдельный ERP-эпик. Staff calendar (B) — не booking, в i18n едет тем же A2.

Отдельный `DEV_PROMPTS` на весь ERP не нужен. Владелец календаря P0: **@DEV**, приёмка **@QA_ARCH**.

### 4.5. Прочие фронт-дыры «на первый клик» (P1, не океан)

Не расследовать все экраны в этой волне. Минимум для демо GitHub:

- Happy path: signup/login demo → `/admin/schedule` создать запись → увидеть в сетке.  
- Не показывать UUID вместо ФИО (Law 8) на демо-сиде.  
- Кнопки мутаций disabled + invalidateQueries (уже частично есть у create booking).

Остальные баги — issue tracker после публикации, не блокер README.

### 4.6. Безопасность OSS

| ID | Класс | Что |
|----|-------|-----|
| S1 | P0 | `LICENSE` PolyForm Shield + README: demo credentials are **not** production — сделано |
| S2 | P0 | Прогнать secret scan (gitleaks/trufflehog или workflow); боевые ключи не в git |
| S3 | P1 | `CREDENTIALS_REFERENCE.md` — оставить, явно DEMO; не удалять (без них клон бесполезен) |
| S4 | P1 | `.env.example` placeholders only (сейчас так) |
| S5 | P2 | SECURITY.md — сделано |

---

## 5. Дорога (короткая, три волны)

### Wave 0 — Public face (идёт сейчас / сразу)

Стыдно без этого открывать репо.

1. English README (стек, дерево, tenancy, limitations).  
2. English PRODUCT_OVERVIEW.  
3. Убрать MVP из `pyproject.toml`.  
4. Default edition = full platform.  
5. SPDX `LICENSE` (PolyForm Shield) + ADR-017.  
6. Secret scan.  
7. Календарь P0 — клик + ошибка не silent (проход 2).

**Гейт @LEAD:** README на EN + LICENSE + календарь создаёт запись на демо-сиде.

### Wave 1 — English product surface

Исполнение админки — **только** по [`ADMIN_I18N_EN_ROADMAP.md`](./ADMIN_I18N_EN_ROADMAP.md) (Cursor Queue, батчи A0→A12).

1. A0: провайдер в `main.tsx` + dayjs clock + test harness — **сделано**.  
2. A1: login **и** header switcher; smoke-routes `/admin/login` (+ `/login` shared panel heading) — **сделано (A1-audit)**. A2: schedule + bookings — **сделано (A2-audit)**. A3: directory / справочники — **сделано (A3-audit)**. A4: задачи / Kanban — **сделано (A4-audit)**. A5: чаты / каналы — **сделано (A5-audit)**. A6: CRM / маркетинг — **сделано (A6-audit)**. A7: деньги клиники — **сделано (A7-audit)**. A8: лента / отчёты + e2e dashboard — **сделано (A8-audit)**. A9: система — **сделано (A9-audit)**. A9b: RBAC JSON — **сделано (A9b-audit)**. A10: shared хвосты — **сделано (A10-audit)**. A11: e2e хвосты — **сделано (A11-audit)**. A12: гейт grep — **сделано**; **A12-audit:** 401 admin `code: unauthorized` + удалена мёртвая `BOOKING_STATUS_LABEL_RU`; Playwright **17 passed** на свежем `dist/` (не цифра A11). **A12-repass:** 405/502 transport codes + узкий empty-db heuristic.  
3. Гейт A12 закрыт: кириллица в **chrome** админки = дыра. Остаток — нумерованный «Вне очереди». **A12-repass:** 405/502/traceback → transport `code` (админ EN Alert); heuristic empty-db сужен.  
4. @SCRIBE: `documentation/` уровень 1 на EN; RU сохранить как вторичный.  
5. CONTRIBUTING.md полностью EN (отдельный батч, не смешивать с i18n UI).

**Гейт:** иностранец проходит demo без знания русского на критическом пути админки.

### Wave 2 — Не стыдно называть majority-Enterprise

Только красные тряпки, не закрытие `PHASE_FULL_CLOSURE_BACKLOG`.

1. Честный раздел Architecture в README = слои + tenancy + workers (без обещания RLS-everywhere).  
2. Вычистить «box product» из публичных фраз; SKU gate оставить в коде.  
3. Не тащить архив волн в первые ссылки; курсы не в git (`local/intern-courses/`).  
4. Один `GOOD FIRST ISSUE` / demo script в README.  
5. Badge CI (существующие GHA) на README.

**Вне скоупа (океан, не озеро):** полный RLS, ребренд, перевод всех 500 md, новый биллинг, микросервисы, «закрыть ERP vNext».

---

## 6. Публичная карта документации (что показывать)

```
GitHub visitor
 ├─ README.md                          ← единственный вход (EN)
 ├─ documentation/PRODUCT_OVERVIEW.md  ← что за продукт
 ├─ documentation/DEVELOPMENT.md       ← запуск (перевести в Wave 1)
 ├─ documentation/CREDENTIALS_REFERENCE.md  ← DEMO only
 ├─ docs/product_state/INDEX.md        ← факты по коду (можно RU до Wave 1)
 └─ docs/archive/…                     ← история процесса, не канон
```

`local/intern-courses/` — онбординг стажёра, **gitignore**, не витрина продукта. Указатель: [`local/README.md`](../../local/README.md).

Канон инженерии для контрибьюторов: `docs/RAG_CANON.md` + `DOCUMENTATION_POLICY.md` — в Wave 1 дать English pointer, не полный перевод.

---

## 7. Стек (канон для README, сверено с lock/файлами)

| Слой | Технология | Зачем |
|------|------------|--------|
| API | Python 3.11, FastAPI, Uvicorn, Pydantic v2 | REST `/api/v1` |
| Домен | SQLAlchemy 2 + asyncpg, Alembic | PostgreSQL 16 source of truth |
| Очереди | Celery + Redis 7 | outbox, уведомления, фон |
| Кэш / лимиты | Redis | сессии короткоживущие, rate limit, отчёты |
| Фронт | React 18, TypeScript, Vite 6 | SPA: marketing / admin / patient PWA |
| UI kit | Mantine 7, Tabler icons | operational contour |
| Данные UI | TanStack Query 5 | серверный кэш, не Redux-дерево |
| Наблюдаемость | Prometheus `/metrics`, Grafana dashboards в `deploy/` | ops |
| Поставка | Docker Compose, Jenkins→GHCR, optional Docker Hub, GHA PR gates | Law 21 |
| Качество | pytest, ruff/black/mypy, vitest, Playwright, githooks | |

Интеграции **включаются конфигом** (нет ключа → модуль тих): платежи (YooKassa и шлюзы клиники), SMS/email/мессенджеры, patient OAuth, captcha, OpenAI-compatible AI.

---

## 8. Тенантность — как есть (не как коробка)

```
Platform (founder / vendor)     /platform/*
  └── Organization (SaaS tenant)
        └── Clinic (operational tenant, clinic_id)
              ├── Staff (RBAC)
              └── Patient (PWA /c/:clinicSlug, /app)
```

Изоляция сегодня: **application-layer** (`clinic_id` / `organization_id` в сервисах и репозиториях) + негативные тесты. RLS — точечно (`organization_entitlements`), не на всём домене (ADR-007 Option B). Это **не** «коробка с одной БД на клиента»; это **shared-schema multi-tenant**. Для GitHub этого достаточно и это правда.

Редакция `EDITION=box|basic` — **срез SKU**, не архитектура. Default: полный продукт.

---

## 9. Возражение (Law 23)

⚠️ **OBJECTION:** MIT (и Apache-2.0) **нельзя** ставить, если цель — запретить конкурентный Yclients-клон.  
**Basis:** MIT = право копировать, продавать, запускать конкурирующий SaaS. Это прямо противоположно запросу владельца.  
**Consequence:** «открыли как MIT» = отдали коммерцию.  
**Proposal:** PolyForm Shield + `Licensor Line of Business` (ADR-017). Не называть репозиторий OSI Open Source.  
→ Принято владельцем 2026-08-17.

---

## 10. Гейты публикации (человек)

Law 40: агент не делает `git commit` / `git push`. Человек:

1. Прочитать README глазами «я не из команды».  
2. `LICENSE` уже в дереве (PolyForm Shield). Проверить глазами Required Notice.  
3. Убедиться, что в git нет `.env` и боевых секретов.  
4. Прогнать `docker compose up` + demo login из `CREDENTIALS_REFERENCE.md`.  
5. Создать запись в `/admin/schedule` на пустом слоте.  
6. Только потом public GitHub.

---

## 11. Completeness (эта волна)

| Класс | Состояние |
|-------|-----------|
| Публичный вход EN | DECIDED — README + overview |
| LICENSE SPDX | DECIDED — `LicenseRef-PolyForm-Shield-1.0.0`, ADR-017, Required Notice = Zaporozhan |
| Календарь P0 (мёртвый клик / silent submit) | DECIDED — исправлено + vitest |
| Курсы стажёров в git | OUT — `local/intern-courses/` gitignore |
| i18n админки EN default | DECIDED — A0–A12 в коде, гейт chrome 2026-08-18. Patient/маркетинг/`index.html` — DECLARED-OPEN, не эта волна ([`ADMIN_I18N_EN_ROADMAP.md`](./ADMIN_I18N_EN_ROADMAP.md)) |
| Перевод всего `docs/` | OUT — океан; архив остаётся историей |
| Ребренд / RLS-everywhere | OUT |
| Inline create patient in schedule modal | DECLARED-OPEN — P1, не блокер клика по слоту |

---

Reference: `README.md` · `LICENSE` · `docs/adr/ADR-017-source-available-polyform-shield.md` · `docs/artifacts/ADMIN_I18N_EN_ROADMAP.md` · `documentation/PRODUCT_OVERVIEW.md` · `docs/adr/ADR-007-platform-multitenancy-super-admin.md` · `frontend/src/config/edition.ts` · `src/core/edition.py`
