# DEV_PROMPTS_AUTH_OAUTH

## Роль и границы задачи

**Роль:** @DEV  
**Контекст:** реализовать OAuth‑авторизацию пациентов через VK и Яндекс согласно `ARCH_AUTH_OAUTH.md`, не ломая текущий SMS‑флоу и модель с JWT.

- Не трогаем админскую авторизацию — только **пациентский** вход.
- SMS‑авторизация остаётся и продолжает работать.
- Все новые entry‑points в итоге выдают тот же `AuthTokenResponse`, что и `/auth/verify-code`.

---

## Цели реализации

1. Добавить к `Patient` поддержку идентификаторов VK и Яндекс.
2. Реализовать полноценные OAuth‑потоки VK и Яндекс на бэкенде (start + callback).
3. Корректно обрабатывать `state` через Redis (CSRF + редирект).
4. Научить фронтенд принимать результат OAuth‑логина (успех/отмена/ошибка) и устанавливать сессию пациента.
5. Сохранить совместимость с текущим API и тестами.

---

## Изменения в модели данных

### 1. Поля в `Patient`

Файл: `src/domain/entities/patient.py`

Добавить поля:

- `vk_id: Mapped[str | None] = mapped_column(String(255), nullable=True)`  
- `yandex_id: Mapped[str | None] = mapped_column(String(255), nullable=True)`

(опционально, но полезно оставить задел):

- `vk_screen_name: Mapped[str | None] = mapped_column(String(255), nullable=True)`
- `yandex_login: Mapped[str | None] = mapped_column(String(255), nullable=True)`

Требования:

- Индексы для быстрых поисков:
  - `idx_patients_vk_id` по `vk_id`
  - `idx_patients_yandex_id` по `yandex_id`
- В рамках одной клиники запрещаем дубли:
  - `UniqueConstraint("clinic_id", "vk_id", name="ux_patients_clinic_vk_id")`
  - `UniqueConstraint("clinic_id", "yandex_id", name="ux_patients_clinic_yandex_id")`

Учитывай существующий паттерн с `deleted_at`: дубликат по `clinic_id+vk_id`/`yandex_id` должен быть невозможен среди **неудалённых** записей.

### 2. Alembic‑миграция

Создать миграцию, например: `alembic/versions/add_patient_oauth_ids.py`.

В `upgrade()`:

- добавить нужные колонки к таблице `patients`;
- создать индексы;
- создать `UniqueConstraint` по `(clinic_id, vk_id)` и `(clinic_id, yandex_id)`.

В `downgrade()`:

- удалить констрейнты, индексы и колонки.

---

## Redis‑state для OAuth

Нужен единый способ хранения `state`:

- для VK: ключ `auth:vk:state:{state}`
- для Яндекс: `auth:yandex:state:{state}`

Содержимое — JSON/строка:

```json
{ "redirect": "/app" }
```

Требования:

- TTL: ~10 минут.
- Одноразовость: после успешного чтения `state` нужно удалить.
- Если `state` не найден — считаем, что флоу недействителен (защита от CSRF и повторного использования ссылки).

Для доступа к Redis используй существующий код (`get_redis` и т.п.), см. `AuthService` и другие места.

---

## VK OAuth: реализация

Эндпоинты уже созданы в `src/api/v1/routers/auth.py`. Нужно **заполнить их тело**.

### 1. `/auth/oauth/vk/start`

Сейчас там есть базовый редирект без state. Нужно:

1. Сгенерировать `state` (например, `secrets.token_urlsafe(32)`).
2. Сохранить в Redis:
   - ключ: `auth:vk:state:{state}`;
   - значение: JSON с полем `redirect`:
     - если query‑параметр `redirect` задан и безопасен (относительный путь, без протокола/домена) — использовать его;
     - иначе `"/app"`;
   - TTL: 600 секунд.
3. Собрать URL:
   - `https://oauth.vk.com/authorize`
   - параметры:
     - `client_id=settings.vk_client_id`
     - `redirect_uri=settings.vk_redirect_uri`
     - `response_type=code`
     - `scope=email`
     - `state={state}`
4. Вернуть `RedirectResponse(url=..., status_code=302)`.

