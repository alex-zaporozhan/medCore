# 📐 ENGINEERING_PLAN — Протоколы системы
> Как система работает изнутри: состояния сессии, передача между ролями, эскалация, quality gate.
> Версия: 2.3 | Синхронизирован с системой ролей; слой **S:** `docs/product_state/` (см. §5); METRICS_PROTOCOL §6

---

## 1. МАШИНА СОСТОЯНИЙ СЕССИИ

@LEAD управляет состоянием проекта от старта до деплоя.

```
[IDLE]
  │ пользователь пишет @LEAD
  ▼
[СТАРТ]
  └── @CREATOR (один вопрос пользователю)
        → внутри: INDUSTRY INTELLIGENCE
        → внутри: @BIZ → KILL SIGNAL + MARKET_AUDIT.md
        → внутри: @DOMAIN_EXPERT → BUSINESS_ROUTES.md
        → пользователю: готовый пакет на утверждение
        → артефакты: BUSINESS_LOGIC.md + MARKET_AUDIT.md + BUSINESS_ROUTES.md
  │ пользователь утвердил пакет
  ▼
[ПЛАНИРОВАНИЕ]
  └── @LEAD: PRE-PLAN GATE (7 пунктов)
  └── @ARCH → SAAS_ARCHITECTURE_SPINE_2026.md + DEV_PROMPTS_*.md (с Domain Checklist)
  │ план утверждён пользователем
  ▼
[ТОННЕЛЬ] ← последовательное выполнение фаз
  ├── @DEV → код → отчёт
  ├── @QA_ARCH → QA_REPORT_*.md → 🟢 или назад @DEV  ← ОБЯЗАТЕЛЬНЫЙ GATE
  ├── @QA → тестирование
  ├── @SEC → аудит безопасности (SAAS/ENTERPRISE)
  │
  │ при аномалии → [АУДИТ] → @AUDITOR → возврат в тоннель
  │ при системном дефекте → [ПЛАНИРОВАНИЕ] (пересмотр ARCH)
  ▼
[QUALITY GATE] ← все P0/P1 закрыты, @QA_ARCH выдал 🟢
  │ пользователь: "деплоить"
  ▼
[DONE] → @OPS (вручную) → @LAWYER (при необходимости)
```

**Правила переходов:**

| Из | В | Условие |
|----|---|---------|
| СТАРТ | ПЛАНИРОВАНИЕ | BUSINESS_LOGIC.md + MARKET_AUDIT.md + BUSINESS_ROUTES.md созданы, KILL SIGNAL ✅ |
| ПЛАНИРОВАНИЕ | ТОННЕЛЬ | PRE-PLAN GATE пройден (7 пунктов), пользователь утвердил план |
| ТОННЕЛЬ (после DEV) | ТОННЕЛЬ (QA_ARCH) | @DEV отчитался о всех to-dos |
| ТОННЕЛЬ (QA_ARCH) | ТОННЕЛЬ (QA) | @QA_ARCH выдал 🟢 по всем векторам |
| ТОННЕЛЬ (QA_ARCH) | ТОННЕЛЬ (DEV) | @QA_ARCH нашёл 🔴 — возврат с конкретным списком |
| ТОННЕЛЬ | АУДИТ | 3 итерации DEV↔QA_ARCH без результата / аномалия |
| АУДИТ | ТОННЕЛЬ | Причина найдена, промпт для @DEV готов |
| АУДИТ | ПЛАНИРОВАНИЕ | @AUDITOR нашёл системный дефект архитектуры |
| QUALITY GATE | DONE | Пользователь явно сказал "деплоить" |

---

## 2. TRANSMISSION PROTOCOL

Роль передаёт управление только с явным контрактом. @LEAD формулирует если роль не сформулировала сама.

```
ПЕРЕДАЧА @[ОТПРАВИТЕЛЬ] → @[ПОЛУЧАТЕЛЬ]

Контекст:      [суть задачи одной фразой]
Вход:          [файлы, контракты, данные для работы]
Ожидание:      [конкретный артефакт на выходе]
Критерий:      [как проверить что сделано правильно]
Блокеры:       [что мешает / что неизвестно]
```

**Примеры по ролям:**

```
ПЕРЕДАЧА @DEV → @QA_ARCH

Контекст:  модуль Finance/Кассы реализован
Вход:      @src/pages/FinancePage.tsx @src/hooks/useFinance.ts
           @src/api/routers/finance.py
Ожидание:  QA_REPORT_Finance.md
Критерий:  все 10 векторов @QA_ARCH проверены (Вектор 10 — N/A с обоснованием или выполнен), вердикт 🟢 или список 🔴 для @DEV
Блокеры:   нет
```

