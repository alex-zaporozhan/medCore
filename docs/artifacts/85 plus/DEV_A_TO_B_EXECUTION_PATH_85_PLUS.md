# DEV_A_TO_B_EXECUTION_PATH_85_PLUS

> **Для кого:** @DEV (backend/frontend/devops)  
> **Цель:** один линейный файл “что делать от A до B”, без переключения между множеством артефактов.  
> **Принцип:** шаг не закрыт без evidence.

**Визуал админки / токены:** единый канон **Swiss Slate / Ink** — `docs/artifacts/85 plus/DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6; маршрут унификации — `docs/artifacts/85 plus/LEAD_DESIGN_UNIFICATION_ROUTE_SWISS_SLATE_INK.md`.

---

## 1) Как использовать этот файл

1. Идти строго по шагам `A1 -> A2 -> A3 -> B1 -> B2 -> B3 -> C1 -> C2 -> C3`.
2. На каждом шаге фиксировать:
   - что сделано,
   - где PR,
   - где тесты/CI,
   - где evidence.
3. Если шаг блокирован — не “пропускать”, а ставить `BLOCKED` и причину.

---

## 2) Step-by-step (A -> B -> GO)

## A. Stabilize foundation

### A1 — Supply-chain and release hardening
**Задача**
- Довести CI/CD до обязательной цепочки: `scan -> sbom -> sign -> provenance -> publish -> digest deploy`.

**Что сделать**
1. В workflow добавить hard dependencies между этими job’ами.
2. Убрать прод-зависимость от mutable tags.
3. Проверить, что release policy соответствует `C2+`.

**DoD**
- есть PR с workflow-изменениями,
- есть успешный CI run c artifacts (scan/sbom/sign/provenance),
- есть evidence, что deploy идёт по digest.

**Execution status (2026-03-26)**
- **Status:** `BLOCKED (external: GitHub Actions quota/billing; deferred until 2026-04-06)`.
- **Что сделано:**
  1. В `.github/workflows/docker-images.yml` введена обязательная цепочка jobs с hard dependencies: `scan -> sbom -> sign -> provenance -> publish -> digest deploy`.
  2. Удалены mutable release tags (`main`, `latest`) из publish-процесса; publish идёт по `:${{ github.sha }}`.
  3. Добавлена проверка digest deploy (compose resolution с `image@sha256:*`) + artifact evidence (`compose.resolved.yml`).
  4. В `docker-compose.yml` и `.env.example` убрана прод-дефолтная зависимость от `:latest`; зафиксирован контракт на immutable digest для staging/prod.
- **PR links:** `https://github.com/alex-zaporozhan/smart-business-os/pull/1`.
- **CI/test links:** 
  - PR checks page: `https://github.com/alex-zaporozhan/smart-business-os/pull/1/checks`
  - latest run (head `6ca2198`): `https://github.com/alex-zaporozhan/smart-business-os/actions/runs/23613241622`
  - blocked jobs: `Backend tests (pytest + ruff)`, `Frontend tests (lint + build + vitest)`, `backend`
  - root cause (from check annotations): `The job was not started because recent account payments have failed or your spending limit needs to be increased`
- **Evidence links:** 
  - code: `.github/workflows/docker-images.yml`, `.github/workflows/backend-ci.yml`, `.githooks/pre-commit`, `.githooks/pre-push`, `scripts/dev/pre_push_gate.sh`, `scripts/dev/pre_commit_gate.sh`, `docker-compose.yml`, `.env.example`
  - PR checks page: `https://github.com/alex-zaporozhan/smart-business-os/pull/1/checks`
  - local gate proof: commit `6ca2198` passed local pre-push full gate before push
  - artifacts: `supply-chain-*` и `digest-deploy-evidence` не формируются, пока Actions jobs не стартуют из-за quota block.
- **Риск/блокер:** внешний лимит GitHub Actions (billing/quota). CI jobs не стартуют; publish chain до Docker Hub не может быть валидирован онлайн.
- **Next action:** после обновления лимита (ориентир `2026-04-06`) сделать `Re-run failed jobs` для PR #1, получить green run и artifacts (`supply-chain-*`, `digest-deploy-evidence`), затем перевести `A1 = DONE (fully evidenced)`.

