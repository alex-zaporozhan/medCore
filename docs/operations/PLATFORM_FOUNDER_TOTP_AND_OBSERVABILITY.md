# Основатель платформы: TOTP (практика) и стек наблюдаемости (Prometheus / Grafana)

> **Цель:** один «как сделать руками» документ для @LEAD / OPS без кода P0 (singleton, отдельная страница безопасности и т.д.).  
> **Связь:** [FOUNDER_ACCESS_BREAKGLASS.md](./FOUNDER_ACCESS_BREAKGLASS.md), [OBSERVABILITY_COMPOSE_SMOKE.md](./OBSERVABILITY_COMPOSE_SMOKE.md), [deploy/grafana/README.md](../../deploy/grafana/README.md).

---

## 1. TOTP для Основателя — де-факто как включить

### 1.1 Что это

- **TOTP** (Google Authenticator, Aegis и т.п.) — **второй фактор** после пароля. Это не замена пароля и не «токен в `.env`».
- В `.env` для подписи JWT сервером задаётся **`PLATFORM_FOUNDER_JWT_SECRET`** (production); к TOTP пользователя не относится.

### 1.2 Предусловия

1. Учётка Основателя в БД (`platform_founder_users`), созданная офлайн:  
   `poetry run python -m src.scripts.create_platform_founder_user --email ... --password ...`  
   (см. `.env.example` и шапку скрипта `src/scripts/create_platform_founder_user.py`).
2. Вход в продукт: **`/platform/login`** (JWT основателя хранится отдельно от админки клиники).

### 1.3 Вариант A — через UI (рекомендуется)

1. Войти на **`/platform/login`** (email + пароль). Пока **TOTP не включён**, редирект в кабинет без шага MFA.
2. Открыть **`/platform/dashboard`**.
3. В блоке **«Состояние сессии»** нажать **«Привязать TOTP / Google Authenticator»**.
4. **«Сгенерировать секрет для приложения»** — появится строка **`otpauth://...`** (и подписи issuer / email).
5. В приложении-аутентификаторе: **добавить аккаунт** → ввести ключ вручную по `otpauth://` (или QR, если клиент умеет открыть ссылку).
6. Ввести **текущий 6-значный код** и **«Подтвердить и включить 2FA»**.

После успеха следующие входы: **`/platform/login`** → при необходимости отдельный шаг **`/platform/login/mfa`** с кодом из приложения.

### 1.4 Вариант B — через API (curl / Postman)

Нужен **Bearer** access-токена основателя после `POST /api/v1/platform/auth/login`.

```http
POST /api/v1/platform/auth/totp/enroll
Authorization: Bearer <access_token>
Content-Type: application/json
```

Ответ: `otpauth_uri`, `issuer`, `account_email` — добавить в приложение, затем:

```http
POST /api/v1/platform/auth/totp/confirm
Authorization: Bearer <тот_же_access_token>
Content-Type: application/json

{"code": "123456"}
```

Если TOTP уже включён, **enroll** вернёт **409** (`platform_founder_totp_already_enabled`).

### 1.5 Политика «нельзя в internal без TOTP» (опционально)

В настройках приложения: **`PLATFORM_FOUNDER_TOTP_REQUIRED=true`** — тогда доступ к маршрутам **`/platform/internal/*`** без пройденного enroll/confirm может быть заблокирован (см. описание в `src/core/config.py` и ответы **403** в `platform_internal`). Логин и **`/platform/auth/totp/*`** остаются для первичного bootstrap.

### 1.6 Потеря телефона / сброс TOTP

См. [FOUNDER_ACCESS_BREAKGLASS.md](./FOUNDER_ACCESS_BREAKGLASS.md) §3.

---

## 2. Prometheus и Grafana — где «живут» и как поднять локально

### 2.1 Важно

- **Дашборды Grafana не встроены в приложение** (`/platform/...` — это продуктовый кабинет Основателя, не Grafana).
- Prometheus/Grafana поднимаются **отдельным профилем** Docker Compose и по умолчанию слушают **только localhost** (см. [SAAS_STRENGTHENING_MASTER_PLAN.md](../architecture/SAAS_STRENGTHENING_MASTER_PLAN.md) §11 M5).

### 2.2 Поднять стек

Из корня репозитория (предусловия и порядок — см. [OBSERVABILITY_COMPOSE_SMOKE.md](./OBSERVABILITY_COMPOSE_SMOKE.md)):

```bash
docker compose up -d db redis migrations backend
docker compose --profile observability up -d
```

| Сервис | URL (локально) |
|--------|----------------|
| Prometheus | http://127.0.0.1:9090 |
| Alertmanager | http://127.0.0.1:9093 |
| Grafana | http://127.0.0.1:3001 |
| Echo (цепочка алертов, smoke) | http://127.0.0.1:8888 |

Пароль администратора Grafana: **`GRAFANA_ADMIN_PASSWORD`** в `.env` или значение по умолчанию из `docker-compose.yml`.

### 2.3 Проверка, что метрики доходят

1. Prometheus → **Status → Targets**: цель **`backend`** (scrape **`/metrics`**) должна быть **UP**.
2. В **Graph** выполнить, например: `up{job="backend"}`.

### 2.4 Дашборды Grafana (как файлы в репозитории)

- JSON: **`deploy/grafana/dashboards/`** (описание назначения панелей — [deploy/grafana/README.md](../../deploy/grafana/README.md)).
- Импорт в UI: **Dashboards → Import** → выбрать JSON; datasource **Prometheus** привязать к вашему источнику (в шаблонах используется **`__inputs`** — см. README).
- Для контура **SaaS / platform** в наблюдаемости есть ряды по метрикам вроде **`platform_signup_intent_stuck`**, **`platform_signup_intent_dead_letter`** (см. тот же README и дашборд `dental_booking_observability_w1_w2.json`).

### 2.5 Алерты

- Правила: **`deploy/prometheus/dental_booking_alerts.yml`**
- Конфиг Alertmanager: **`deploy/alertmanager/alertmanager.yml`** (пример Telegram — `*.telegram.example.yml`, токены не коммитить).

### 2.6 Staging / production

- Вынести Grafana за **VPN / BasicAuth** (чеклисты: [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md), [OBSERVABILITY_COMPOSE_SMOKE.md](./OBSERVABILITY_COMPOSE_SMOKE.md) §чеклист OPS).
- Автоматические проверки в CI: см. `tests/deploy/test_prometheus_alert_rules_yaml.py`, `tests/core/test_grafana_dashboard_json.py` (указаны в OBSERVABILITY_COMPOSE_SMOKE).

---

## 3. Что не смешивать

| Тема | Где смотреть |
|------|----------------|
| Очередь signup / провижининг в **продукте** | UI Основателя: **`/platform/provision-queue`** (данные API `platform/internal`, не Grafana). |
| Картинка по метрикам / алертам | **Prometheus + Grafana** (compose-профиль), не страница приложения. |
| Break-glass TOTP | [FOUNDER_ACCESS_BREAKGLASS.md](./FOUNDER_ACCESS_BREAKGLASS.md) |

---

**Версия:** 2026-04-07 (LEAD)
