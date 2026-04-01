# DEV_PROMPTS: Кассы — хранение credentials на бэкенде

> Задача для @DEV: реализовать на бэкенде и в API хранение credentials платёжных касс для одной активной кассы на клинику, по архитектуре из `ARCH_PAYMENT_GATEWAYS.md` (раздел 5). На этом этапе реализуем только **хранение** (запись/чтение), без интеграции новых провайдеров в процесс оплаты (создание платежа по‑прежнему только через ЮKassa).

---

## 1. Контекст и цели

- Страница «Касса» (`/admin/payment-gateway`) уже показывает поля для:
  - ЮKassa, Тинькофф, Сбербанк, Robokassa, Stripe, PayPal, Своя касса.
- Сейчас при сохранении:
  - в API клиники (`PUT /v1/clinics/{id}`) уходят только:
    - `payment_gateway`
    - `payment_gateway_custom_name`
    - `yookassa_shop_id`
    - опционально `yookassa_secret_key` (перезапись зашифрованного ключа);
  - поля других касс и «Идентификатор / Ключ» для `custom` живут только в state фронта и **теряются** при перезагрузке.
- Цель этого промпта:
  - сделать так, чтобы **credentials всех касс кроме ЮKassa** сохранялись на бэкенде в зашифрованном виде, по архитектуре из `ARCH_PAYMENT_GATEWAYS.md` (раздел 5);
  - не трогать пока логику `PaymentService` (create payment → ЮKassa), только подготовить единое хранилище.

См. также:
- `docs/ARCH_PAYMENT_GATEWAYS.md` — раздел 5 (архитектура хранения).
- `docs/DEV_PROMPTS_PAYMENT_GATEWAYS.md` — тексты и поля UI.

---

## 2. Архитектура (что считаем реализованным после задачи)

После выполнения промпта должно быть так:

- В базе есть новая таблица `clinic_payment_gateways`, описанная в `ARCH_PAYMENT_GATEWAYS.md`:
  - `clinic_id`, `gateway`, `credentials_encrypted`, `status`, timestamps, опционально `created_by`/`updated_by`.
  - Уникальный ключ `(clinic_id, gateway)`.
- Есть сервис, который умеет:
  - по `(clinic_id, gateway)` **сохранять** credentials (строка JSON) в зашифрованном виде;
  - по `(clinic_id, gateway)` **читать** расшифрованную строку (для будущих интеграций и потенциальной диагностики через CLI/скрипты).
- Есть админский endpoint:
  - `POST /v1/admin/clinics/{clinic_id}/payment-gateway/credentials`,
  - принимает `gateway` + `payload` (строка JSON),
  - сохраняет или обновляет запись в `clinic_payment_gateways`,
  - возвращает `204 No Content` при успехе.
- Фронтенд на `/admin/payment-gateway`:
  - после успешного сохранения клиники (`PUT /v1/clinics/{id}`) отправляет credentials активной кассы на новый endpoint;
  - корректно обрабатывает ошибки (не скрывает форму, показывает сообщение).

Важно: **ЮKassa** продолжает использовать текущую схему (`clinics.yookassa_*`), чтобы не ломать рабочую оплату. Для ЮKassa credentials в новую таблицу пока не дублируем.

---

## 3. Данные и модели

### 3.1. Новая сущность `ClinicPaymentGateway`

**Файлы:**
- `src/domain/entities/clinic_payment_gateway.py` (новый)
- миграция в `alembic/versions/*.py`

**Требования к модели (см. ARCH 5.2):**

- Таблица `clinic_payment_gateways`:
  - `id: UUID` — PK;
  - `clinic_id: UUID` — FK → `clinics.id`, index;
  - `gateway: str` — String(32), not null (значения вроде `yookassa`, `tinkoff`, `sber`, `robokassa`, `stripe`, `paypal`, `custom`);
  - `credentials_encrypted: str | None` — Text, nullable;
  - `status: str` — String(32), not null, default/`server_default="PENDING"`;
  - `created_by: UUID | None` — опционально, для аудита (админ, который сохранил ключи);
  - `updated_by: UUID | None`;
  - `created_at`, `updated_at` — timestamps по паттерну других сущностей;
  - `__table_args__`: UniqueConstraint по `(clinic_id, gateway)`.

