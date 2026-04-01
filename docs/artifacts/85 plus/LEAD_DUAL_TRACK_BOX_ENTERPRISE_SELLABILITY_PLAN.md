# LEAD_DUAL_TRACK_BOX_ENTERPRISE_SELLABILITY_PLAN

> **Роль:** @LEAD  
> **Цель:** переформатировать стратегию в 2 продаваемых пакета:  
> 1) **BOX** для салонов/сетей салонов (честно продаваемая коробка),  
> 2) **ENTERPRISE** модуль для масштабного бизнеса (высокая операционная зрелость).  
> **Опора:** `LEAD_PRODUCT_CRITIQUE_GAP_VS_ENTERPRISE.md`.

---

## 1) Главный принцип: не “один продукт на всех”, а 2 честных оффера

Ошибка, которая ломает продажи: обещать enterprise-уровень там, где реально готов только mid-level контур.  
Решение: разделить продукт на 2 явных коммерческих профиля и **доказывать ценность каждого отдельно**.

---

## 2) Пакет 1 — BOX (салоны и сети салонов)

## 2.1 Для кого

- Одиночные салоны красоты.
- Малые/средние сети салонов (несколько филиалов), без сложного compliance-контра.

## 2.2 Что клиент покупает (core value)

1. Стабильная онлайн-запись без срывов.
2. Умные напоминания и снижение no-show.
3. Базовая аналитика владельца (понятная и actionable).
4. Быстрый запуск без сложной интеграционной нагрузки.

## 2.3 “Точно куплю” для BOX — минимальный честный набор

### Must-have функционал
1. Booking + расписание + защита от дублей.
2. Напоминания (24h/2h) с предсказуемой доставкой.
3. CRM-light: карточка клиента, история визитов, простые сегменты.
4. Финансы-light: выручка, средний чек, no-show, конверсия.
5. Роли/доступы на уровне салона/сети без enterprise-сложности.

### Must-have надежность
1. Закрыты P0 из runway (`payments authz`, reminders reliability).
2. Еженедельный restore drill lite + подтверждённый runbook.
3. Нет критичных L3 рисков по Box-контру.

### Must-have UX
1. P0 дизайн-контур закрыт (`D2+`): header/table/drawer/severity/a11y.
2. Нет “мертвых” разделов и обманных enterprise-элементов в BOX.

## 2.4 Что НЕ обещаем в BOX

1. Полный enterprise compliance stack.
2. Продвинутая мультиконтурная governance-аналитика.
3. Тяжёлые owner-отчёты и расширенные enterprise-модули (если ограничены edition policy).

---

## 3) Пакет 2 — ENTERPRISE

## 3.1 Для кого

- Крупные сети, франшизы, корпоративные медицинские/beauty группы.
- Покупатели, которым нужны аудитопригодность, release safety, governance.

## 3.2 Что клиент покупает (core value)

1. Масштабируемую операционную систему, а не просто CRM/booking.
2. Контролируемую reliability под нагрузкой и инцидентами.
3. Доказуемую безопасность и предсказуемый релизный контур.

## 3.3 “Точно куплю” для ENTERPRISE — минимальный честный набор

### Must-have архитектура/операции
1. Supply-chain уровень не ниже `C2` (scan/sbom/sign/provenance/digest deploy).
2. Integration gates `G1..G8` с реальными evidence и runbooks.
3. DB/Cache enterprise hardening без открытых L3.
4. Multi-tenant/edition integrity без обходов и серых зон.

### Must-have коммерческая доказуемость
1. 1+ полный “чистый” релизный цикл с evidence pack.
2. Incident/readiness пакет: drills, postmortems, MTTR динамика.
3. Executive dashboard с SLA/SLO и operational risk индикаторами.

---

## 4) Сверх-строгий аудит текущего плана (что добавить)

## 4.1 Что уже правильно

