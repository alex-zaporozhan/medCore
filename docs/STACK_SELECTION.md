# 📦 STACK_SELECTION — Выбор стека по задаче

> Источник решений для @ARCH и @CREATOR. @ARCH читает этот файл перед фиксацией стека.

---

## РЕЖИМЫ И СТЕК

| Режим | Заказчик | Backend | Frontend | БД |
|-------|---------|---------|----------|-----|
| **SCRIPT** | Соло / микропроект | Python | HTML + минимум JS | SQLite |
| **SAAS** | Стартап / малый бизнес РФ | Python (FastAPI) или Node (NestJS) | TypeScript + React/Vue | PostgreSQL |
| **ENTERPRISE** | Корпорация, банк, госсектор | Java 21 + Spring Boot | TypeScript + React/Angular | PostgreSQL / Oracle |
| **HIGHLOAD** | Трафик, реальное время | Go / Java по профилю | TypeScript + фреймворк | PostgreSQL + Kafka/Redis |

**Правило:** TypeScript обязателен для фронтенда в продакшене. Голый JS — только для простых лендингов.

---

## ВЫБОР BACKEND (когда что)

**Java** — крупная компания, банк, госсектор, аудит, долгосрочная поддержка, корпоративные интеграции (LDAP, Oracle, IBM MQ). Стек: Java 21 LTS + Spring Boot 3.x + Maven/Gradle.

**Python** — скрипты, MVP, быстрый старт, малый бизнес РФ, ЮKassa, Telegram-боты, аналитика. Стек: FastAPI + SQLAlchemy 2.0 + Alembic + PostgreSQL + Redis + Celery.

**Go** — высоконагруженные сервисы, микросервисы, CLI, минимальная память и быстрый старт (контейнеры).

**Node.js** — единый язык с фронтом (TypeScript), реальное время (WebSocket), быстрый MVP API. Не выбирать как основной backend для enterprise без явного запроса заказчика.

---

## ОБЯЗАТЕЛЬНЫЙ БЛОК @ARCH (начало любого архитектурного документа)

```
Режим:    [SCRIPT / SAAS / ENTERPRISE / HIGHLOAD]
Backend:  [язык + фреймворк]
Frontend: [TypeScript + фреймворк]
БД:       [тип + версия + очереди если нужны]
Почему:   [одна фраза]
```

Без этого блока выбор стека не считается зафиксированным.

---

## 🔒 CRYSTAL: Docker Compose — секреты через ENV

**Проблема:** хардкод паролей в `docker-compose.yml` — секреты попадают в git.

**Решение:** подстановка из `.env` файла. Compose загружает `.env` из директории с compose-файлом автоматически.

```yaml
# docker-compose.yml — правильно
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_DB: ${POSTGRES_DB}

  app:
    build: .
    env_file:
      - .env          # ← все переменные приложения из .env
    depends_on:
      - db
```

```env
# .env (в .gitignore!)
POSTGRES_PASSWORD=supersecret
POSTGRES_USER=myapp
POSTGRES_DB=mydb
```

```env
# .env.example (в git — без реальных значений)
POSTGRES_PASSWORD=
POSTGRES_USER=
POSTGRES_DB=
```

**Правило @ARCH:** при проектировании docker-compose — всегда `env_file: - .env` для сервисов приложения, `${VAR}` для БД. Никаких хардкодов паролей в yaml.

---

## ФАКТИЧЕСКИЙ СТЕК ПРОЕКТА DENTAL BOOKING

```text
Режим:    SAAS
Backend:  Python 3.11 + FastAPI + SQLAlchemy 2 (async) + Alembic
Frontend: TypeScript + React 18 + Mantine + React Router + React Query + Vite + PWA
БД:       PostgreSQL 15+ (основная), Redis (кеш, rate limiting, Celery broker/result), Celery (фоновая обработка)
Почему:   Быстрый запуск SAAS‑продукта для клиник с богатыми интеграциями (YooKassa, мессенджеры, AI) и удобной PWA/админкой.
```

**Интеграции, заложенные в стек проекта:**

- Платежи: YooKassa (предоплата/оплата по записям, webhook‑обновление статусов).
- Коммуникации: Telegram, WhatsApp Business, VK, Instagram Direct, email, web‑чат (через единый интеграционный шлюз).
- Уведомления: SMS (SMSC.ru‑совместимый провайдер) + Email + Telegram.
- AI: внешний чат‑провайдер (HTTP API) для ассистента и аналитики диалогов.

**Правило:** при изменении стека (добавление брокеров, смена СУБД, отказ от Celery/Redis и т.п.) @ARCH обязан обновить этот блок и соответствующие TECH_PASSPORT файлы:

- `docs/TECH_PASSPORT_BACKEND.md`
- `docs/TECH_PASSPORT_FRONTEND.md`
- `docs/TECH_PASSPORT_PROJECT.md`

---

Reference: docs/ROLE_ARCH.md · docs/ROLE_CREATOR.md