Миграция:
- Создать таблицу с указанными полями, индексами и уникальным ключом.
- `downgrade` — удаляет таблицу.

### 3.2. Сервис для работы с credentials

**Файл:**
- `src/application/services/clinic_payment_gateway_service.py` (новый)

**Функциональность:**

- Конструктор принимает `AsyncSession`.
- Методы:
  - `async def upsert_credentials(clinic_id: UUID, gateway: str, raw_payload: str, actor_id: UUID | None) -> ClinicPaymentGateway`:
    - находит запись по `(clinic_id, gateway)` или создаёт новую;
    - шифрует `raw_payload` через `encrypt_plaintext`;
    - пишет в `credentials_encrypted`;
    - устанавливает/обновляет `status = "PENDING"` (при первом сохранении или при обновлении);
    - сохраняет `created_by` / `updated_by`;
    - `flush + refresh` перед возвратом.
  - `async def get_credentials(clinic_id: UUID, gateway: str) -> str | None`:
    - находит запись по `(clinic_id, gateway)`;
    - если `credentials_encrypted` пуст, возвращает `None`;
    - иначе расшифровывает через `decrypt_ciphertext` и возвращает строку (без парсинга JSON).

Аудит (по желанию в этой задаче):
- Если есть готовая модель audit-логов для интеграций (по аналогии с `OmnichannelIntegrationsConfigService`), можно добавить простую запись «INTEGRATION_KEY_CREATED/ROTATED»; но это не обязательно для первого этапа, можно вынести в отдельную задачу.

---

## 4. Admin API: endpoint для сохранения credentials

**Файл:**
- новый роутер, например `src/api/v1/routers/admin_payment_gateway.py`
  - не путать с `/v1/owner/channels`; это именно **admin**‑уровень для клиник.
- зарегистрировать роутер в `src/api/v1/router.py`.

**Endpoint:**

- `POST /v1/admin/clinics/{clinic_id}/payment-gateway/credentials`
  - `clinic_id: UUID` — ID клиники (как в других admin-роутах).
  - Авторизация: как в других админских маршрутах (`get_current_admin` + проверка, что админ привязан к этой клинике).

**Request body (Pydantic):**

```python
class AdminPaymentGatewayCredentialsRequest(BaseModel):
    gateway: str = Field(..., max_length=32)  # например, "tinkoff", "sber", "robokassa", "stripe", "paypal", "custom"
    payload: str = Field(..., max_length=8000, description="JSON-строка с полями по провайдеру")
```

**Поведение:**

- Проверить, что клиника существует и принадлежит текущему администратору (по паттерну других admin-роутов).
- Вызвать `ClinicPaymentGatewayService.upsert_credentials` с:
  - `clinic_id` из пути,
  - `gateway` из тела (`.strip().lower()` для нормализации),
  - `raw_payload = body.payload`,
  - `actor_id = current_admin.id`.
- Вернуть `204 No Content`.

**Ошибки:**

- При отсутствии клиники — `404` с понятным `detail`.
- При длине payload > лимита или некорректном gateway можно вернуть `400` (но фронт в этой задаче не парсит ответ детально; главное — осмысленный `detail`).

---

## 5. Фронтенд: отправка credentials с «Кассы»

**Файл:**
- `frontend/src/admin/pages/AdminPaymentGatewayPage.tsx`

**Текущее поведение:**
- При нажатии «Сохранить» вызывается `api.put(/v1/clinics/{id}, body)` и обновляются:
  - `payment_gateway`
  - `payment_gateway_custom_name`
  - `yookassa_shop_id`
  - опционально `yookassa_secret_key`.

