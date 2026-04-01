# DEV_PROMPTS: Пакет тестов бэкенда — улучшения и новые тесты

> Промпты для @DEV по документу `ARCH_QA_SEC_BACKEND_TEST_PACKAGE.md`. Выполнять по порядку: сначала блок A (улучшения), затем B (security-тесты), затем C (маркеры и документация).

---

## Блок A. Улучшения существующих тестов (QA)

### A.1. Rate limit для admin login в тестах (429)

**Цель:** при запуске полного набора тестов admin login не должен возвращать 429.

**Варианты (реализовать один):**

- **Вариант 1 (рекомендуется):** в `src/core/config.py` для настроек `rate_admin_login_ip_limit` и `rate_admin_login_email_limit` при `os.environ.get("TESTING") == "1"` подставлять очень большие значения (например, 100_000) или считать лимит отключённым (0 = не проверять; в `RateLimiter.check_or_raise` при `limit <= 0` уже есть ранний return).
- **Вариант 2:** в `src/api/v1/routers/admin_auth.py` перед вызовом `rate_limiter.check_or_raise` проверять `os.environ.get("TESTING") == "1"` и не вызывать rate limiter в тестах.

**Критерий готовности:** `poetry run pytest tests/api/test_admin_payment_gateway_credentials.py tests/api/test_admin_omni_chat.py tests/api/test_owner_omni_ai_settings.py -v` проходит без 429 (при необходимости запустить дважды подряд).

---

### A.2. Мок SMS для send-code в тестах

**Цель:** тесты, использующие `POST /api/v1/auth/send-code` и `patient_auth`, не вызывают реальный SMS и не падают с 500.

**Действия:**

- В тестах, где вызывается send-code (например, `test_auth_send_code`, `test_frontend_integration.py::test_auth_send_code`, e2e `test_booking_to_payment_flow`), замокать отправку SMS так, чтобы код по-прежнему записывался в Redis (логика `AuthService.send_code` сохраняет код в Redis до вызова SMS). Варианты:
  - В `TESTING=1` в `AuthService.send_code` (или в SMS-клиенте) не вызывать внешний HTTP/SMS, а только записывать код в Redis и возвращать успех.
  - Либо в этих тестах через `monkeypatch` или `patch` подменять метод отправки SMS на no-op (например, `SmsClient.send_sms` — пустая корутина или сохранение кода без реальной отправки).

**Файлы для правок:** `src/application/services/auth_service.py`, или `src/infrastructure/external_apis/sms_client.py`, или тесты (patch в conftest/тесте).

**Критерий готовности:** `test_auth_send_code` и `test_booking_to_payment_flow` проходят без 500 из-за SMS.

---

### A.3. Добавить admin_auth в тесты, дающие 401

**Цель:** тесты admin-эндпоинтов передают заголовок авторизации и получают 200, а не 401.

**Список тестов и правки:**

1. **tests/api/test_pricing_and_ai.py**
   - `test_admin_clinic_services_pricing_fields` — добавить в сигнатуру `admin_auth: dict`, сформировать `headers = {"Authorization": f"Bearer {admin_auth['access_token']}"}` и передавать `headers=headers` в `client.get(f"/api/v1/admin/clinics/{clinic_id}/services")`.
   - `test_admin_chat_ai_summary_fallback_without_provider` — добавить `admin_auth`, передавать заголовок в запросе к admin chat AI.
   - `test_admin_chat_ai_suggest_reply_fallback_without_provider` — то же.
   - `test_admin_patient_ai_insight_fallback_without_provider` — добавить `admin_auth`, передавать заголовок в GET admin/patients/.../ai-insight.
   - `test_admin_ai_reports_conflicts_reanalyze_and_list` — добавить `admin_auth`, передавать заголовок в POST и GET к admin/ai-reports/conflicts.

2. **tests/api/test_frontend_integration.py**
   - `test_admin_bookings_list` — добавить в сигнатуру `admin_auth: dict`, передавать `headers={"Authorization": f"Bearer {admin_auth['access_token']}"}` в `client.get("/api/v1/admin/bookings")`.
   - `test_reports_dashboard`, `test_reports_no_show`, `test_reports_revenue` — если эти эндпоинты требуют админ-токен, добавить `admin_auth` и заголовок (проверить по роутеру).
   - `test_admin_doctor_schedule` — если требуется админ, добавить `admin_auth` и заголовок.

**Критерий готовности:** перечисленные тесты выполняются с `admin_auth` и проходят (статус 200 где ожидается).

---

### A.4. «Чужой» clinic_id в тестах изоляции

**Цель:** тесты «доступ запрещён к чужой клинике/каналу» используют заведомо чужой ID и ожидают 404/403.

**Проверить:**

