# 🗺 DEVELOPMENT_PLAN — Dental Booking (исторический план)

> ВАЖНО: фактическое текущее состояние кода, модулей и интеграций описано в  
> `HANDOFF_AI_PRODUCT_AND_TECH_CURRENT.md` и кратко в `HANDOFF_AI_ONEPAGER.md`.
> Этот файл — **исторический план эволюции** (фазы 0–5) и бэклог идей, а НЕ источник правды
> о том, что уже реализовано. Для любого анализа всегда сначала смотрите HANDOFF и код.

---

## 0. Ось продукта и связь с PROCESS_LAUNCH

- Мы находимся в **Фазе 1–2 PROCESS_LAUNCH** (MVP → Стабильность) для SAAS‑продукта «Dental Booking».
- Этот `DEVELOPMENT_PLAN.md` разбивает работу на внутренние фазы проекта:
  - **Фаза 0:** Organization/Clinic (мультиклиника).
  - **Фаза 1:** Услуги + календарная сетка.
  - **Фаза 2:** Предоплата + умная очередь.
  - **Фаза 3:** Recall + омниканальные рассылки.
  - **Фаза 4:** Маркетинговая лента (акции/новости/сторис).
  - **Фаза 5:** Аналитика и тарифы (после первых денег).

Каждая фаза содержит:
- краткую цель,
- состав работ (backend / frontend),
- готовый **Transmission Protocol‑промпт** для @ARCH (если нужен) и @DEV.

### 0.1. Чек-лист фаз

- [x] Фаза 0 — Clinic, clinic_id, CRUD клиник, селектор (Organization/PatientClinic отложено)
- [x] Фаза 1.a — Услуги, ServiceDoctor, admin/public API
- [x] Фаза 1.b — Сетка расписания, drag&drop между врачами
- [x] Фаза 2 — Предоплата, очередь (PrepaymentPolicy, Waitlist, QueuePolicy)
- [x] Фаза 3 — Recall, рассылки
- [x] Фаза 4 — Маркетинг (лента, сторис)
- [x] Фаза 5 — Аналитика, тарифы, owner-dashboard

Детали: [SYS_DEVELOPMENT_PLAN_CHANGELOG.md](SYS_DEVELOPMENT_PLAN_CHANGELOG.md).

---

## Фазы (кратко)

- **Фаза 0** — Organization/Clinic: каркас сделан (Clinic, clinic_id, селектор); Organization/PatientClinic отложено. Промпты: [DEV_PROMPTS_DENTAL_BOOKING.md](DEV_PROMPTS_DENTAL_BOOKING.md), [ARCH_PROMPTS_DENTAL_BOOKING.md](ARCH_PROMPTS_DENTAL_BOOKING.md).
- **Фаза 1** ✓ — Услуги + ServiceDoctor + сетка расписания, drag&drop.
- **Фаза 2** ✓ — Предоплата + умная очередь.
- **Фаза 3** ✓ — Recall + рассылки.
- **Фаза 4** ✓ — Маркетинг (лента, сторис).
- **Фаза 5** ✓ — Аналитика, тарифы, owner-dashboard.

Детальные контракты и состав работ по фазам при необходимости восстанавливаются из архива или запроса к @ARCH/@DEV. Ниже — сокращённые цели фаз без объёмных промптов.

---

## Фаза 1 — Услуги + календарная сетка ✓

**Цель:** услуги per clinic, сетка «все врачи за день» + drag&drop. Выполнено.

---

## Фаза 2 — Предоплата + умная очередь ✓

**Цель:** политики предоплаты, waitlist, queue policy. Выполнено.

---

## Фаза 3 — Recall + омниканальные рассылки ✓

**Цель:** MessagingService, Recall, автоматизации по каналам. Выполнено.

---

## Фаза 4 — Маркетинговая лента (акции, новости, сторис) ✓

**Цель:** PromoPost, Story, лента в PWA. Выполнено.

---

## Фаза 5 — Аналитика и тарифы ✓

**Цель:** дэшборд владельца, метрики, тарифы Basic/Pro/Max. Выполнено.

---

## Текущее состояние и следующий шаг

