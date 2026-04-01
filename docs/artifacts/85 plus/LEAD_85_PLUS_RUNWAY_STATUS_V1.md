# LEAD_85_PLUS_RUNWAY_STATUS_V1

> **Дата:** 2026-03-26  
> **Подход:** только evidence-based оценка по текущему репозиторию (без “галочек по обещаниям”).  
> **Шкала:** `GREEN` (подтверждено), `YELLOW` (частично), `RED` (критичный разрыв), `UNKNOWN` (нет достаточных данных).

---

## 1) Snapshot по “взлётной полосе”

| Блок | Статус | Вердикт |
|------|--------|---------|
| Pre-flight artifacts | `GREEN` | Артефакты 85+ присутствуют |
| A1 Security/Supply-chain lock | `RED` | CI сильно усилен, но цепочка не дотягивает до `C2` |
| A2 DB/Cache P0 closure | `RED` | Есть открытые P0 по payments authz и celery reminders |
| A3 Integration gates baseline | `YELLOW` | Gate-документ есть, но runbook/evidence база неполная |
| B1 Design token adoption | `YELLOW` | Токены/концепт готовы, внедрение в код подтверждено частично |
| B2 P0 design implementation | `UNKNOWN` | Нет полного proof по всем P0 экранам и D1..D6 |
| B3 P1 stabilization | `UNKNOWN` | На уровне планов/артефактов, без код-evidence закрытия |
| C1 Evidence pack assembly | `YELLOW` | Форматы отчётов есть, не заполнены для реального релиза |
| C2 Final readiness review | `UNKNOWN` | Формальная сессия review не зафиксирована |
| C3 Controlled launch | `UNKNOWN` | Нет evidence последнего полного цикла staging->prod |

---

## 1.1 Dual-track snapshot (BOX vs ENTERPRISE)

| Трек | Статус | Комментарий |
|------|--------|-------------|
| BOX sellability | `YELLOW/RED` | Коробочный оффер сформирован концептуально, но критичные A1/A2 блокеры ещё открыты |
| ENTERPRISE sellability | `RED` | До enterprise-purchasable уровня не хватает `C2+` compliance и полного evidence-cycle |

Правило: до появления отдельных evidence pack по BOX и ENTERPRISE статусы не повышаются.

---

## 2) Детализация с доказательствами

## 2.1 Pre-flight artifacts — `GREEN`

Наличие ключевых артефактов подтверждено:
- `LEAD_85_PLUS_RUNWAY_PLAN.md`
- `LEAD_INTEGRATION_GATES.md`
- `LEAD_DB_CACHE_AUDIT.md`
- `LEAD_CICD_SUPPLY_CHAIN_GATES.md`
- дизайн-пакет (`DESIGN_*`, `LEAD_DESIGN_*`)

Риск: организационный, не технический — нужно поддерживать актуальность версий.

---

## 2.2 A1 Security/Supply-chain lock — `RED`

### Что подтверждено (плюс)
- В `docker-images.yml` есть backend/frontend tests, lint, e2e, alembic upgrade.
- Есть scan workflow: `.github/workflows/security-trivy.yml`.
- Есть image tags по sha/main/latest.

### Что не закрыто до `C2` (критично)
1. В build/push контуре нет явных шагов **SBOM/sign/provenance**.
2. Для release всё ещё публикуется `latest`.
3. Нет доказанного enforce-порядка `scan -> sbom -> sign -> attest -> publish -> digest deploy` в одном mandatory workflow.

**Вывод:** `A1` не пройден.

---

## 2.3 A2 DB/Cache P0 closure — `RED`

Открытые P0 из аудита подтверждаются кодом:

1. **payments authz boundary**
   - `get_request_context` допускает fallback `system/unauthenticated`.
   - `create_payment` вызывает сервис по `booking_id` без явной tenant/subject авторизации в роуте.
2. **celery reminders critical**
   - `notifications.run_reminders` объявлен без `bind=True`, но функция принимает `self`.

**Вывод:** `A2` не пройден.

---

## 2.4 A3 Integration gates baseline — `YELLOW`

Плюс:
- `LEAD_INTEGRATION_GATES.md` формализует `G1..G8`, stop-rules и evidence schema.

Минус:
- специализированные runbook-файлы из gate-матрицы в явном виде не подтверждены в полном наборе.
- фактические релизные evidence-отчёты по G1..G8 не зафиксированы как completed.

**Вывод:** документ есть, операционное наполнение частичное.

---

## 2.5 B1/B2/B3 Design execution — `YELLOW/UNKNOWN`

Плюс:
- дизайн-пакет полноценный (concept, matrix, tokens, mapping, backlog, playbook).
- тема/токены в коде существуют (`frontend/src/theme.ts`, `frontend/src/index.css`).

Минус:
- нет полного code-evidence закрытия D1..D6 на всех P0 экранах.
- нет заполненного design readiness report с вердиктом `D2+`.

**Вывод:**
- B1: `YELLOW` (готово концептуально, частично подтверждено в коде),
- B2/B3: `UNKNOWN` до сквозной валидации.

---

## 2.6 C1/C2/C3 Launch readiness — `YELLOW/UNKNOWN`

Плюс:
- шаблоны compliance/evidence/report созданы.

Минус:
- нет заполненного end-to-end evidence pack на конкретный релиз.
- нет зафиксированного финального review и протокола controlled launch.

**Вывод:**
- C1: `YELLOW`,
- C2/C3: `UNKNOWN`.

---

## 3) Честный итог “можно ли взлетать сейчас”

**Сейчас: `NO-GO`.**

### По трекам:
- **BOX:** `NO-GO` до закрытия коробочных критичных блокеров.
- **ENTERPRISE:** `NO-GO` до достижения `C2+` и полного operational evidence.

Причины:
1. `A1` = `RED`,
2. `A2` = `RED`,
3. `B2`/`C2`/`C3` без достаточного evidence.

---

## 4) Что нужно сделать, чтобы перейти в “готов к взлёту”

### Critical now (24-72h)
1. Закрыть `payments authz boundary`.
2. Исправить `run_reminders` и добавить regression test.
3. Довести release workflow до mandatory supply-chain gate (`scan+sbom+sign+provenance`) и убрать зависимость от `latest` для prod.

### Next (после critical)
1. Заполнить первый реальный `Release Compliance Report` (C-level).
2. Закрыть D1..D6 evidence по design P0 и выдать `D2` verdict.
3. Собрать единый C1 evidence pack и провести C2 review.

---

## 5) Правило обновления статуса

Этот статус обновляется только при добавлении новых доказательств:
- PR/commit с исправлением,
- CI run/report URL,
- runbook/evidence attachments,
- formal decision record.

Без новых доказательств статус не повышается.
