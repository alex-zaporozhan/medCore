## 📈 ARCH_MARKETING_ATTRIBUTION — Сквозная аналитика и UTM

> Роли: @ARCH, @BIZ, @LEAD.  
> Цель: спроектировать модуль Marketing Attribution — от UTM‑меток и источников трафика до денег и ROI по каналам.  
> На этом этапе — архитектура, без реализации.

---

## 1. Задача и связь с текущими модулями

- Сейчас:
  - лендинг (`LANDING_WEB_FRONTEND.md`) уже умеет отправлять лиды (`/api/leads`) с `meta.page/anchor`;
  - есть домены Leads/CRM (см. `ARCH_CRM_KANBAN.md`) и Payments/ERP (см. `ARCH_ERP_FINANCE_AND_INVENTORY.md`).
- Задача:
  - связать **источник трафика** (UTM/канал) → **лид** → **запись** → **оплата** → **выручка**;
  - дать владельцу клиники честный дашборд:
    - «сколько денег принёс Яндекс/ВК/Instagram/Telegram»;
    - ROI и стоимость привлечённого клиента по каналам.

---

## 2. Сущности маркетинговой атрибуции

### 2.1. TrafficSource / Campaign

**TrafficSource**

- Назначение: агрегированный источник трафика (канал).
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `code: str` (`yandex_ads`, `vk_ads`, `instagram`, `direct`, `referral`, `offline` и т.п.);
  - `name: str`;
  - `description: str | None`.

**Campaign**

- Назначение: рекламная кампания в пределах источника.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `traffic_source_id: UUID`;
  - `name: str`;
  - `external_id: str | None` (ID кампании в Яндекс/ВК и т.п., если ведётся);
  - `budget_planned: Decimal | None`;
  - `date_start: date | None`;
  - `date_end: date | None`.

### 2.2. UTM и сессии

**VisitAttribution**

- Назначение: хранит UTM‑данные первого визита клиента.
- Поля:
  - `id: UUID`;
  - `clinic_id: UUID`;
  - `patient_id: UUID | None`; // связывается после регистрации/первой записи;
  - `lead_id: UUID | None`; // связь с CRM‑лидом;
  - `traffic_source_id: UUID | None`;
  - `campaign_id: UUID | None`;
  - `utm_source: str | None`;
  - `utm_medium: str | None`;
  - `utm_campaign: str | None`;
  - `utm_content: str | None`;
  - `utm_term: str | None`;
  - `landing_page: str | None`;
  - `created_at: datetime`;
  - `session_id: str | None` (идентификатор сессии/куки).

Связывание:

- при первом заполнении формы/записи/чата с utm‑параметрами создаётся `VisitAttribution` (с session_id);
- когда клиент авторизуется (Patient) или создаётся `LeadCard`, `VisitAttribution` обновляется:
  - проставляется `patient_id`/`lead_id`.

### 2.3. Связи с финансовыми сущностями

- `LeadCard` (см. ARCH_CRM_KANBAN):
  - расширяется полями:
    - `visit_attribution_id: UUID | None`;
    - дублирование utm‑полей как кэша (опционально).
- `FinancialTransaction` (ERP):
  - добавляется:
    - `lead_id: UUID | None`;
    - `visit_attribution_id: UUID | None`;
  - это позволяет строить отчёты:
    - «какая выручка пришлась на какой источник».

---

## 3. Потоки атрибуции

### 3.1. Лендинг → лид

1. Пользователь переходит по рекламной ссылке на лендинг:
   - `https://.../?utm_source=yandex&utm_medium=cpc&utm_campaign=brand&utm_content=...`.
2. Frontend:
   - сохраняет utm‑параметры в `localStorage`/куки и в состоянии страницы.
3. При отправке формы `GetStarted`:
   - в payload backend‑эндпоинта `/api/leads` добавляются:
     - utm‑параметры;
     - `landing_page`, `anchor`.