Если VK‑настройки не заданы (`vk_client_id` или `vk_redirect_uri` пустые) — вернуть 503 с текстом `"VK OAuth is not configured"`.

### 2. `/auth/oauth/vk/callback`

Шаги:

1. Если пришёл query‑параметр `error` — считать, что пользователь отменил вход:
   - попытаться вычитать `redirect` из Redis по `state` (если возможно);
   - выдать 302 на `{redirect}?oauth=vk&status=cancelled`.
2. Проверить `state`:
   - прочитать `auth:vk:state:{state}` из Redis;
   - если нет значения → 302 на `/app/login?oauth=vk&status=state_invalid`;
   - если есть — распарсить JSON, получить `redirect` (если нет — `"/app"`), удалить ключ из Redis.
3. Обменять `code` на токен VK через `https://oauth.vk.com/access_token` с параметрами:
   - `client_id=settings.vk_client_id`
   - `client_secret=settings.vk_client_secret`
   - `redirect_uri=settings.vk_redirect_uri`
   - `code=code`
   Использовать `httpx.AsyncClient`, аккуратно обрабатывать сетевые ошибки и статусы != 200. В случае ошибки — лог + редирект `redirect?oauth=vk&status=provider_error`.
4. Из ответа взять:
   - `user_id` (основной ID);
   - `email` (может отсутствовать);
   - `access_token` (на будущее).
5. Собрать профиль:

```python
vk_profile = {
    "user_id": str(user_id),
    "email": email or None,
}
```

6. Передать профиль в доменный сервис (см. раздел **OAuthAuthService**) для поиска/создания `Patient` по `(clinic_id, vk_id=user_id)` и выдачи JWT.
7. Вернуть результат через 302‑редирект:

```text
redirect?oauth=vk&status=ok&token={jwt}&patient_id={patient.id}
```

где `redirect` взят из значения Redis под `state`.

---

## Yandex OAuth: реализация

Поток полностью аналогичен VK, но с Яндекс‑эндпоинтами.

### 1. `/auth/oauth/yandex/start`

Шаги те же, что и для VK, но:

- URL: `https://oauth.yandex.ru/authorize`
- параметры:
  - `client_id=settings.yandex_client_id`
  - `redirect_uri=settings.yandex_redirect_uri`
  - `response_type=code`
  - `scope=login:email login:info`
  - `state={state}`
- Redis‑ключ: `auth:yandex:state:{state}`.

### 2. `/auth/oauth/yandex/callback`

Шаги:

1. Обработать `error` (аналогично VK, статус `cancelled`).
2. Проверить и считать `state` (`auth:yandex:state:{state}`) и удалить ключ.
3. Обменять `code` на `access_token` через `https://oauth.yandex.ru/token` c параметрами:
   - `client_id=settings.yandex_client_id`
   - `client_secret=settings.yandex_client_secret`
   - `code`
   - `grant_type=authorization_code`
4. Получить профиль пользователя через `https://login.yandex.ru/info` с заголовком `Authorization: OAuth {access_token}`.
5. Из профиля взять:
   - стабильный `id` → `yandex_id`;
   - `default_email` или `emails` (опционально);
   - логин.
6. Собрать профиль:

```python
yandex_profile = {
    "id": str(user_id),
    "email": email_or_none,
    "login": login_or_none,
}
```

7. Через доменный сервис создать/найти `Patient` по `(clinic_id, yandex_id)` и выдать JWT.
8. Вернуть редирект `redirect?oauth=yandex&status=ok&token=...&patient_id=...`.

---

## Сервисный слой: OAuthAuthService (рекомендация)

Чтобы не дублировать логику `AuthService.verify_code`, введи отдельный сервис.

Файл: `src/application/services/oauth_auth_service.py` (или расширь `AuthService`).

Интерфейс:

```python
class OAuthAuthService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def authenticate_vk(self, profile: dict[str, Any]) -> tuple[str, UUID]:
        ...

    async def authenticate_yandex(self, profile: dict[str, Any]) -> tuple[str, UUID]:
        ...
```

Функции внутри:

- получают `clinic = await _get_default_clinic()` (вынести в helper по аналогии с `AuthService._get_default_clinic`);
- ищут/создают `Patient` по правилам из `ARCH_AUTH_OAUTH.md`:
  - сначала поиск по `(clinic_id, vk_id)` / `(clinic_id, yandex_id)`;
  - если не найден — создание нового `Patient` с заполненными полями `vk_id`/`yandex_id`;
