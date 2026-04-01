# DEV_PROMPTS: Единый чат — мост PWA → omni, канал WEB_APP, мультиклиника

> Подробный пошаговый план для @DEV по документу `ARCH_UNIFIED_CHAT_BIZ_AND_PLAN.md`. Цель: сообщения из внутреннего чата (PWA) попадали в Единый чат; ответы админа из Единого чата по каналу WEB_APP доходили до пациента в PWA; корректная работа для любой клиники в сети.

---

## 0. Почему сообщения из PWA «нигде не появились»

- Сообщения от пациента (например, +79001234576 в клинике Dental_Booking 2) пишутся **только** в `conversations` и `chat_messages`. Мост в омниканаль **не реализован** (Фаза 2 не делалась).
- Интерфейс «Единый чат» читает **только** `omni_chats` и `omni_messages`. Поэтому диалоги из PWA в нём не отображаются.
- **Что сделать:** реализовать мост (ниже). После этого каждое сообщение из PWA будет дублироваться в omni с каналом `WEB_APP` и появится в Едином чате **для той же клиники**, к которой привязан пациент.

---

## 1. Связь с БД и мультиклиника (кратко для реализации)

- **Изоляция по клинике:** везде `business_account_id = clinic_id` (одна клиника = один «бизнес-аккаунт»).
- **Пациент:** у каждого пациента один `patient.clinic_id`. При отправке сообщения из PWA используем именно этот `clinic_id` как `business_account_id` для создания Contact/Chat/Message в omni.
- **Админ:** сейчас список чатов в API строится по `current_admin.clinic_id`. То есть админ видит только чаты своей клиники. Для «выбора клиники» в Едином чате — см. блок 6 (опционально).

---

## 2. Блок 1: Канал WEB_APP в OmnichannelChatService

**Файл:** `src/application/services/omnichannel_chat_service.py`

**Задача:** В `get_or_create_channel_for_provider` добавить маппинг для провайдера `"WEB_APP"`:

- Если `provider_upper == "WEB_APP"`, задавать `channel_type = "WEB_APP"` (без преобразования).
- Дальше логика та же: `select(Channel).where(business_account_id, type=channel_type)`, при отсутствии — создать канал с `type="WEB_APP"`, `display_name="WEB_APP"` (или «Приложение»), `status="PENDING_SETUP"`.

**Критерий готовности:** Вызов `get_or_create_channel_for_provider(business_account_id, "WEB_APP")` возвращает UUID канала и при повторном вызове возвращает тот же канал.

---

## 3. Блок 2: Поиск/создание Contact по Patient (patient_id)

**Файлы:**  
- `src/domain/interfaces/repositories/omnichannel_chat_repository.py`  
- `src/infrastructure/database/omnichannel_chat_repo_impl.py`  
- `src/application/services/omnichannel_chat_service.py`

**Задача:**

1. **Репозиторий Contact:** уже есть `find_by_external_id(business_account_id, external_key, external_value)`. Использовать для поиска контакта по пациенту: `external_key="patient_id"`, `external_value=str(patient_id)`.
2. **Сервис:** добавить метод вида:
   - `get_or_create_contact_for_patient(self, business_account_id: UUID, patient_id: UUID, full_name: str | None, primary_phone: str | None) -> Contact`
   - Логика: вызвать `contacts.find_by_external_id(business_account_id, "patient_id", str(patient_id))`. Если нашли — вернуть.
   - Если не нашли: создать `Contact(business_account_id=..., full_name=full_name, primary_phone=primary_phone, external_ids={"patient_id": str(patient_id)})`, сохранить, вернуть.

**Критерий готовности:** По `patient_id` и `clinic_id` можно получить один и тот же Contact; при первом обращении он создаётся, при повторном — возвращается существующий.

---

## 4. Блок 3: Мост «сообщение от пациента PWA → omni»

