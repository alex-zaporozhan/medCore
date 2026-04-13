# Платформенный signup: приватность, хранение, доступ субъекта (LEAD)

> **Статус:** инженерный чеклист **заполнен по базовым пунктам** (2026-04-06); юридические тексты страниц — **вне scope репозитория**, финальная вычитка Product + юрист до рекламы **платного** публичного лендинга.  
> **Связь:** [SAAS_STRENGTHENING_MASTER_PLAN.md](./SAAS_STRENGTHENING_MASTER_PLAN.md) §19 п.13; сущности `platform_signup_intents` (контур B).

## 1. Цель обработки

- Заявка на подписку / регистрация Владельца до активации организации.
- Данные в БД: `platform_signup_intents` (email, phone, `tariff_snapshot`, статусы) — см. миграцию `20260406_platform_billing_contour_b`.

## 2. Чеклист (минимум до публикации лендинга)

| # | Тема | Статус | Примечание |
|---|------|--------|------------|
| 1 | Явное **согласие** на обработку ПДн в UI | ☑ инж. | **LEAD:** при появлении UI лендинга — чекбокс + ссылка на политику; тексты утверждает Product + юрист. До UI — требование зафиксировано в мастер-плане §5. |
| 2 | Страница **Политика конфиденциальности** (RU; структура EN) | ☑ инж. | **LEAD:** URL стабильны (`/privacy` или `/legal/privacy` — выбрать при внедрении фронта). Черновик правового текста — вне репо. |
| 3 | Страница **Условия использования** | ☑ инж. | Аналогично п.2 (`/terms`). Плейсхолдер в прод-рекламе **запрещён** (мастер-план). |
| 4 | **Срок хранения** черновиков и неактивных intent | ☑ инж. | **`expires_at`** выставляется при `POST .../public/platform/signup/checkout` (`PLATFORM_SIGNUP_INTENT_PAYMENT_TTL_DAYS`, по умолчанию 30). Фоновая пометка `expired`: Celery **`platform_billing.expire_stale_signup_intents`** (beat hourly). Поздний `payment.succeeded` по webhook B всё ещё переводит intent в `paid` (см. `apply_platform_yookassa_notification`). |
| 5 | **Право субъекта:** запрос копии / удаление до активации org | ☑ инж. | **LEAD:** канал — email поддержки или тикет OPS до self-service API; логировать обращение. API `DELETE` intent по токену — эпик DEV (Фаза 1b). |
| 6 | **Маскирование** в логах и экспортах (телефон, email) | ☑ инж. | `settings.log_mask_pii`; webhook payload в JSONB — без PAN; при логировании intent — не печатать полный email в INFO (SEC). См. [PLATFORM_BILLING_ERROR_CATALOG.md](./PLATFORM_BILLING_ERROR_CATALOG.md). |
| 7 | Rate limit / антибот на signup (C3) | ☑ инж. | **Checkout:** Redis per-IP + per-email (`RATE_PUBLIC_PLATFORM_CHECKOUT_*`). **Каталог лендинга:** per-IP на `GET .../public/platform/catalog/*`. **Webhook B:** per-IP (`RATE_PLATFORM_BILLING_WEBHOOK_*`). За reverse-proxy: **`PUBLIC_RATE_LIMIT_TRUSTED_PROXY_CIDRS`**. Пациентский auth: send-code/verify + Turnstile — как ранее. |

## 3. Ответственность

| Роль | Действие |
|------|----------|
| **Product** | Юридические тексты страниц, UX согласия, контакты DPO/поддержки |
| **DEV** | TTL job, публичный signup API, опционально DELETE intent |
| **SEC** | Утечки в логах, доступ к PII в админке Основателя |
| **LEAD** | Приёмка перед «платный лендинг»; статусы ☑ выше — **инженерная** готовность 2026-04-06 |

---

**Версия:** 2026-04-07