- вызывают `create_access_token` так же, как в `AuthService.verify_code` (`role="patient"`, нужный TTL);
- возвращают `(token, patient.id)`.

`auth.py` при этом остаётся тонким слоем: HTTP‑обмен с VK/Яндекс + вызов `OAuthAuthService` + редирект.

---

## Фронтенд: обработка результата OAuth

На стороне фронта уже есть кнопки на `LoginPage`:

- `/api/v1/auth/oauth/vk/start?redirect=/app`
+- `/api/v1/auth/oauth/yandex/start?redirect=/app`

Нужно добавить простую страницу/эффект, который:

1. Читает из URL параметры:
   - `oauth` (`vk`/`yandex`)
   - `status` (`ok`/`cancelled`/`error`/`state_invalid`/`provider_error`)
   - `token`
   - `patient_id`
2. Если `status=ok` и есть `token` + `patient_id`:
   - вызывает `login(token, patient_id)` из `PatientAuthContext`;
   - переводит на нужную страницу (`/app` или другую в зависимости от URL).
3. Если `status=cancelled`:
   - возвращается/остаётся на `/login` без ошибок.
4. Если `status=error` или `state_invalid`/`provider_error`:
   - показывает аккуратное сообщение: «Не удалось войти через VK/Яндекс. Попробуйте ещё раз или используйте вход по SMS.».

---

## Тестирование

Обязательные проверки:

- **Бэкенд (unit/integration):**
  - успешный VK‑флоу (мокаем httpx к VK, Redis, проверяем создание `Patient`, генерацию JWT и корректный редирект);
  - успешный Yandex‑флоу;
  - невалидный/просроченный `state`;
  - ошибки от провайдера (`access_token`/`userinfo` вернули ошибку);
  - сценарий с уже существующим `Patient` с тем же `vk_id`/`yandex_id`.
- **E2E/ручные:**
  - вход через VK/Яндекс при настроенных `.env` с OAuth‑кредами;
  - поведение при выключенном OAuth (нет client_id/secret): кнопки могут оставаться, но бэкенд возвращает 503 и фронт показывает, что метод временно недоступен.

---

## Итоговый промпт для @DEV

> Открой `docs/ARCH_AUTH_OAUTH.md` и этот `DEV_PROMPTS_AUTH_OAUTH.md`.  
> Реализуй поддержку OAuth‑авторизации пациентов через VK и Яндекс:
> - добавь поля `vk_id`, `yandex_id` (и при необходимости `vk_screen_name`, `yandex_login`) в `Patient` и создай alembic‑миграцию с индексами и уникальными ограничениями по `(clinic_id, vk_id)` и `(clinic_id, yandex_id)`;
> - реализуй хранение и проверку `state` в Redis для VK и Яндекс согласно схемам (`auth:vk:state:{state}`, `auth:yandex:state:{state}`, TTL 10 минут, одноразовость);
> - допиши код в `auth.py` для эндпоинтов `/auth/oauth/vk/start`, `/auth/oauth/vk/callback`, `/auth/oauth/yandex/start`, `/auth/oauth/yandex/callback`:
>   - стартовые эндпоинты должны генерировать `state`, писать его в Redis и делать 302‑редирект к провайдеру;
>   - callback‑эндпоинты — обрабатывать `error`, валидировать `state`, обменивать `code→token`, получать профиль пользователя, искать/создавать `Patient` и выдавать пациентский JWT, завершаясь редиректами вида `redirect?oauth={vk|yandex}&status={ok|cancelled|error}&token=...&patient_id=...`;
> - при необходимости вынеси работу с профилем и созданием токена в отдельный сервис (`OAuthAuthService`), чтобы не дублировать логику `AuthService.verify_code`;
> - доработай фронтенд так, чтобы:
>   - кнопки входа через VK/Яндекс, уже добавленные на `LoginPage`, корректно отрабатывали редирект;
>   - конечная страница читала параметры `oauth`, `status`, `token`, `patient_id`, вызывала `login(token, patient_id)` при успехе и показывала аккуратные сообщения при ошибке/отмене.