**Файлы:**  
- `src/application/services/chat_service.py`  
- `src/application/services/omnichannel_chat_service.py`  
- (опционально) отдельный модуль `src/application/services/unified_chat_bridge.py`

**Задача:** После успешной записи сообщения пациента в `Conversation` и `ChatMessage` (в `send_message_from_patient`) выполнять мост в омниканаль:

1. Загрузить пациента из БД по `patient_id` (нужны `full_name`, `phone` / `primary_phone`).
2. `get_or_create_contact_for_patient(clinic_id, patient_id, full_name, primary_phone)`.
3. `get_or_create_channel_for_provider(clinic_id, "WEB_APP")` → `channel_id`.
4. `get_or_create_chat(clinic_id, contact, channel_id)`.
5. **Идемпотентность:** перед созданием сообщения в omni проверять, что сообщение с таким внешним id ещё не есть. Использовать `source_metadata = {"provider": "WEB_APP", "external_message_id": f"patient_msg_{chat_message.id}"}` (или `str(chat_message.id)`). В репозитории уже есть `exists_by_chat_and_external_id(chat_id, provider, external_message_id)`. В сервисе — `exists_inbound_by_external_id`. Если уже есть — не создавать повторно, не падать.
6. `create_inbound_message(chat, contact, content=body, channel_id=channel_id, source_metadata=source_metadata)`.

**Важно:** Мост вызывать **после** коммита/флаша `ChatMessage` и `Conversation`, чтобы `chat_message.id` был известен. Если мост выполнять в той же транзакции, порядок: создали ChatMessage → flush → затем создаём Message в omni. При сбое моста транзакция откатится — допустимо; при следующей отправке идемпотентность по `external_message_id` не сработает (id сообщения может быть другой), поэтому в качестве `external_message_id` надёжнее использовать стабильный ключ, например `f"patient_msg_{conversation_id}_{chat_message.id}"` после flush.

**Критерий готовности:** Отправка сообщения из PWA от любого пациента любой клиники создаёт запись в `omni_messages` и обновляет omni_chat; диалог появляется в списке Единого чата для этой клиники.

---

## 5. Блок 4: Диспетчер WEB_APP — ответ админа в PWA

**Файл:** `src/application/services/omnichannel_outbound_dispatcher.py`

**Задача:** В методе, который по `channel_type` выбирает способ доставки (сейчас: TELEGRAM_BOT, WEB_WIDGET, иначе — лог), добавить ветку для **`WEB_APP`**:

1. Не вызывать внешние API (Telegram, WhatsApp и т.д.).
2. Загрузить Contact по `chat.contact_id`. Из `contact.external_ids` взять `patient_id` (строка UUID).
3. По `patient_id` и `business_account_id` (из чата = clinic_id) найти `Conversation` (таблица `conversations`, уникальность по clinic_id + patient_id).
4. Если Conversation не найдена — залогировать предупреждение и выйти (сообщение уже записано в omni_messages, но в PWA не попадёт).
5. Записать в `chat_messages` новое сообщение: `sender_type="admin"`, `body=message.content`, привязка к найденной Conversation. Обновить `conversations`: `last_message_at`, `last_message_sender_type`, увеличить `unread_by_patient_count`.
6. При наличии в проекте механизма push/лонгполла для PWA — вызвать уведомление о новом сообщении (опционально).

**Зависимости:** Нужен доступ к `Conversation`, `ChatMessage`, репозиторию разговоров/сообщений. Диспетчер может получить сессию и вызвать `ChatService` или напрямую репозитории — по усмотрению, без циклических импортов.

**Критерий готовности:** Ответ админа в Едином чате в диалоге с каналом WEB_APP появляется в PWA пациента (запись в `chat_messages`, пациент видит при обновлении/подгрузке).

---

## 6. Блок 5: Поиск по контакту в списке чатов (опционально, но желательно)

**Файл:** `src/infrastructure/database/omnichannel_chat_repo_impl.py` (и при необходимости интерфейс в `omnichannel_chat_repository.py`)