---

### A2 — DB/Cache P0 blockers
**Задача**
- Закрыть 2 критичных блока:
  1) payment authz boundary,
  2) reminders task reliability.

**Что сделать**
1. Ограничить `create_payment` валидным субъектом/тенантом.
2. Исправить reminders task и добавить regression test.

**DoD**
- PR #1 (payments authz) + негативные тесты,
- PR #2 (reminders) + regression test,
- CI green по релевантным тестам.

**Execution status (2026-03-26)**
- **Status:** `BLOCKED (external: GitHub Actions quota/billing; deferred until 2026-04-06)`.
- **PR #1 — payments authz boundary:**
  1. `POST /api/v1/payments` ограничен валидным субъектом: только `patient`-контекст.
  2. Добавлена защита от cross-subject доступа: пациент не может создать оплату для чужого `booking_id` (возвращается `PAYMENT_BOOKING_NOT_FOUND`).
  3. Негативные тесты добавлены: unauth/system forbidden; foreign booking rejected.
- **PR #2 — reminders task reliability:**
  1. Исправлен bind-контракт periodic task: `notifications.run_reminders` теперь `bind=True` и не падает из-за сигнатуры.
  2. Добавлен dedup перед enqueue: если reminder по тому же `booking_id` + `template` уже существует, повторно не ставим задачу.
  3. Regression test добавлен (signature + dedup behavior).
- **PR links:** 
  - payments authz: `https://github.com/alex-zaporozhan/smart-business-os/pull/2`
  - reminders reliability: `https://github.com/alex-zaporozhan/smart-business-os/pull/3`
- **Code evidence:** `src/api/v1/routers/payments.py`, `src/infrastructure/messaging/tasks/notifications.py`, `tests/api/test_payments_authz_and_reminders.py`, `tests/api/test_reminders_reliability.py`.
- **CI/test links:** 
  - PR #2 checks: `https://github.com/alex-zaporozhan/smart-business-os/pull/2/checks`
  - PR #3 checks: `https://github.com/alex-zaporozhan/smart-business-os/pull/3/checks`
  - blocking symptom: jobs in required workflows do not start; annotation reason is billing/quota block (`job was not started... spending limit`)
- **Риск/блокер:** внешний лимит GitHub Actions (billing/quota), из-за чего невозможно получить обязательный green CI proof для PR #2/#3.
- **Next action:** после обновления лимита (ориентир `2026-04-06`) сделать rerun checks на PR #2/#3, зафиксировать green links и перевести `A2 = DONE (fully evidenced)`.

---

### A3 — Integration gates operationalization
**Задача**
- Ввести реальный evidence по критичным gate-сценариям.

**Что сделать**
1. Заполнить минимум `G1/G3/G4/G7` evidence.
2. Привязать runbooks и smoke evidence к gate-report.

**DoD**
- есть заполненный gate-report,
- ссылки на тесты/smoke/runbooks доступны и проверяемы.

**Execution status (2026-03-26)**
- **Status:** `NOT STARTED (blocked by A1/A2 + external CI quota block until 2026-04-06)`.
- **Причина:** по stop-rules шаг `A3` не стартует до закрытия evidence/CI по `A1/A2`; онлайн CI подтверждение временно недоступно из-за GitHub Actions billing/quota.

---

## B. Standardize product UX

