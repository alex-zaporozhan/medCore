## Пошаговая инструкция деплоя (GitHub → Docker Hub → VPS)

Этот сценарий описывает **текущий рабочий процесс** деплоя лендинга `goodcode-app.ru`.

- Репозиторий: `alex-zaporozhan/web-landing`
- Docker Hub: `moircreator/web-landing-backend:latest`, `moircreator/web-landing-frontend:latest`
- VPS: `/home/app`, запуск через `docker-compose.yml`
- nginx на VPS проксирует домен `goodcode-app.ru` на `http://127.0.0.1:3004`

---

### 1. Локальная работа с кодом

1. Вносишь изменения во фронт/бекенд.
2. Локально при необходимости:
   - фронт: `npm run dev` в `frontend` (порт 5173 или свой);
   - бекенд: `uvicorn app.main:app --reload` в `backend` (порт 8000).
3. Проверяешь, что всё работает.

---

### 2. Коммит и push в GitHub

В корне проекта (`d:\CURSOR\projects\web`):

```bash
git status          # убедиться, что изменено то, что нужно
git add .
git commit -m "Короткое описание изменений"
git push origin main
```

Это автоматически запустит GitHub Actions workflow:

- файл: `.github/workflows/docker-images.yml`
- имя job: **Build and push Docker images**

---

### 3. Проверка GitHub Actions

1. Открываешь репозиторий на GitHub.
2. Вкладка **Actions** → выбираешь последний запуск `Add Docker build & push workflow` (или другое имя, но с описанием «Build and push Docker images»).
3. Убеждаешься, что job `build-and-push` зелёная (**succeeded**):
   - шаг `Build and push backend image` — успешен;
   - шаг `Build and push frontend image` — успешен.

После успеха в Docker Hub оказываются:

- `moircreator/web-landing-backend:latest`
- `moircreator/web-landing-frontend:latest`

---

### 4. Подготовка VPS (делается один раз)

На VPS (Beget), под `root`:

```bash
cd /home/app
git clone https://github.com/alex-zaporozhan/web-landing.git .   # уже сделано

docker login -u moircreator
```

- Ввести токен/пароль Docker Hub.
- После `Login Succeeded` авторизация сохранится в `/root/.docker/config.json`.

nginx уже настроен так, что:

- HTTP → HTTPS редирект;
- HTTPS `goodcode-app.ru` → `proxy_pass http://127.0.0.1:3004;`.

---

### 5. Деплой новой версии на VPS (каждый раз)

Каждый раз, когда готова новая версия:

```bash
ssh root@IP_СЕРВЕРА

cd /home/app
git pull origin main          # подтянуть последние изменения репо

docker compose pull           # стянуть последние образы из Docker Hub
docker compose up -d          # пересоздать контейнеры в фоне
```

Пояснения:

- `docker compose pull` возьмёт:
  - `moircreator/web-landing-backend:latest`
  - `moircreator/web-landing-frontend:latest`
  - `postgres:16-alpine` (если образа ещё нет локально).
- `docker compose up -d`:
  - поднимет `app-backend-1`, `app-frontend-1`, `app-db-1` с новыми образами;
  - сохранит порты и окружение из `docker-compose.yml`.

---

### 6. Проверка после деплоя

1. Контейнеры:

```bash
docker ps
```

Ожидаешь:

- `app-backend-1` — `0.0.0.0:8004->8000/tcp`
- `app-frontend-1` — `0.0.0.0:3004->80/tcp` (и опционально `3001->80`)
- `app-db-1` — `5432/tcp` (без внешнего порта).

2. Локальные проверки на VPS:

```bash
curl -I http://127.0.0.1:3004
curl -I http://127.0.0.1:8004/health   # если есть endpoint здоровья бекенда
```

3. Проверка домена снаружи:

- открыть `https://goodcode-app.ru` в браузере (лучше в инкогнито);
- убедиться, что фронт — новый.

---

### 7. Быстрый чек‑лист, если что‑то пошло не так

1. **На GitHub**:
   - Actions → последний запуск;
   - если красный — смотреть лог шагов сборки образов.
2. **На VPS**:
   - `git status` в `/home/app` — убедиться, что нет локальных незакоммиченных правок.
   - `docker compose pull` — нет ли ошибок доступа к Docker Hub.
   - `docker compose up -d` — нет ли ошибок запуска (например, порт занят).
   - `docker logs app-backend-1` / `docker logs app-frontend-1` — что пишет контейнер.
3. **nginx**:
   - `sudo nginx -t` — конфиг валиден?
   - `sudo systemctl status nginx` — nginx запущен?

---

### 8. Команды, которые НЕ использовать в проде без особой причины

- `docker compose build` / `docker build` на VPS — сборка должна происходить на GitHub Actions.
- Ручное изменение образов через `docker commit`.
- Изменение `docker-compose.yml` прямо на VPS (всегда править в Git и деплоить через `git pull`).