- `tests/api/test_owner_omni_channels.py::test_owner_cannot_access_foreign_channel` — уже создаёт канал с `other_clinic_id = uuid.uuid4()` и проверяет 404. Убедиться, что тест стабильно проходит.
- Если есть другие тесты с формулировкой «cannot access foreign X», убедиться, что подставляется UUID другой клиники/сущности (не из seed_data для текущего админа).

**Критерий готовности:** все тесты изоляции проходят; при подстановке чужого ID возвращается 404 или 403.

---

### A.5. Фикстура admin_auth — scope session (опционально)

**Цель:** снизить число запросов на admin login при полном прогоне.

**Действие:** в `tests/conftest.py` рассмотреть смену фикстуры `admin_auth` на `scope="session"`. Учесть, что `client` и `seed_data` должны быть доступны в сессии; при session-scoped client один раз залогиниться и вернуть токен. Если это потребует переработки порядка фикстур (client зависит от init_db, seed_data), можно оставить текущий scope и полагаться на A.1 (ослабление rate limit в тестах).

**Критерий готовности:** либо реализовано session-scoped admin_auth, либо явно решено оставить function scope с учётом A.1.

---

## Блок B. Security-тесты (SEC)

**Общее:** создать каталог `tests/security/` и файлы `test_security_kassa.py`, `test_security_pd.py`, `test_security_chats.py`. Все тесты помечать `@pytest.mark.security`. Использовать фикстуры из `conftest`: `init_db`, `seed_data`, `client`, `admin_auth`, `patient_auth`, `redis_client`. При необходимости импортировать сущности и `AsyncSessionLocal` из `src.infrastructure.database.base` и т.п.

---

### B.1. tests/security/test_security_kassa.py (SEC-K1–K5)

- **SEC-K1.** Тест: от имени админа своей клиники выполнить GET эндпоинты, которые возвращают данные клиники или платежей (например, GET /v1/clinics/{id} или аналог из admin; GET списка платежей/букингов, если есть). Сериализовать ответ в JSON (или строку) и проверить, что в нём нет подстрок, похожих на секретные ключи: например, нет полей `yookassa_secret_key`, `secret_key` в открытом виде, нет `credentials_encrypted` с расшифрованным содержимым. Можно проверять отсутствие ключевых слов из payload (terminal_key, password, client_secret) в значениях ответа.
- **SEC-K2.** Тест: запрос `POST /v1/admin/clinics/{clinic_id}/payment-gateway/credentials` с токеном админа клиники A и `clinic_id = B` (другой UUID, не A). Ожидать 404 (или 403). Уже покрыто в `test_admin_payment_gateway_credentials.py`; при желании продублировать в security с маркером `security`.
- **SEC-K3.** Тест: после вызова `ClinicPaymentGatewayService.upsert_credentials` с известным `raw_payload` (например, `{"terminal_key":"T1","password":"P1"}`) прочитать из БД запись в `clinic_payment_gateways` и убедиться, что в поле `credentials_encrypted` нет подстрок `"T1"`, `"P1"`, `terminal_key`, `password` в открытом виде (хранится только шифрованный текст).
- **SEC-K4.** Пропустить или заглушить: «если появится проверка подписи webhook — тест неверная подпись → 401/400». Сейчас можно добавить `@pytest.mark.skip(reason="Webhook signature not implemented yet")` и короткий docstring.
- **SEC-K5.** По возможности: тест или ревью, что при сохранении credentials в лог не попадают сырые значения. Вариант: в тесте вызвать endpoint сохранения credentials и проверить, что в перехваченных логах (если перехват настроен) нет строки из payload. При сложности настройки перехвата логов — оставить в документе как ревью-пункт, в коде не реализовывать.

**Критерий готовности:** в `tests/security/test_security_kassa.py` есть тесты для SEC-K1, SEC-K2, SEC-K3; SEC-K4 помечен skip при отсутствии подписи; SEC-K5 по возможности или пропущен.

---

### B.2. tests/security/test_security_pd.py (SEC-P1–P4)

- **SEC-P1.** Тест: админ клиники A (seed_data) получает список пациентов или врачей своей клиники (200). Затем запрос к эндпоинту пациента/врача с подменённым ID на UUID другой клиники (или несуществующий, но в URL подставить patient_id/doctor_id от другой клиники, если есть способ создать вторую клинику в seed или в тесте). Ожидать 404 или 403. Конкретные эндпоинты взять из роутеров (например, GET /v1/admin/patients/{id} или GET /v1/doctors с фильтром по clinic).
- **SEC-P2.** Тест: вызвать эндпоинт, который возвращает ошибку (например, GET /v1/admin/patients/{несуществующий-uuid} с валидным admin_auth). Проверить, что в `response.json()` (или в `detail`) нет телефона, email, ФИО из seed_data пациентов/врачей. То есть сообщение об ошибке не подставляет ПД в текст.
- **SEC-P3.** Тест: если в API есть отчёты или экспорт с параметром `clinic_id`, запрос от админа клиники A с подставленным `clinic_id = B` (другой UUID) должен вернуть 404/403 или пустой результат без данных клиники B.
- **SEC-P4.** Кратко: при наличии эндпоинтов согласий/ПД — тест, что пациент не может изменить данные другого пациента; админ не может получить/изменить данные пациентов чужой клиники. Реализовать один-два сценария по существующим маршрутам.

