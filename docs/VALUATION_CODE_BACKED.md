# Dental Booking — Code‑Backed Valuation (RF market)

Этот документ фиксирует **фактическую оценку системы и стоимости** для рынка РФ в двух моделях продажи:

- **MVP+ (лицензия/передача кода + внедрение/сопровождение)**
- **SaaS (продажа продукта как бизнеса)**

Ключевое правило: **все выводы опираются только на код** и снабжены проверяемыми ссылками на файлы/модули.

---

## 1) Фактическая “комплектация продукта” по коду (что реально есть)

### 1.1 Ширина продукта (API‑модули)

В `src/api/v1/router.py` подключён большой набор доменных модулей. Это сильный сигнал “не шаблон”, а полноценная ERP‑платформа:

- **ядро записи**: `auth`, `patients`, `doctors`, `services`, `schedule`, `bookings`  
  Доказательство: `src/api/v1/router.py`.
- **платежи/предоплата**: `payments`, `admin_prepayment`, `admin_payment_gateway`  
  Доказательство: `src/api/v1/router.py`, `src/api/v1/routers/payments.py`, `src/api/v1/routers/admin_payment_gateway.py`.
- **финансы/ERP‑контуры**: `admin_finance`, `admin_payroll`, `admin_inventory`, `admin_reports`, `admin_reports_aggregate`  
  Доказательство: `src/api/v1/router.py`.
- **CRM/Tasks**: `admin_crm`, `admin_tasks`, `admin_task_boards`, `admin_task_streams`, `admin_task_tags`  
  Доказательство: `src/api/v1/router.py`.
- **staff collab**: `admin_staff_collab`, `admin_staff_announcement_policy`, `admin_staff_directory`, `admin_staff_profile`  
  Доказательство: `src/api/v1/router.py`.
- **omnichannel**: `admin_omni_chat`, `admin_omni_chat_closure_tags`, `integrations_gateway`, `owner_omni_channels`, `owner_omni_ai_settings`, `owner_omni_audit`  
  Доказательство: `src/api/v1/router.py`, `src/api/v1/routers/integrations_gateway.py`.
- **RBAC**: `admin_rbac_management`  
  Доказательство: `src/api/v1/router.py`, `src/api/v1/routers/admin_rbac_management.py`, `src/application/rbac_matrix.py`.
- **AI‑контуры**: `admin_ai_settings`, `admin_ai_status`, `admin_ai_reports`, `admin_ai_tasks_settings`, `ai_agent`, `admin_omni_tools`  
  Доказательство: `src/api/v1/router.py`, `src/api/v1/routers/admin_omni_tools.py`, `src/application/services/omnichannel_ai_orchestrator.py`.

### 1.2 Omnichannel inbox (операционный “внутренний чат”)

Подтверждённая функциональность omni‑чата:

- список/фильтры/назначение/resolve/close/quick replies/вложения/SSE/presence/аналитика/ai_mode toggle  
  Доказательство: `src/api/v1/routers/admin_omni_chat.py`.
- realtime: Redis pubsub → SSE  
  Доказательство: `src/infrastructure/realtime/omni_pubsub.py`, `src/api/v1/routers/admin_omni_chat.py`.
- UI экрана omni‑чата + E2E сценарии  
  Доказательство: `frontend/src/admin/pages/AdminOmniChatPage.tsx`, `frontend/e2e/admin-omni-chat.spec.ts`.

**Критическая граница по outbound** (важно для коммерческой оценки):

- Операторский outbound подтверждён кодом только для `TELEGRAM_BOT`, `WEB_WIDGET`, `WEB_APP`.  
  Доказательство: `src/application/services/omni_outbound_policy.py`, `src/application/services/omnichannel_outbound_dispatcher.py`.
- Inbound вебхуки есть для Telegram/WhatsApp/VK/Email/Instagram/Webchat.  
  Доказательство: `src/api/v1/routers/integrations_gateway.py`, `src/application/services/integration_gateway_service.py`.

### 1.3 AI (assistant + function calling tools)

AI‑оркестратор для omni‑чата:

- режимы `DISABLED / SUGGEST_ONLY / AUTO_REPLY` + полноценный function‑calling агент (tools loop)  
  Доказательство: `src/application/services/omnichannel_ai_orchestrator.py`.
- UI‑эндпоинт “какие инструменты доступны текущему админу”  
  Доказательство: `src/api/v1/routers/admin_omni_tools.py`.

### 1.4 Платежи (“кассы”)

- YooKassa: создание платежа + webhook + подтверждение записи по оплате  
  Доказательство: `src/api/v1/routers/payments.py`, `src/application/services/payment_service.py`, `src/infrastructure/external_apis/yookassa_client.py`.
- Зашифрованные креды платёжных шлюзов per clinic (для расширений)  
  Доказательство: `src/api/v1/routers/admin_payment_gateway.py`, `src/application/services/clinic_payment_gateway_service.py`.

### 1.5 RBAC (Enterprise)

- каноническая матрица прав + роли owner/manager/admin/doctor  
  Доказательство: `src/application/rbac_matrix.py`.
- админ‑API RBAC: роли, пресеты, назначения, персональные overrides, политики, аудит  
  Доказательство: `src/api/v1/routers/admin_rbac_management.py`.

---

## 2) Оценка “готовности к продаже” по коду (не по докам)

### 2.1 Delivery/Infra‑готовность