По чек-листу 0.1 выполнены фазы 0–5. Детали и история: [SYS_DEVELOPMENT_PLAN_CHANGELOG.md](SYS_DEVELOPMENT_PLAN_CHANGELOG.md).

**Текущий пакет запросов (2026-02):** [REQUEST_BATCH_UI_AND_POLICIES.md](REQUEST_BATCH_UI_AND_POLICIES.md). Продукт — единое приложение без тарифов: все функции (каналы, интеграции, оформление, стикеры, скидки, политика уведомлений) включены по умолчанию. Историческая инструкция по фазам: [DEV_PROMPT_EDITIONS_AND_LEVELS.md](DEV_PROMPT_EDITIONS_AND_LEVELS.md).

---

## Пакет изменений (бэклог / фаза 6)

Зафиксированные запросы владельца, заложенные в план. Порядок приоритета уточняется @LEAD/@BIZ.

| № | Направление | Документ / содержание |
|---|-------------|------------------------|
| 1 | **Отчёт по врачам и администраторам** | Ежемесячный отчёт: врачи — часы/дни работы, сумма заработано; администраторы — часы/дни работы. Backend: агрегация по doctor_id / admin (сессии или факт действий) за период. Frontend: страница/раздел отчётов. См. [BIZ_YCLIENTS_HONEST_COMPARISON.md](BIZ_YCLIENTS_HONEST_COMPARISON.md). |
| 2 | **Интеграции: 1С, qMS, Битрикс24** | Прямые интеграции вместо только CSV. 1С: режим «1С API» (URL + ключ), контракт обмена. qMS: запрос к производителю, затем контракт. Битрикс24: входящий вебхук, создание лида при новой записи. См. [ARCH_INTEGRATIONS_1C_QMS_BITRIX24.md](ARCH_INTEGRATIONS_1C_QMS_BITRIX24.md). |
| 3 | **Чат + мессенджеры + история для AI** | Из админки отправка в «привычный мессенджер» клиента (Telegram, WhatsApp, VK). Сохранение истории из мессенджеров в БД, единая лента. Задел под AI-анализ переписок. См. [BIZ_CHAT_MESSENGERS_AND_AI.md](BIZ_CHAT_MESSENGERS_AND_AI.md). |
| 4 | **Web Push в PWA** | Push при новом сообщении в чате и новостях клиники. Без платной подписки (VAPID, свой backend). Запрос разрешения — при первом входе в чат/ленту или в настройках. См. [ARCH_WEB_PUSH_CLARIFICATION.md](ARCH_WEB_PUSH_CLARIFICATION.md), [REQUEST_BATCH_UI_AND_POLICIES.md](REQUEST_BATCH_UI_AND_POLICIES.md) (P1). |
| 5 | **Универсальный бизнес (клиники, стоматология, салоны)** | Адаптация под «любой бизнес»: выбор типа (клиника/стоматология/салон) или тип специалиста (врач/мастер). Максимально рациональные изменения по архитектуре, при необходимости переписывание части с нуля. См. [BIZ_PLAN_UNIVERSAL_BUSINESS_AND_PRICING.md](BIZ_PLAN_UNIVERSAL_BUSINESS_AND_PRICING.md). |

**Предоплата:** В коде уже опциональна (по умолчанию ВЫКЛ), политики по врачу/услуге (PrepaymentPolicy) реализованы. Бизнес-документация обновлена: [BUSINESS_LOGIC.md](BUSINESS_LOGIC.md), [BIZ_YCLIENTS_HONEST_COMPARISON.md](BIZ_YCLIENTS_HONEST_COMPARISON.md).

---

## Техдолг (зафиксировать до QA)

- **Frontend npm audit (PWA tooling):**
  - Обнаружены 4 high severity vulnerabilities в цепочке `serialize-javascript → @rollup/plugin-terser → workbox-build → vite-plugin-pwa`.
  - Для автофикса требуется `npm audit fix --force` с обновлением `vite-plugin-pwa` до `0.19.8` (breaking change).
  - Решение @LEAD: **оставить как есть до этапа QA/production hardening**, не выполнять `--force` в рабочем ветке.
  - План на QA: отдельная задача — обновить `vite-plugin-pwa` до безопасной версии, адаптировать конфиг Vite, прогнать `npm run build` и smoke‑тесты PWA.