**Критерий готовности:** в `tests/security/test_security_pd.py` есть тесты для SEC-P1, SEC-P2; SEC-P3 и SEC-P4 по возможности по текущим эндпоинтам.

---

### B.3. tests/security/test_security_chats.py (SEC-C1–C4)

- **SEC-C1.** Тест: с токеном админа клиники A вызвать GET списка чатов/сообщений (admin omni chat). В запросе подставить параметр `clinic_id` равный UUID другой клиники (или второй клиники, созданной в тесте). Убедиться, что в ответе нет данных чатов другой клиники (пустой список или 403).
- **SEC-C2.** Тест: с `patient_auth` вызвать GET сообщений разговора. Подставить `conversation_id` от другого пациента (создать второго пациента и разговор в тесте, запросить сообщения с conversation_id этого разговора). Ожидать 404 или 403.
- **SEC-C3.** Тест: owner не может получить/обновить канал другой клиники. Уже есть аналог в `test_owner_cannot_access_foreign_channel`. Продублировать в security с маркером `security` или сослаться на тот тест (и пометить его `@pytest.mark.security`).
- **SEC-C4.** Тест: вызов admin AI summary/suggest/insight с корректным clinic_id. Проверить, что в ответе нет идентификаторов (chat_id, message_id) или текстов сообщений из другой клиники. При отсутствии второй клиники в seed — проверить хотя бы структуру ответа и отсутствие в нём полей с сырыми сообщениями чужих чатов.

**Критерий готовности:** в `tests/security/test_security_chats.py` есть тесты для SEC-C1, SEC-C2, SEC-C3; SEC-C4 по возможности.

---

## Блок C. Маркеры и документация

### C.1. Маркеры pytest

Маркеры уже добавлены в `pyproject.toml`: `regression_payments`, `regression_pd`, `regression_chats`, `security`. Нужно проставить их в тестах:

- В тестах оплат и payment gateway (например, `test_payments.py`, `test_admin_payment_gateway_credentials.py`, `test_clinic_payment_gateway_service.py`, релевантные тесты из `test_pricing_and_ai.py`, `test_booking_to_payment.py`) добавить `@pytest.mark.regression_payments` там, где это регрессия по оплатам.
- В тестах безопасности ПД и изоляции по клинике (SEC-P, тесты пациентов/врачей) добавить `@pytest.mark.regression_pd`.
- В тестах чатов и омниканалов (admin_omni_chat, owner_omni_channels, patient_chat) добавить `@pytest.mark.regression_chats`.
- Во всех тестах в `tests/security/*` и в дублирующих сценариях в api добавить `@pytest.mark.security`.

**Критерий готовности:** `pytest -m security` запускает только security-тесты; `pytest -m regression_payments` — регрессию по оплатам (по желанию то же для regression_pd и regression_chats).

### C.2. Документация

- В `docs/QA_REGRESSION_PAYMENTS_ADMIN.md` в начале или в разделе «Запуск» добавить ссылку на пакет тестов: «Полный пакет тестов (архитектура, QA, security): `docs/ARCH_QA_SEC_BACKEND_TEST_PACKAGE.md`. Промпты для реализации: `docs/DEV_PROMPTS_BACKEND_TEST_PACKAGE.md`.»
- По желанию создать `docs/QA_SMOKE.md` с минимальным дымовым набором после деплоя: health, auth send-code (с моком), один GET admin с admin_auth, один POST payments/webhook. Либо один файл `tests/smoke/test_smoke.py` с этими кейсами и команду запуска в документе.

**Критерий готовности:** ссылка в QA_REGRESSION добавлена; при желании создан QA_SMOKE или tests/smoke.

---

## Итог для @DEV

1. Выполнить блок A (A.1–A.5) — улучшения тестов и окружения.
2. Выполнить блок B (B.1–B.3) — создать `tests/security/` и тесты SEC-K, SEC-P, SEC-C.
3. Выполнить блок C (C.1–C.2) — маркеры и обновление документации.

После этого пакет считается внедрённым. Запуск: полный регресс по `docs/QA_REGRESSION_PAYMENTS_ADMIN.md`, отдельно `pytest tests/security/ -v` или `pytest -m security -v`.