1. Сильная документационная база и система гейтов.
2. Есть runway-подход и честный статус (`NO-GO` пока не закрыты красные зоны).
3. Есть дизайн-контур с приоритизацией внедрения.

## 4.2 Что не хватает для двух продаваемых пакетов

1. Нет формального **Package Contract** для BOX и ENTERPRISE (feature boundary + SLA boundary + evidence boundary).
2. Нет отдельного **Sales Readiness Checklist** по каждому пакету.
3. Нет “пробного продающего цикла” с измерением conversion drivers для BOX.
4. Нет отдельной дорожки “enterprise maturity while BOX sells”.

---

## 5) Двухпутевая стратегия (parallel tracks)

## Track A — BOX Monetization Now (0-60 дней)

### A1. Product contract BOX
- Зафиксировать “что входит/не входит”, edition-policy, UX и API ограничения.

### A2. Reliability close for BOX
- Закрыть красные P0 runway, влияющие на доверие владельца салона.

### A3. BOX Sales Kit
- Demo script, ROI one-pager, onboarding checklist, 30-day success metrics.

### A4. Pilot sales loop
- 3-5 пилотов, сбор возражений, итерации UX и пакета.

**KPI Track A:**
- pilot conversion rate,
- 30-day retention,
- no-show reduction,
- support ticket severity profile.

## Track B — Enterprise Maturity Continuous (0-120 дней)

### B1. Compliance and release hardening
- Довести supply-chain до `C2+`.

### B2. Integration reliability evidence
- Закрыть evidence по G1..G8.

### B3. Governance-grade operations
- Регулярные drill/postmortem и измеримый MTTR.

### B4. Enterprise deal readiness
- Security questionnaire pack, architecture dossier, readiness report.

**KPI Track B:**
- compliance level C2/C3,
- L3 incidents count,
- release predictability,
- enterprise PoC conversion.

---

## 6) “Честно продаваемо” критерии по каждому пакету

## BOX = sellable if all true
1. Нет открытых L3 по BOX-критичным цепочкам.
2. P0 дизайн и reliability закрыты.
3. Есть подтверждённый пилотный цикл и кейсы результата.
4. Команда может честно сказать “что не входит в BOX”.

## ENTERPRISE = sellable if all true
1. `C2+` supply-chain и доказанный release discipline.
2. Integration/DB/Cache гейты закрыты evidence-данными.
3. Есть operational transparency пакет (drill, MTTR, runbooks).
4. Нет edition/entitlement противоречий.

---

## 7) Пошаговый план внедрения в текущие 85+ файлы

### Step 1
- В `roadmap` и `tracker` добавить dual-track как обязательный execution mode.

### Step 2
- Создать `BOX_PACKAGE_CONTRACT.md` и `ENTERPRISE_PACKAGE_CONTRACT.md`.

### Step 3
- Создать `BOX_SALES_READINESS_CHECKLIST.md` и `ENTERPRISE_DEAL_READINESS_CHECKLIST.md`.

### Step 4
- Привязать runway daily-status к двум трекам (A/B) и публиковать weekly evidence.

### Step 5
- На каждом релизе фиксировать 2 вердикта: `BOX sellability` и `ENTERPRISE sellability`.

### Step 6
- Для presale использовать только актуальные версии:
  - `BOX_PACKAGE_CONTRACT.md`
  - `ENTERPRISE_PACKAGE_CONTRACT.md`
  - `LEAD_85_PLUS_RUNWAY_STATUS_V1.md` / `LEAD_85_PLUS_RUNWAY_STATUS_V1_1_7D.md`

---

## 8) Финальный @LEAD вердикт

Да, вы можете одновременно:
1. довести BOX до “честно продаваемо” и начать продажи,
2. параллельно тянуть enterprise maturity.

Но только если:
- BOX и ENTERPRISE разделены как **разные коммерческие контракты**,  
- и по каждому есть **свои доказательства готовности**, а не общий “мы почти готовы”.