### B1 — Token contract adoption
**Задача**
- Выровнять код с `docs/artifacts/85 plus/DESIGN_TOKENS_85_PLUS.json` и каноном **Swiss Slate / Ink** (`DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6.2a).

**Статус базы (2026-03+):** глобальные `frontend/src/theme.ts`, `frontend/src/index.css` и JSON-токены уже приведены к свотчу §1; **B1** в текущем цикле = **аудит дрейфа**: sweep ad-hoc hex / локальные тени вне токенов на экранах, которые трогает **B2**.

**Что сделать**
1. Подтвердить diff `DESIGN_TOKENS_85_PLUS.json` ↔ `theme.ts` / `:root` (нет расхождений по семантике §3.6.2a).
2. По мере работ **B2** удалять/заменять inline-цвета и одноразовые тени в затронутых файлах на токены/Mantine `brand`/`gray`/`green`/`yellow`/`red`.

**DoD**
- короткая таблица “current → target token” для остаточных отклонений (если есть),
- P0-экраны после B2 не вводят новых запрещённых hex (§3.6.2a).

**Execution status (2026-03-30)**
- **Status:** `DONE (dev implemented, evidenced)`.
- **Что сделано:**
  1. Проведен drift sweep по admin runtime экранам (`frontend/src/admin/pages/*`, `frontend/src/admin/layouts/*`).
  2. Удалены/заменены ad-hoc surface/bg отклонения на токенизированные shell colors.
  3. Выделены shared UI contracts для chat chrome и settings sections, чтобы не накапливать повторный drift.
- **Evidence links:**
  - `docs/artifacts/85 plus/B1_TOKEN_DRIFT_TABLE_2026-03-30.md`
  - `frontend/src/shared/adminChatChrome.ts`
  - `frontend/src/shared/ui/AdminSettingsSectionCard.tsx`

---

### B2 — P0 design implementation (админка по концепту + бэклог DGN-P0)

**Задача**
- Внедрить **паттерны и поведение** из `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` (§3–4, детально **§3.6**) на P0-контуре админки, **не** переписывая продукт «с нуля», а унифицируя shell, таблицы, drawer, семантику и a11y.

**Связь с `DESIGN_P0_P1_BACKLOG.md` (один шаг B2 = закрытие P0-блоков):**

| B2 подпункт | ID бэклога | Суть |
|-------------|------------|------|
| Единый заголовок / sticky actions | **DGN-P0-01** | `ContextBar` на всех admin pages |
| Таблицы: toolbar, density, empty/loading/error | **DGN-P0-02** | Tasks, Reports, Patients, Bookings |
| Drawer сущностей | **DGN-P0-03** | Booking / Patient / Doctor / Service |
| Severity на ops-экранах | **DGN-P0-04** | Tasks, Omni Chat, Emergency notifications |
| A11y safety net на P0 | **DGN-P0-05** | keyboard, focus, contrast spot-check |

**Что сделать (порядок рациональный)**
1. **DGN-P0-01** — выровнять все страницы §2 инвентаря админки на единый header-контракт (§4 концепта, §3.6.3 слой 3).
2. **DGN-P0-02** — одна табличная «матрица» для четырёх экранов (§3.6.3–3.6.4, состояния §5).
3. **DGN-P0-03** — единый каркас drawer (§3.6.6, §3.6.11 футер).
4. **DGN-P0-04** — выровнять critical/warning/info к семантическим токенам §3.6.2a (не смешивать с brand-ink без роли).
5. **DGN-P0-05** — чеклист §6 концепта на затронутых экранах; evidence для релиза.

**Кто исполняет (никакой одной «магической роли» в Cursor)**
- **Реализация в коде:** @DEV FE (агент в новом окне с контекстом `frontend/` + ссылки на концепт и DGN-ID).
- **Приёмка визуала и границ scope:** @DESIGN (или владелец концепта).
- **Evidence / WCAG spot:** @QA_ARCH или назначенный QA.
- **Вердикт merge и приоритет:** @LEAD.

Запуск «просто нового чата» имеет смысл как **сессия @DEV FE** с явным промптом: «закрыть DGN-P0-0x по `DESIGN_P0_P1_BACKLOG.md`, сверяясь с `DESIGN_ENTERPRISE_85_PLUS_CONCEPT.md` §3.6; не менять бизнес-логику и API; один PR на блок или один PR на DGN-P0-02 чтобы не разнести регресс». Плохая стратегия — один промпт «перекрась всю админку»: это нарушает архитектуру и обзор PR.

**DoD**
- по каждому из **DGN-P0-01 … 05** есть PR (или сгруппированный PR с явным списком), скрин/evidence, статус в бэклоге,
- пакет **P0 UI evidence** (before/after или чеклист по экранам),
- вердикт @DESIGN / @LEAD: нет критичного drift от §3.6 (цвет, тени, motion §3.6.12, зеркальность §3.6.11 где применимо).

**Повторный проход B2:** если база токенов обновлена (Swiss §1), **B2 не отменяет B1** — B2 переигрывается как «ещё раз пройти P0-паттерны» с тем же DoD, чтобы выловить остаточный локальный стиль.

**Execution status (2026-03-30)**
- **Status:** `DONE (dev implemented) / PENDING SIGN-OFF (@DESIGN + @QA_ARCH)`.
- **Что сделано:**
  1. `DGN-P0-01`: header contract через `ContextBar` на admin контуре.
  2. `DGN-P0-02`: table/surface contract для Bookings/Patients/Reports + aligned surfaces на Tasks.
  3. `DGN-P0-03`: unified entity drawer chrome (`Booking/Patient/Doctor/Service`).
  4. `DGN-P0-04`: severity semantics через `SEMANTIC.opsSeverity` на ops-экранах.
  5. `DGN-P0-05`: a11y safety net spot-check и локальные улучшения (aria labels / message regions).
- **Evidence links:**
  - `docs/artifacts/85 plus/B2_P0_UI_A11Y_EVIDENCE_2026-03-30.md`
  - `frontend/src/shared/ui/AdminDrawer.tsx`
  - `frontend/src/shared/adminChatChrome.ts`

---

### B3 — P1 stabilization
**Задача**
- Закрывать P1-блоки без срыва BOX-продаж.

**Что сделать**
1. CRM/pipeline стандартизация.
2. settings/forms стандартизация.
3. chat/omni convergence.

**DoD**
- задачи P1 переведены в PR и status updated,
- нет критичного UI drift в enterprise-модулях.

**Execution status (2026-03-30)**
- **Status:** `DONE (dev implemented, evidenced)`.
- **Что сделано:**
  1. `P1-01`: CRM/Pipeline visual standard на Sales/Marketing/Retention.
  2. `P1-02`: unified settings form contract (`AdminSettingsSectionCard`) на AI/OmniAI/Integrations/Payment.
  3. `P1-03`: chat/omni convergence через shared chat chrome (patient/staff/omni admin chats).
  4. `P1-04`: numeric/table consistency improvements в reports/marketing surfaces.
  5. `P1-05`: проверен и зафиксирован Box/Enterprise integrity gate (edition guards + scope boundaries).
  6. Дополнительно: PWA compatibility uplift (icons/maskable/apple touch/screenshots + refresh UX).
- **Evidence links:**
  - `docs/artifacts/85 plus/B3_P1_STABILIZATION_EVIDENCE_2026-03-30.md`
  - `docs/artifacts/85 plus/BOX_PACKAGE_CONTRACT.md`
  - `frontend/src/config/edition.ts`

---

## C. Final launch readiness

### C1 — Unified evidence pack
**Собрать**
1. Release compliance report.
2. Integration gate report.
3. DB/Cache audit status.
4. Design readiness report.

**DoD**
- единый evidence pack сформирован и доступен команде.

---

### C2 — Final review
**Задача**
- Совместный review: @LEAD + @QA_ARCH + @OPS + @DEV.

**DoD**
- подписанный протокол решения: `GO` / `GO-WAIVER` / `NO-GO`.

---

### C3 — Controlled launch
**Задача**
- staging -> smoke -> prod approval -> prod deploy.

**DoD**
- post-launch smoke пройден,
- post-launch report опубликован.

---

## 3) Dual-track правило для @DEV

На каждом цикле фиксируй **2 статуса**:
1. `BOX sellability` (готово/не готово и почему),
2. `ENTERPRISE sellability` (готово/не готово и почему).

Запрещено закрывать итерацию одним общим “готово”.

---

## 4) Ежедневный DEV чеклист (копипаст)

| Поле | Что заполнить |
|------|---------------|
| Day | D1..D7 |
| Step | A1/A2/A3/B1/B2/B3/C1/C2/C3 |
| Planned | что делаем сегодня |
| Done | done/partial/blocked |
| PR links | ссылки |
| CI/test links | ссылки |
| Evidence links | ссылки |
| Risks | что мешает |
| Next action | что завтра |

---

## 5) Локальный hardening-режим (до восстановления GitHub Actions minutes)

**Период:** с текущего момента до `2026-04-06` (или до ручного подтверждения, что CI jobs снова стартуют).

**Режим обязателен:**
1. Только PR-ветки (`a1-supply-chain-hardening`, `a2-payments-authz`, `a2-reminders-reliability`), без merge/push в `main`.
2. Локальные hooks обязательны:
   - `pre-commit` (быстрый gate по staged файлам),
   - `pre-push` (полный gate backend+frontend).
3. Любое изменение фиксируется кратким локальным отчетом с лог-ссылками.

**Формат краткого локального отчета (заполнять на каждое изменение):**

| Поле | Что указать |
|------|-------------|
| Date/Time (UTC) | время прогона |
| Branch | ветка |
| Change summary | 1-2 строки, что изменено |
| Pre-commit | PASS/FAIL + путь к логу |
| Pre-push | PASS/FAIL + путь к логу |
| Target PR | ссылка на PR |
| Risks | что осталось рискованным |
| Next action | следующий шаг |

**Пути логов:**
- `.tmp_ci_logs/local-pre-commit-gate.log`
- `.tmp_ci_logs/local-pre-push-gate.log`

---

## 6) Zero-friction resume checklist (на 2026-04-06)

**Цель:** за один проход восстановить online evidence и закрыть `A1/A2` в `DONE (fully evidenced)`.

### 6.1 Ветки/PR для немедленного rerun
- `a1-supply-chain-hardening` -> PR #1: `https://github.com/alex-zaporozhan/smart-business-os/pull/1`
- `a2-payments-authz` -> PR #2: `https://github.com/alex-zaporozhan/smart-business-os/pull/2`
- `a2-reminders-reliability` -> PR #3: `https://github.com/alex-zaporozhan/smart-business-os/pull/3`

### 6.2 Required checks (должны быть green)
- `Backend CI / backend`
- `CI (tests) + Build & push Docker images / Backend tests (pytest + ruff)`
- `CI (tests) + Build & push Docker images / Frontend tests (lint + build + vitest)`
- `CI (tests) + Build & push Docker images / E2E frontend pages (Playwright)`

### 6.3 Expected artifacts/evidence для A1
- `supply-chain-scan`
- `supply-chain-sbom`
- `supply-chain-signatures`
- `supply-chain-provenance`
- `digest-deploy-evidence`

### 6.4 Порядок восстановления
1. Проверить, что billing/quota разблокирован и jobs стартуют.
2. На PR #1/#2/#3 нажать `Re-run failed jobs`.
3. Дождаться завершения required checks.
4. Для PR #1 зафиксировать ссылки на artifacts (`supply-chain-*`, `digest-deploy-evidence`).
5. Обновить `Execution status` блоки `A1/A2`: статус `DONE (fully evidenced)` + ссылки.
6. Только после этого стартовать `A3`.

---

## 7) GO-WAIVER (временное правило до 2026-04-06)

**Решение:** `B-work allowed in parallel, but no C2/C3/launch decisions until A1/A2 DONE`.

**Расшифровка:**
1. Разрешено выполнять `B1/B2/B3` (backend/frontend продуктовые задачи) параллельно с блоком `A`.
2. Статусы `A1/A2` не повышаются без online CI evidence после разблокировки quota.
3. Любые решения уровня launch (`C2/C3`, `GO`) запрещены до закрытия `A1/A2` в `DONE (fully evidenced)`.
4. После `2026-04-06` приоритетный шаг — закрыть `A1/A2` rerun-ами, затем снять waiver.

---

## 8) Stop rules (для @DEV)

1. Нет тестов/evidence -> задача не закрыта.
2. Нет PR/CI proof -> статус не повышается.
3. Есть открытый L3 -> не идём в launch.
4. Нет раздельных BOX/ENTERPRISE статусов -> итерация не принята.