**Что нужно добавить:**

1. **Мутация для нового endpoint’а**
   - Добавить хук (по аналогии с `useSetOwnerOmniChannelCredentials`), например:
     - `useSetClinicPaymentGatewayCredentials(clinicId: string | null)` в новом файле `frontend/src/hooks/useAdminPaymentGateway.ts` или рядом с существующими admin-хуками.
   - Мутация вызывает:

```ts
api.post<void>(`/v1/admin/clinics/${clinicId}/payment-gateway/credentials`, {
  gateway,       // текущее значение state gateway (yookassa / tinkoff / sber / ... / custom)
  payload,       // JSON.stringify(credentialsObject)
});
```

2. **Формирование `credentialsObject` по активной кассе**

После успешного `PUT /v1/clinics/{id}`:

- Если `gateway === "yookassa"`:
  - **ничего не отправляем** в новый endpoint (ЮKassa живёт в полях клиники).
- Если `gateway === "tinkoff"`:
  - объект:
    - `terminal_key`: значение поля «Идентификатор терминала (Terminal Key)»;
    - `password`: значение поля «Пароль терминала».
- Если `gateway === "sber"`:
  - объект:
    - `userName`: значение поля «Логин (UserName)»;
    - `password`: значение поля «Пароль API».
- Если `gateway === "robokassa"`:
  - объект:
    - `merchant_login`: «Идентификатор магазина (Merchant Login)»;
    - `password1`: «Пароль #1»;
    - `password2`: «Пароль #2».
- Если `gateway === "stripe"`:
  - объект:
    - `secret_key`: «Secret key»;
    - `publishable_key`: «Publishable key (опционально)».
- Если `gateway === "paypal"`:
  - объект:
    - `client_id`: «Client ID»;
    - `client_secret`: «Client Secret».
- Если `gateway === "custom"`:
  - объект:
    - `identifier`: поле «Идентификатор»;
    - `key`: поле «Ключ».

Структуры и имена ключей совпадают с разделом 5.4 `ARCH_PAYMENT_GATEWAYS.md`.

3. **Вызов мутации и обработка ошибок**

- В `handleSave` после успешного обновления клиники:
  - если активная касса не `yookassa` и есть хотя бы одно непустое поле credentials для неё — вызвать мутацию на сохранение credentials;
  - при ошибке:
    - показать пользователю сообщение (например, через `notifications` или локальный `setError` под формой);
    - не блокировать работу «Касса» (важнее сохранить выбор кассы, чем ключи).

---

## 6. Нефункциональные требования

- **Безопасность:**
  - Credentials всегда шифруются перед записью.
  - Сырые credentials не возвращаются ни в одном API-ответе.
- **Миграции:**
  - Миграция не должна ломать существующие данные клиник и ЮKassa.
  - На пустой базе таблица создаётся корректно.
- **Тесты:**
  - Юнит-тесты для `ClinicPaymentGatewayService`:
    - upsert → создаёт новую запись и возвращает расшифрованную строку через get.
    - повторный upsert для того же `(clinic_id, gateway)` обновляет запись.
  - Минимальные API-тесты для нового endpoint’а:
    - happy path (204, запись создана);
    - 404 при несуществующей клинике/нет доступа (по аналогии с другими admin-роутами).

---

## 7. Готовность задачи

Задача считается выполненной, когда:

- Таблица `clinic_payment_gateways` создана и доступна;
- Endpoint `POST /v1/admin/clinics/{clinic_id}/payment-gateway/credentials` работает по контракту:
  - сохраняет/обновляет зашифрованные credentials;
  - возвращает 204 при успехе;
- Страница `/admin/payment-gateway`:
  - по‑прежнему сохраняет `payment_gateway` и поля ЮKassa;
  - дополнительно отправляет credentials активной кассы (кроме ЮKassa) на новый endpoint;
  - в случае ошибки сохранения credentials показывает пользователю сообщение (без потери уже сохранённого выбора кассы).

