# Деплой: GitHub → CI → Registry → VPS

Пошаговый сценарий: **код в репозитории** → **сборка образов в CI** → **образы в registry** → **на VPS** `git pull` + `docker compose pull/up`.

Ниже — **общий процесс**. Конкретные имена репозитория, образов и домена подставляются из вашего проекта (в этом документе дан **пример** лендинга `goodcode-app.ru`; для репозитория `dental_booking` см. комментарии в `docker-compose.yml` и `docs/DOCKER_INFRA_PASSPORT.md`).

---

## Содержание

1. [Схема и роли веток](#1-схема-и-роли-веток)
2. [Параметры окружения (заполнить под проект)](#2-параметры-окружения-заполнить-под-проект)
3. [Локальная разработка](#3-локальная-разработка)
4. [Публикация кода: коммит и merge в `main` через PR](#4-публикация-кода-коммит-и-merge-в-main-через-pr)
5. [CI: сборка и push образов](#5-ci-сборка-и-push-образов)
6. [Подготовка VPS (один раз)](#6-подготовка-vps-один-раз)
7. [Деплой новой версии на VPS (каждый раз)](#7-деплой-новой-версии-на-vps-каждый-раз)
8. [Проверка после деплоя](#8-проверка-после-деплоя)
9. [Если что-то пошло не так](#9-если-что-то-пошло-не-так)
10. [Чего не делать в проде без причины](#10-чего-не-делать-в-проде-без-причины)

---

## 1. Схема и роли веток

```text
[локально] feature-ветка → git push origin feature/…
      ↓
[GitHub] Pull Request: base = main ← compare = feature/…
      ↓
[GitHub] Merge PR (после ревью и зелёных проверок CI)
      ↓
[GitHub] main обновлён → при наличии workflow: build → push образов в Docker Hub / GHCR
      ↓
[VPS]    git pull origin main → docker compose pull → docker compose up -d
```

Важно:

- **Прямой `git push origin main` с ноутбука** часто **запрещён политикой** репозитория — это норма. В `main` попадают изменения через **merge PR**, а не через обход правил.
- Команда **`git push -u origin feature/имя-ветки`** отправляет на сервер **только feature-ветку**. Этого достаточно, чтобы открыть PR и влить код в `main` на GitHub.
- После merge в `main` на VPS выполняется **`git pull origin main`** — на сервере должна быть **чистая** копия репозитория без ручных правок в tracked-файлах.

---

## 2. Параметры окружения (заполнить под проект)

| Параметр | Пример (web-landing) | Где смотреть в `dental_booking` |
|----------|----------------------|--------------------------------|
| Репозиторий GitHub | `alex-zaporozhan/web-landing` | `git remote -v` |
| Ветка продакшена | `main` | обычно `main` |
| Образы приложения | `moircreator/web-landing-backend:latest`, `…-frontend:latest` | переменные `BACKEND_IMAGE` / `FRONTEND_IMAGE` в `.env`, см. шапку `docker-compose.yml` |
| Каталог на VPS | `/home/app` | выбрать один путь и не менять без причины |
| Домен и nginx | `goodcode-app.ru` → `127.0.0.1:3004` | свой домен и порт фронта в compose |
| Workflow CI | `.github/workflows/docker-images.yml` | фактическое имя файла в `.github/workflows/` |

---

## 3. Локальная разработка

### Универсально

1. Внести изменения во фронтенд и/или бэкенд.
2. Прогнать линтеры/тесты так, как принято в репозитории (pre-commit, `pytest`, `npm run lint` и т.д.).
3. Убедиться, что приложение поднимается локально.

### Пример путей для репозитория `dental_booking`

В корне репозитория (например `d:\CURSOR\projects\dental_booking`):

- **Фронтенд:** каталог `frontend` — `npm install` (первый раз), затем `npm run dev` (Vite, порт по умолчанию 5173).
- **Бэкенд:** из корня — `poetry run uvicorn src.main:app --reload` (порт задаётся в команде или конфиге; часто 8000).

Для **другого** проекта (как в исходном примере web-landing) структура могла быть `frontend` / `backend` с `uvicorn app.main:app` — ориентируйтесь на README репозитория.

---

## 4. Публикация кода: коммит и merge в `main` через PR

### 4.1. Не путать ветки и команды push

| Команда | Что делает |
|---------|------------|
| `git push origin feature/моя-ветка` | Отправляет **текущую feature-ветку** на GitHub — **это нужно для PR**. |
| `git push origin main` | Пытается отправить **локальную ветку `main`** на сервер. На feature-ветке вы **всё ещё не на `main`**, а эта команда не публикует feature-ветку под именем `main` без дополнительных шагов. Плюс политика может **блокировать** push в `main`. |

Правильный путь кода в `main` на GitHub:

1. Находиться на feature-ветке (или создать её от актуального `main`):

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/кратко-что-делаете
   ```

2. Закоммитить изменения:

   ```bash
   git status
   git add -A
   git commit -m "Коротко: что изменилось"
   ```

3. Отправить **feature-ветку**:

   ```bash
   git push -u origin feature/кратко-что-делаете
   ```

4. На GitHub: **Pull requests → New pull request**  
   - **base:** `main`  
   - **compare:** ваша `feature/…`  
   - Создать PR, пройти ревью, дождаться **успешного CI** (если настроен).

5. Нажать **Merge pull request** (или Squash merge — по правилам команды).

6. Локально обновить `main`:

   ```bash
   git checkout main
   git pull origin main
   ```

После этого в удалённом `main` лежит то же, что вы влили PR’ом; дальше обычно **срабатывает** workflow сборки Docker-образов (если триггер на push в `main`).

### 4.2. Если `git commit` пишет «nothing to commit»

Значит, для Git **нет отличий** от последнего коммита: либо изменения уже закоммичены, либо файлы не попали в индекс, либо совпадают с HEAD. Проверка: `git status`, `git diff`.

---

## 5. CI: сборка и push образов

После того как изменения оказались в **`main`** на GitHub (через merge PR), должен выполниться workflow (часто при push в `main`).

1. Открыть репозиторий на GitHub → **Actions**.
2. Найти workflow вроде **Build and push Docker images** (точное имя смотрите в `.github/workflows/*.yml`).
3. Убедиться, что последний запуск **succeeded**: шаги сборки и пуша **backend** и **frontend** образов прошли без ошибок.

В примере web-landing в registry попадают, например:

- `moircreator/web-landing-backend:latest`
- `moircreator/web-landing-frontend:latest`

Для `dental_booking` имена могут быть **GHCR** или другой registry — смотрите workflow и `docker-compose.yml`.

---

## 6. Подготовка VPS (один раз)

На сервере (пример: пользователь `root`, каталог приложения `/home/app`).

```bash
cd /home/app
git clone https://github.com/alex-zaporozhan/web-landing.git .
# для другого репозитория — подставить свой URL; если каталог не пустой, clone делают один раз заранее
```

Авторизация в Docker Hub (или другом registry), откуда `docker compose` тянет образы:

```bash
docker login -u ВАШ_ЛОГИН
```

После успешного входа учётные данные сохраняются (часто `/root/.docker/config.json`).

**nginx** (если используется) настраивается один раз, например:

- HTTP → HTTPS;
- для домена `goodcode-app.ru` — `proxy_pass` на порт фронтенда контейнера (в примере `http://127.0.0.1:3004`).

Конкретные порты и имена контейнеров должны совпадать с вашим `docker-compose.yml` в репозитории.

---

## 7. Деплой новой версии на VPS (каждый раз)

Когда в `main` уже влит нужный код и в CI успешно собраны и запушены образы:

```bash
ssh root@IP_СЕРВЕРА

cd /home/app
git pull origin main

docker compose pull
docker compose up -d
```

Смысл:

- **`git pull origin main`** — обновить на сервере **только** compose-файлы и конфиги из репозитория (без ручного редактирования на VPS).
- **`docker compose pull`** — скачать свежие теги образов (`:latest` или зафиксированные в `.env`).
- **`docker compose up -d`** — пересоздать контейнеры в фоне с новыми образами.

В примере web-landing `pull` подтянет образы приложения и при необходимости базу (`postgres:16-alpine` и т.д.). Имена сервисов и тома — из вашего `docker-compose.yml`.

---

## 8. Проверка после деплоя

### Контейнеры

```bash
docker ps
```

Ожидаемо (имена из примера web-landing; у вас могут быть `dental_booking_*` и др.):

- контейнер бэкенда с пробросом порта на хост (например `8004->8000`);
- контейнер фронта (например `3004->80`);
- при необходимости — БД без публикации порта наружу.

### HTTP с самого VPS

```bash
curl -I http://127.0.0.1:3004
curl -I http://127.0.0.1:8004/health
```

Второй URL — если в приложении есть маршрут здоровья; путь уточните по коду (`/health`, `/api/v1/...`).

### Снаружи

- Открыть сайт по HTTPS в браузере (лучше инкогнито), проверить актуальность версии UI.

---

## 9. Если что-то пошло не так

| Где | Что проверить |
|-----|----------------|
| **GitHub Actions** | Последний запуск workflow — красный шаг: лог сборки образа, ошибки push в registry. |
| **VPS: Git** | `git status` в каталоге приложения — нет ли незакоммиченных правок; при необходимости сохранить `.env` и не затирать секреты при `git pull`. |
| **VPS: Docker** | `docker compose pull` — ошибки логина в registry или отсутствующий тег. |
| **VPS: контейнеры** | `docker compose up -d` — конфликт портов, нехватка места. |
| **Логи** | `docker logs <имя_контейнера>` для backend/frontend. |
| **nginx** | `sudo nginx -t`, `sudo systemctl status nginx`. |

---

## 10. Чего не делать в проде без причины

- Собирать образы на VPS (`docker compose build`, `docker build`) — если принято, что **единственная** сборка в CI.
- Менять образы через `docker commit`.
- Править `docker-compose.yml` только на сервере: изменения вносить **в Git**, коммитить, мержить в `main`, затем `git pull` на VPS.
- Пушить напрямую в `main` в обход политики репозитория — лучше PR и merge после CI.

---

## Краткий чек-лист «от коммита до продакшена»

1. Feature-ветка → commit → `git push origin feature/…`.
2. PR в `main` → merge после зелёного CI.
3. Actions: образы в registry — успех.
4. VPS: `git pull origin main` → `docker compose pull` → `docker compose up -d`.
5. Проверка: `docker ps`, `curl`, браузер.
