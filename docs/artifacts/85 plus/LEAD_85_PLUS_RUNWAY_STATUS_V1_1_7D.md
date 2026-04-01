# LEAD_85_PLUS_RUNWAY_STATUS_V1_1_7D

> **Формат:** 7-дневный план закрытия красных зон runway с доказательствами.  
> **Принцип:** без evidence задача не считается закрытой.

---

## 1) Цель на 7 дней

Перевести статус runway из `NO-GO` в состояние, где:
- нет открытых критичных блокеров A1/A2,
- есть проверяемый evidence pack для решения `GO-WAIVER` или `GO`.

---

## 2) День-за-днем (D1..D7)

| День | Критичный пункт | Действие | Owner | Обязательное доказательство |
|------|------------------|----------|-------|-----------------------------|
| D1 | A2 RED: payments authz boundary | Закрыть доступ к create-payment только для валидного субъекта/тенанта | DEV BE + QA_ARCH | PR + негативные тесты + API contract evidence |
| D2 | A2 RED: celery reminders critical | Исправить `run_reminders` сигнатуру/вызов + regression test beat-task | DEV BE | PR + тест + CI green на task suite |
| D3 | A1 RED: supply-chain chain gap | Добавить в release pipeline `scan -> sbom -> sign -> provenance` как hard dependencies | DEVOPS + DEV | workflow diff + CI run + artifacts links |
| D4 | A1 RED: immutable deploy discipline | Убрать прод-зависимость от mutable tags; зафиксировать deploy по digest | OPS | deploy spec + staging dry-run logs |
| D5 | A3 YELLOW: integration evidence | Заполнить G1..G8 evidence минимум по критичным G1/G3/G4/G7 | QA_ARCH + OPS | заполненный gate-report + ссылки на smoke/tests |
| D6 | B2 UNKNOWN: design P0 evidence | Подтвердить D1..D6 для P0 (ContextBar/tables/drawers/severity/accessibility) | DESIGN + DEV FE + QA | UI evidence pack (`before/after`, checklist, acceptance) |
| D7 | C1/C2 readiness | Собрать единый launch evidence pack + провести финальный review протокол | LEAD + QA_ARCH + OPS | signed review note + verdict (`GO`/`GO-WAIVER`) |

---

## 2.1 Dual-track привязка дней

| День | BOX track вклад | ENTERPRISE track вклад |
|------|------------------|-------------------------|
| D1 | Закрытие платежного доверия для коробки | Базовый tenant/authz стандарт |
| D2 | Стабильность напоминаний и no-show контур | Надёжность фоновых задач |
| D3 | Минимально безопасный release baseline | Основа enterprise supply-chain |
| D4 | Коробочный deploy без mutable риска | Governance deploy policy |
| D5 | Box-critical gates evidence | Enterprise integration evidence base |
| D6 | P0 UX readiness для продаваемой коробки | Единый дизайн-контур как масштабируемая база |
| D7 | Решение `GO-BOX` или `NO-GO` | Решение `GO-ENT` roadmap-status |

---

## 3) Daily stop rules

1. Если D1 или D2 не закрыт — дальнейшие шаги считаются подготовительными, но запуск невозможен.
2. Если D3 или D4 не закрыт — supply-chain verdict остаётся ниже `C2`.
3. Если D5 без evidence — integration readiness не подтверждён.
4. Если D6 без evidence — design verdict ниже `D2`.
5. Если D7 без подписанного протокола — launch decision недействителен.
6. Если нет раздельных вердиктов `BOX` и `ENTERPRISE` — день считается не закрытым.

---

## 4) Минимальный отчет в конце каждого дня

| Поле | Формат |
|------|--------|
| Что обещали закрыть сегодня | 1-3 пункта |
| Что фактически закрыто | done/partial/block |
| Ссылки на evidence | PR/CI/report |
| Новые риски | кратко |
| План на завтра | конкретные действия |

---

## 5) Критерий “неделя успешна”

Неделя считается успешной только если:
1. D1..D4 закрыты полностью,
2. по D5 и D6 есть проверяемый evidence,
3. D7 содержит формальный вердикт и подписанный launch note.
4. Есть отдельные статусы: `BOX sellability` и `ENTERPRISE sellability`.