```
ПЕРЕДАЧА @AUDITOR → @ARCH

Контекст:  кнопка "Сохранить расписание" не даёт POST в Network
Вход:      admin.py (строки 3126–3228), custom_page.html
Ожидание:  архитектурное решение — как гарантировать выполнение скрипта после DOM
Критерий:  typeof window.scheduleConstructorSave === "function"
           и POST появляется в Network при клике
Блокеры:   неизвестно точно, в head или body выполняется скрипт в продакшне
```

```
ПЕРЕДАЧА @CREATOR → @LEAD

Контекст:  старт проекта [название] завершён
Вход:      BUSINESS_LOGIC.md + MARKET_AUDIT.md + BUSINESS_ROUTES.md
Ожидание:  PRE-PLAN GATE + архитектурное планирование
Критерий:  spine обновлён, DEV_PROMPTS_Phase1.md готов
Блокеры:   [нет / что осталось неясным]
```

---

## 3. ЭСКАЛАЦИЯ ПО УРОВНЯМ

Роль не молчит и не угадывает — эскалирует.

```
Уровень 1 — роль справляется сама
Уровень 2 — Round Table (нужно мнение смежных ролей)
Уровень 3 — эскалация к @LEAD (решение за рамками роли)
Уровень 4 — @LEAD блокирует фазу, запрашивает пользователя
```

**Триггеры:**

**Уровень 2:**
- @ARCH предлагает решение влияющее на безопасность → зовёт @SEC
- @DEV видит что реализация изменит API контракт → зовёт @ARCH
- @QA_ARCH нашёл баг с неясной причиной → зовёт @ARCH + @DEV
- @QA_ARCH нашёл Missing Feature → зовёт @DOMAIN_EXPERT для gap-анализа

**Уровень 3:**
- Роль не может сформулировать критерий готовности
- Решение требует изменения архитектуры целиком
- Обнаружен риск который KILL SIGNAL не поймал
- @QA_ARCH находит одно и то же 🔴 после трёх итераций @DEV

**Уровень 4:**
- Противоречие между бизнес-требованием и техническим ограничением
- Нужно удалить или переписать >50% кода
- Обнаружена юридическая проблема
- KILL SIGNAL срабатывает на уже запущенном проекте

---

## 4. QUALITY GATE ПЕРЕД ДЕПЛОЕМ

@LEAD проводит лично, не делегирует.

```
□ @QA_ARCH:  все модули получили 🟢, QA_REPORT_*.md существуют
□ @ARCH:     все решения задокументированы в SAAS_ARCHITECTURE_SPINE_2026.md (и модульных файлах по необходимости),
             контракт ошибок зафиксирован
□ @QA:       все сценарии покрыты, нет открытых P0/P1
□ @SEC:      (SAAS/ENTERPRISE) аудит без критических находок
□ @AUDITOR:  если вызывался — рекомендации учтены или явно отклонены
             с датой и причиной
□ @OPS:      конфиги готовы, README для клиента написан
□ SEED:      prod-seed запущен и идемпотентен (docs/SEED_PROTOCOL.md)
□ Пользователь: явно сказал "деплоить"
```

---

## 5. КОНВЕНЦИЯ ИМЕНОВАНИЯ АРТЕФАКТОВ

### 5.0 Слои P / S / W (кратко)

По `docs/ENTERPRISE_ROLE_SYSTEM_RESTRUCTURE_PLAN.md`: **P** — норма процесса в `docs/` (роли, шаблоны, паспорта); **S** — состояние продукта в **`docs/product_state/`** (канон, allowlist, INV-1 — см. `docs/product_state/README.md`); **W** — рабочие хвосты в **`docs/artifacts/`** (`DEV_PROMPTS_*`, `QA_REPORT_*`, черновики волн). Код и тесты — первичный факт поведения; при конфликте с S обновлять S (INV-4).

**Топология подпапок** (`adr/`, `operations/`, `architecture/` и т.д.): **`docs/DOC_TOPOLOGY.md`**.

### 5.1 Рабочие и проектные артефакты — `docs/artifacts/`

**W и долгоживущие проектные файлы** по-прежнему размещаются в **`docs/artifacts/`**. В корне **`docs/`** (вне `artifacts/` и `product_state/`) — системные файлы: роли (`ROLE_*.md`), шаблоны (`TEMPLATE_*.md`), универсальные паспорта (`*_PASSPORT.md`, `DOMAIN_STANDARDS.md` и т.п.), планы инженерии вроде этого файла.