4. Backend:
   - создаёт `LeadCard` и `VisitAttribution`:
     - `lead_id` установлен;
     - `patient_id` пока `NULL`.

### 3.2. Чат/PWA → пациент и визиты

1. Если клиент после лендинга:
   - устанавливает PWA/заходит в чат/авторизуется как пациент;
   - frontend пробрасывает utm‑идентификатор/сессию при первом запросе.
2. Backend:
   - находит существующий `VisitAttribution` по session_id/utm и связывает:
     - `patient_id` (при создании `Patient`);
     - `lead_id` (если CRM‑лид уже создан или создаётся).

### 3.3. Оплата и завершение визита

1. При оплате/завершении визита:
   - `FinancialTransaction` создаётся для `Booking` (см. ERP);
   - если у `Booking.patient_id` есть `VisitAttribution` (по пациенту/лиду):
     - `FinancialTransaction.visit_attribution_id` и `lead_id` заполняются.
2. В результате:
   - каждая денежная операция знает, из какого источника и кампании пришёл клиент.

---

## 4. Отчёты и аналитика

### 4.1. Базовые отчёты владельца

**Отчёт «ROI по каналам»**

- Для заданного периода:
  - группировка по `TrafficSource` и/или `Campaign`:
    - `leads_count` — количество лидов (LeadCard) с атрибуцией;
    - `bookings_count` — количество записей;
    - `completed_bookings_count`;
    - `unique_patients_count`;
    - `revenue_sum` — сумма `FinancialTransaction.amount` по `income`, привязанных к этим лидам/атрибуциям;
    - `avg_check` — средний чек;
    - поля для ввода/учёта маркетинговых затрат (`ad_spend`) → `ROI = revenue_sum / ad_spend`.

**Отчёт «Качество трафика»**

- Метрики:
  - коэффициент конверсии:
    - `lead → booking`;
    - `booking → completed`;
  - среднее время от первого контакта до денег по источнику.

### 4.2. UI

- Владелец видит:
  - дашборд с колонками по каналам:
    - `Лиды`, `Записи`, `Дошли`, `Выручка`, `ROI`;
  - возможность провалиться в детали по кампании:
    - список лидов/пациентов/визитов.

---

## 5. API и frontend‑изменения

### 5.1. Frontend (лендинг + PWA)

- Лендинг:
  - при монтировании Hero:
    - считывает utm‑параметры из URL;
    - сохраняет их в `localStorage`/контексте;
  - при отправке форм:
    - добавляет utm‑данные в тело запроса (`submitLead`, `/api/leads`).
- PWA:
  - при первой авторизации пациента:
    - пробрасывает utm‑/session‑идентификатор в backend для связывания с `VisitAttribution`.

### 5.2. Backend API

- Расширение существующего `/api/leads`:
  - приём utm‑параметров и метаданных страницы;
  - создание `VisitAttribution`.
- Новый роутер `admin_marketing_attribution.py`:
  - `GET /api/v1/admin/attribution/summary` — сводный отчёт;
  - `GET /api/v1/admin/attribution/campaigns` — список кампаний и их метрик;
  - `POST /api/v1/admin/attribution/campaigns` — ручной ввод/редактирование кампаний и их плановых бюджетов.

RBAC:

- доступ к отчётам — только ролям `Owner` и `Manager` (см. `ARCH_RBAC_AND_TASKS.md`).

---

## 6. Инварианты и ограничения

1. **Лёгкое отключение:** модуль атрибуции не должен ломать основную бизнес‑логику при отсутствии utm/данных.
2. **Простота хранения:** utm‑данные и связи не должны дублироваться во множестве мест, достаточно:
   - `VisitAttribution` + ссылки из LeadCard и FinancialTransaction.
3. **Конфиденциальность:** utm‑параметры не содержат ПДн, их можно безопасно использовать в AI‑аналитике и отчётах.

После согласования этого документа @LEAD сможет создать `DEV_PROMPTS_MARKETING_ATTRIBUTION.md` для реализации.

