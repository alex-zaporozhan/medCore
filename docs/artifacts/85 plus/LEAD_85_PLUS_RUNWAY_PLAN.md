# LEAD_85_PLUS_RUNWAY_PLAN — “самолет на взлетной полосе” (A -> B)

> **Роль:** @LEAD  
> **Цель:** дать команде один линейный, исполнимый сценарий от текущего состояния до финального `GO` без разрывов и “серых зон”.

---

## 1) Что это даёт команде

Этот документ = единая “взлётная полоса”:

1. входные условия (до запуска),
2. пошаговый маршрут (что делать и в каком порядке),
3. стоп-линии (`NO-GO`),
4. критерии “успешного взлёта”.

Правило: если шаг не имеет evidence, шаг считается незавершённым.

---

## 2) Pre-flight (обязательно до старта)

### 2.1 Артефакты должны быть на месте

- `QA_ARCH_85_PLUS_ROADMAP.md`
- `QA_ARCH_85_PLUS_8W_EXECUTION_TRACKER.md`
- `LEAD_INTEGRATION_GATES.md`
- `LEAD_DB_CACHE_AUDIT.md`
- `LEAD_CICD_SUPPLY_CHAIN_GATES.md`
- `LEAD_DESIGNER_TZ_ENTERPRISE_85_PLUS.md`
- `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md`
- `DESIGN_SCREEN_AUDIT_MATRIX.csv`
- `DESIGN_TOKENS_85_PLUS.json`
- `DESIGN_COMPONENT_MAPPING.md`
- `DESIGN_P0_P1_BACKLOG.md`
- `LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md`

### 2.2 Роли подтверждены

- @LEAD — финальный вердикт
- @ARCH — архитектурные решения
- @QA_ARCH — evidence и quality gate
- @DEV / @OPS — реализация и эксплуатация
- @DESIGN — UI/UX стандартизация

### 2.3 “Запреты перед выкатом”

1. Нет ручных обходов гейтов.
2. Нет релизов без evidence-пакета.
3. Нет “сначала выкатим, потом доделаем P0”.

---

## 3) Линейный маршрут A -> B

> В режиме продаж используется dual-track:
> - **Track BOX:** “продаём сейчас” после закрытия коробочных блокеров,
> - **Track ENTERPRISE:** “доращиваем без паузы” до governance-grade уровня.

## A. Stabilize foundation

### Step A1 — Security and supply-chain lock
- Выполнить `S1..S10` из `LEAD_CICD_SUPPLY_CHAIN_GATES.md`.
- Пройти compliance минимум `C2`.

**Exit gate A1:** нет открытых L3, release chain не bypass'ится.

### Step A2 — DB/Cache risk closure
- Закрыть P0 из `LEAD_DB_CACHE_AUDIT.md`:
  - payments authz boundary,
  - alembic drift control,
  - celery reminders critical fix.

**Exit gate A2:** DB/Cache контур без L3 блокеров.

### Step A3 — Integration gates baseline
- Включить рабочий цикл `G1..G8` из `LEAD_INTEGRATION_GATES.md`.
- Для каждого gate есть runbook и evidence.

**Exit gate A3:** интеграционные стопперы отсутствуют.

---

## B. Standardize product UX (enterprise shell)

### Step B1 — Design token adoption
- Выполнить Step 0/1 из `LEAD_DESIGN_IMPLEMENTATION_PLAYBOOK_85_PLUS.md`.

**Exit gate B1:** token contract принят DESIGN + DEV.

### Step B2 — P0 design implementation
- Выполнить D1..D6 (ContextBar, tables, drawers/modals, severity, accessibility).

**Exit gate B2:** design verdict минимум `D2`.

### Step B3 — P1 stabilization wave
- Выполнить P1-пул задач из `DESIGN_P0_P1_BACKLOG.md`.

**Exit gate B3:** нет критичного UI drift в enterprise-модулях.

---

## C. Operational readiness and final launch

### Step C1 — Evidence pack assembly
- Собрать единый evidence-пакет:
  - CI/CD compliance report,
  - integration gates report,
  - DB/Cache audit status,
  - design readiness report.

**Exit gate C1:** пакет полон и проверяем.

### Step C2 — Final readiness review
- Финальный review @LEAD + @QA_ARCH + @OPS.
- Проверка стоп-условий.

**Exit gate C2:** решение `GO` или `GO-WAIVER`.

### Step C3 — Controlled launch
- staging deploy -> smoke -> prod approval -> prod deploy.
- Post-launch smoke и наблюдение по алертам.

**Exit gate C3:** “успешный взлёт” подтвержден метриками.

---

## 3.1 Dual-track режим (обязательно)

### Track BOX (салоны / сети салонов)

1. Обязательные условия `GO-BOX`:
   - закрыты критичные блокеры A1/A2, влияющие на коробку,
   - design readiness для P0 не ниже `D2`,
   - нет открытых L3 по box-критичным цепочкам,
   - есть box evidence pack (smoke + UX + ops-lite runbooks).
2. Цель: коммерческий запуск BOX без ложных enterprise-обещаний.

### Track ENTERPRISE (масштабный бизнес)

1. Обязательные условия `GO-ENT`:
   - supply-chain compliance не ниже `C2`,
   - integration gates `G1..G8` подтверждены evidence,
   - DB/Cache/tenant/edition контуры без открытых L3,
   - есть полный operational transparency pack.
2. Цель: enterprise-ready контур для крупных сделок и тендеров.

### Правило параллельного исполнения

Запуск BOX не останавливает ENTERPRISE трек;  
ENTERPRISE дорабатывается отдельными итерациями, пока BOX проходит пилоты/продажи.

---

## 4) Stop-line matrix (что блокирует взлёт)

Любой пункт ниже = автоматический `NO-GO`:

1. Любой L3 в integration/db/cache/supply-chain.
2. CI/CD compliance ниже `C2` без утверждённого waiver.
3. Design readiness ниже `D2` для P0 экранов.
4. Нет runbook/evidence по критичным гейтам.
5. Есть противоречие Box/Enterprise UX и server-side policy.
6. Для dual-track нет раздельного вердикта `GO-BOX` и `GO-ENT`.

---

## 5) Definition of Successful Takeoff

“Успешный взлёт” засчитывается только если одновременно:

1. Supply-chain verdict: `C2` или выше.
2. Design verdict: `D2` или выше.
3. Нет открытых L3 рисков в `LEAD_INTEGRATION_GATES.md` и `LEAD_DB_CACHE_AUDIT.md`.
4. Staging и prod smoke пройдены, evidence сохранён.
5. Команда имеет план следующей волны улучшений без критичных долгов P0.
6. Зафиксированы 2 статуса: `BOX sellability` и `ENTERPRISE sellability`.

---

## 6) Одностраничный операционный чек (для запуска)

1. Pre-flight completed.
2. A1 -> A2 -> A3 завершены.
3. B1 -> B2 завершены, B3 запланирован/выполнен.
4. C1 evidence pack complete.
5. C2 approval signed.
6. C3 launch complete.
7. Post-launch report опубликован.

Если любой пункт “нет” — запуск не выполняется.