- docker‑сборка/compose‑деплой/публикация образов, quality gates (ruff/mypy/pytest, eslint/vitest/build)  
  Доказательство: `Jenkinsfile`, `docker-compose.yml`, `pyproject.toml`, `frontend/package.json`.

Вывод: проект выглядит как **продукт, который можно запускать и обслуживать**, а не только демо‑код.

### 2.2 Тестируемость (как сигнал стоимости)

- backend quality gate включает `ruff`, `pytest` и аудит tenant‑колонок  
  Доказательство: `Jenkinsfile` (stage “Backend tests”).
- frontend gate включает `eslint`, `vitest`, `build`  
  Доказательство: `Jenkinsfile` (stage “Frontend tests”), `frontend/package.json`.
- E2E покрытие для ключевого дифференциатора (omni‑чат)  
  Доказательство: `frontend/e2e/admin-omni-chat.spec.ts`.

---

## 3) Модель стоимости #1: MVP+ (лицензия/код + внедрение)

### 3.1 Что именно продаётся (как актив)

В модели MVP+ покупатель покупает:

- исходники backend+frontend,
- схему данных/миграции (alembic),
- операционную админ‑панель,
- omni‑чат (inbox) + AI‑помощник (как продуктовую “фишку”),
- платежи/предоплату,
- RBAC + аудит.

Этот актив **дороже шаблонов** по двум причинам, подтверждённым кодом:

- Ширина ERP‑контуров (`admin_finance/payroll/inventory/crm/tasks/...`) — см. `src/api/v1/router.py`.
- Сложный операционный модуль omni‑чата + AI + realtime — см. `src/api/v1/routers/admin_omni_chat.py` и `src/application/services/omnichannel_ai_orchestrator.py`.

### 3.2 Рекомендованная вилка цены (РФ)

**Лицензия/исходники (без внедрения)**: **600k – 1.8M ₽**

**MVP+ “под ключ” (деплой+настройка+обучение)**: **900k – 2.5M ₽**

### 3.3 Почему именно так (формула)

Я использую 3 коэффициента, которые можно аудировать по коду:

- **S (scope breadth)**: число доменных контуров (ERP+omni+AI+payments+RBAC)  
  Подтверждение: `src/api/v1/router.py`.
- **D (delivery readiness)**: есть ли CI‑gate, docker‑деплой, тесты, миграции  
  Подтверждение: `Jenkinsfile`, `docker-compose.yml`, `pyproject.toml`, `frontend/package.json`.
- **R (risk / gaps)**: известные границы, которые потребуют добработок  
  Подтверждение: ограничение outbound‑каналов в `src/application/services/omni_outbound_policy.py`.

Реалистично:

- S высокий → цена растёт.
- D высокий → цена растёт (покупатель платит за “поставляемость”).
- R умеренный/высокий (если целевой рынок требует VK/WA outbound) → цена снижается или выделяется в отдельный roadmap.

---

## 4) Модель стоимости #2: SaaS (продажа как бизнеса)

### 4.1 Важное: код ≠ SaaS‑оценка

SaaS оценивается не “по строкам кода”, а по метрикам:

- MRR/ARR
- churn/retention
- CAC/LTV
- gross margin
- темпы роста

**Код влияет косвенно**: снижает cost‑to‑serve и повышает конверсию/retention (например, omni‑инбокс + AI).

### 4.2 Привязка стоимости к ARR (РФ ориентиры)

Ориентиры мультипликаторов в РФ для малого B2B SaaS (без международных премий):

- **0–3 платящих клиента / нестабильный MRR**: чаще “asset deal” → **2.5 – 6.0M ₽**
- **есть подтверждённый MRR**: обычно **1.0× – 3.0× ARR**

Пример расчёта:

- MRR 300k ₽ ⇒ ARR 3.6M ₽ ⇒ оценка ~ **3.6 – 10.8M ₽**
- MRR 800k ₽ ⇒ ARR 9.6M ₽ ⇒ оценка ~ **9.6 – 28.8M ₽**

### 4.3 Почему omni‑чат + AI реально повышают SaaS‑оценку (по коду)

Потому что это “операционный центр” продукта, который:

- ускоряет обработку лидов (inbox, статусы, claim/resolve),
- даёт управляемость (аналитика, RBAC, audit),
- снижает нагрузку на операторов (AI suggest/auto reply, function‑calling tools).

Подтверждение: `src/api/v1/routers/admin_omni_chat.py`, `src/application/services/omnichannel_ai_orchestrator.py`, `frontend/src/admin/pages/AdminOmniChatPage.tsx`.

---

## 5) Итоговый “ценник” (если упростить)

Если продавать **как код/продукт (MVP+)**:

- **600k – 1.8M ₽** (лицензия/исходники)
- **900k – 2.5M ₽** (под ключ, внедрение)

Если продавать **как SaaS**:

- без стабильного MRR: **2.5 – 6.0M ₽**
- с MRR: **1–3× ARR** (плюс/минус в зависимости от churn/роста/маржи)

---

## 6) Что нужно, чтобы зафиксировать верхнюю границу (только code-backed)

Чтобы честно обосновать верх вилки, обычно нужны (и это тоже можно подтвердить по коду/инфре):

- прямые outbound‑адаптеры для целевых каналов (если WA/VK обязателен)  
  Сейчас по коду outbound ограничен: `src/application/services/omni_outbound_policy.py`.
- health‑checks/monitoring/алерты/DR runbooks (часть уже есть в CI/compose, см. `Jenkinsfile`, `docker-compose.yml`).