```
docs/artifacts/
  SAAS_ARCHITECTURE_SPINE_2026.md — единый каркас архитектуры (@ARCH); точечно ARCH_MODULE_* по теме
  PRODUCT_OPERATING_CORPUS_2026.md — продукт, фазы, операционный контекст
  BUSINESS_LOGIC.md              — бизнес-логика (компактный канон)
  BUSINESS_ROUTES.md             — карта API/SPA (сверять с кодом)
  MARKET_AUDIT.md                — конкурентный анализ (@BIZ)
  SME_BOX_NFR_CHECKLIST.md       — NFR коробки
  DEVELOPMENT_PLAN.md            — текущий фокус (@LEAD)
  METRICS_REGISTRY.md            — реестр M-XX
  README.md · ARTIFACT_MAP.md    — индекс слоя W
  DEV_PROMPTS_[НАЗВАНИЕ].md      — инструкция для @DEV (по волне)
  QA_REPORT_[МОДУЛЬ].md          — отчёт бизнес-аудита (@QA_ARCH)
  PRINCIPLE_FINDINGS_*.md        — @PRINCIPLE
  DESIGN_*.md                    — @DESIGN
  … (SEC_*, OPS_*, и т.д. по необходимости)

  История волн и старые сетки промптов — в git; не плодить ARCH_DEV_* без задачи @LEAD.
```

### 5.2 Состояние продукта (слой S) — `docs/product_state/`

Канонические **выходы** @SCRIBE и иные снимки «что продукт умеет сейчас» — по списку в **`docs/product_state/README.md`**. Примеры целевых путей: `PRODUCT_KNOWLEDGE_BASE.md`, `SALES_PITCH.md`, `USER_DOCS/`, при появлении — `openapi.json`. **Не дублировать** эти классы в `docs/artifacts/` без решения @LEAD (INV-1). Реестр метрик **M-XX** до переноса: `docs/artifacts/METRICS_REGISTRY.md` (INV-6, `METRICS_PROTOCOL` §5).

```
docs/product_state/
  README.md                      — состав S, allowlist RAG, INV-1 / INV-6, разрешение дублей
  PRODUCT_KNOWLEDGE_BASE.md      — создаётся @SCRIBE (когда запущен прогон)
  SALES_PITCH.md                 — создаётся @SCRIBE
  USER_DOCS/                     — пользовательская документация @SCRIBE
```

---

## 6. КТО ЧИТАЕТ ЭТОТ ФАЙЛ И КОГДА

| Роль | Когда | Какой раздел |
|------|-------|-------------|
| @LEAD | при каждом переходе между фазами | 1, 4 |
| @LEAD | при передаче между ролями | 2 |
| @AUDITOR | при диагностике зависшего бага | 3 |
| @QA_ARCH | при эскалации найденной проблемы | 3 |
| @QA, @SEC, @OPS | перед деплоем | 4 |
| @ARCH, @DEV, @SCRIBE | при создании артефактов и слоя S | §5.1–§5.2, `docs/product_state/README.md` |
| @PRINCIPLE | при G4 (агрегат / отчёт / KPI / новая метрика) | `docs/METRICS_PROTOCOL.md` §2–§4 |
| @QA_ARCH | при аудите модуля с метриками, дашбордами, отчётами, событиями | `docs/METRICS_PROTOCOL.md` §3.1–§3.3 (вектор 10 в `ROLE_QA_ARCH`) |
| @LEAD | при приоритизации KPI, временных исключениях по карточке метрики, триггерах §4 протокола | `docs/METRICS_PROTOCOL.md` §4–§5 · `docs/ROLE_LEAD.md` п.11 |
| @ARCH | при проектировании витрин, наблюдаемости, новых M-XX | `docs/METRICS_PROTOCOL.md` §2.3–§5 · `docs/artifacts/METRICS_REGISTRY.md` |
| @DEV | при инструментации и отчётном коде | `docs/METRICS_PROTOCOL.md` §2.3 · `docs/ROLE_DEV.md` |
| @QA | перед релизом с отчётами/дашбордами | `docs/ROLE_QA.md` (согласование с QA_REPORT / метрики) |
| @SEC | при аудите перед деплоем, если есть телеметрия / product events | `docs/METRICS_PROTOCOL.md` §3.3 · `docs/ROLE_SEC.md` P16 |
| @DESIGN | при SPEC/AUDIT экранов с KPI и графиками | `docs/METRICS_PROTOCOL.md` §2.1 · `docs/ROLE_DESIGN.md` |

---

Reference: docs/ROLE_LEAD.md · docs/ROLE_QA_ARCH.md · docs/ROLE_QA.md · docs/ROLE_ARCH.md · docs/ROLE_DEV.md · docs/ROLE_SEC.md · docs/ROLE_DESIGN.md · docs/ROLE_AUDITOR.md · docs/METRICS_PROTOCOL.md · docs/CRYSTALS.md