**Задача:** Сейчас `list_chats` фильтрует поиск только по `Chat.title`. Для чатов WEB_APP заголовок часто пустой. Расширить поиск: если передан `search`, дополнительно искать по полям контакта (`Contact.full_name`, `Contact.primary_phone`) через join Chat → Contact. Конкретика: в запросе `list_chats` при непустом `search` добавить join с `Contact` по `Chat.contact_id` и условие вида `(Chat.title.ilike(...) OR Contact.full_name.ilike(...) OR Contact.primary_phone.ilike(...))`.

**Критерий готовности:** В Едином чате поиск по имени или телефону находит диалоги WEB_APP.

---

## 7. Блок 6: Выбор клиники в Едином чате (опционально)

**Задача:** Реализовать возможность «чат клиники №1» / «чат клиники №2», если в UI админ может переключать клинику.

**Бэкенд:**  
- В эндпоинтах списка/детали чатов (например, `GET /admin/omni-chats`, `GET /admin/omni-chats/{id}`, и остальные, где используется `business_account_id`) принимать опциональный query-параметр `clinic_id` (UUID).  
- Если `clinic_id` передан: проверить, что `current_admin.clinic_id == clinic_id` (пока единственная модель доступа). Подставить этот `clinic_id` как `business_account_id` при выборке.  
- Если не передан — использовать `current_admin.clinic_id` как сейчас.

**Фронтенд:**  
- На странице Единого чата передавать в API выбранную в шапке клинику: `currentClinicId` из `useAdminClinic()` — в query всех запросов к `/admin/omni-chats` (например, `?clinic_id=...`).  
- При смене клиники в шапке список чатов перезапрашивается для выбранной клиники.

**Критерий готовности:** Админ может выбрать клинику в шапке и видеть в Едином чате только чаты этой клиники. Режим «чат всех клиник» в этот блок не входит (см. ARCH).

---

## 8. Блок 7: Тесты и проверка «крепкой связи»

**Минимально:**

1. **Мост PWA → omni:** Интеграционный тест: создать пациента в клинике A, от имени пациента отправить сообщение через API `POST /patient/chat/conversation/messages`; проверить, что в БД появились запись в `omni_contacts` (с `external_ids.patient_id`), запись в `omni_chats` (channel_type WEB_APP), запись в `omni_messages` (INBOUND, CLIENT). Вызвать `GET /admin/omni-chats` под админом клиники A — в списке должен быть этот диалог.
2. **Диспетчер WEB_APP:** Тест: создать omni_chat с channel WEB_APP и contact с `external_ids.patient_id`; отправить сообщение от админа через `POST /admin/omni-chats/{id}/messages`; проверить, что в `chat_messages` появилось сообщение и что соответствующая `Conversation` обновлена; при запросе сообщений из PWA для этого пациента сообщение видно.
3. **Идемпотентность:** Дважды выполнить мост для одного и того же `chat_message.id` (или одного и того же внешнего ключа) — во второй раз не должно создаваться дубликата в `omni_messages`.

**Ручная проверка:** Пациент +79001234576 (Иванов В.П.) в клинике Dental_Booking 2: отправить два сообщения из PWA; открыть Единый чат под админом этой клиники — оба сообщения и диалог должны отображаться; ответить из Единого чата — ответ должен появиться в чате пациента в PWA.

---

## 9. Порядок выполнения (рекомендуемый)

1. Блок 1 (канал WEB_APP).  
2. Блок 2 (Contact по patient_id).  
3. Блок 3 (мост при send_message_from_patient).  
4. Блок 4 (диспетчер WEB_APP).  
5. Блок 5 (поиск по контакту).  
6. Блок 7 (тесты и ручная проверка).  
7. Блок 6 (выбор клиники) — по необходимости.

После выполнения блоков 1–4 и 7 связь «любой пациент любой клиники → Единый чат этой клиники» и «ответ из Единого чата → PWA пациента» должна быть обеспечена.
