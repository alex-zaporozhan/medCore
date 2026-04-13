# Dental Booking — Roadmap “Value → Price” (P0 / P1 / P2, code-backed)

Цель: поднять **коммерческую ценность** и **цену на рынке РФ**.  
Формат каждого пункта:

- **Что открывает (сегмент/цена)**: какой тип покупателя и какая прибавка к оценке.
- **Что менять (точно)**: конкретные файлы/модули.
- **Критерий готовности (доказательство)**: что можно показать покупателю и как проверить.

Ключевой принцип: **все утверждения опираются на код**. Если фича есть — указываем её кодовые точки; если нет — фиксируем gap.

---

## P0 — максимальный прирост цены за минимальный риск (0–6 недель)

### P0.1 Сделать omni‑омниканал “замкнутым”: outbound для `WHATSAPP_BUSINESS` и `VK_BOT`

- **Что открывает (сегмент/цена)**: контакт‑центр для клиник, где WA/VK — ключевые каналы. Существенно повышает цену (часто +25–60% к “MVP+” оценке), потому что omni‑чат перестаёт быть intake‑only.
- **Что менять (точно)**:
  - `src/application/services/omni_outbound_policy.py` (сейчас outbound разрешён только `TELEGRAM_BOT/WEB_WIDGET/WEB_APP`)
  - `src/application/services/omnichannel_outbound_dispatcher.py` (добавить адаптеры по `channel.type`)
  - `src/application/services/omnichannel_integrations_config_service.py` (уже есть encrypted secret store per omni channel)
  - `src/api/v1/routers/admin_omni_chat.py` (при необходимости: выбрать канал ответа `reply_channel_id`)
  - (опционально) новые файлы в `src/infrastructure/external_apis/` для VK/WhatsApp клиентов
- **Критерий готовности (доказательство)**:
  - E2E/интеграционный тест, который создаёт inbound из WA/VK → оператор отвечает → исходящее уходит в провайдера (или mock‑провайдера) и помечается delivery_status в `source_metadata`.
  - Код‑пруф: в `channel_type_allows_admin_outbound(...)` появляются `WHATSAPP_BUSINESS` и `VK_BOT`, а в dispatcher есть ветки `elif channel_type == "WHATSAPP_BUSINESS": ...` и `elif channel_type == "VK_BOT": ...`.

### P0.2 Мультиклиника для inbound webhooks: убрать “first clinic” шорткат

- **Что открывает (сегмент/цена)**: продажа сетям/партнёрам, где 1 инстанс обслуживает N клиник (повышает цену и снижает риск внедрения).
- **Что менять (точно)**:
  - `src/api/v1/routers/integrations_gateway.py` (`_get_default_business_account_id` сейчас берёт первую клинику)
  - `src/application/services/integration_gateway_service.py` (передача/выбор `business_account_id`)
  - (скорее всего) `src/domain/entities/omnichannel_integration_config.py` и/или `omni_channels` как источник “ключ → clinic_id”
- **Критерий готовности (доказательство)**:
  - Вебхук принимает `X-Clinic-Key` (или path key) → по нему резолвится `clinic_id` → сообщение попадает строго в нужную клинику.
  - Автотест: два clinic_id, один webhook key — сообщения не пересекаются.

### P0.3 Защитить критичные вебхуки (платежи + интеграции)

- **Что открывает (сегмент/цена)**: enterprise‑доверие и прохождение due diligence (юристы/безопасники).
- **Что менять (точно)**:
  - `src/api/v1/routers/payments.py` (`/payments/webhook` сейчас MVP без обязательной подписи)
  - `src/api/v1/routers/integrations_gateway.py` (WA/VK/Email/Instagram — добавить подпись/секрет/allowlist)
  - `src/core/config.py` (секреты/флаги)
- **Критерий готовности (доказательство)**:
  - Неверная подпись → 403; верная → 200.
  - Логи/метрики на rejection.

### P0.4 “Buyer‑grade” UX: единая полировка чатов (omni + staff + patient)

По коду видно, что у вас уже сильный UX слой:

- аудио‑запись в браузере: `frontend/src/shared/ui/VoiceNoteRecorderButton.tsx`
- staff chat: `frontend/src/admin/pages/AdminStaffChatPage.tsx`
- patient chat: `frontend/src/admin/pages/AdminChatPage.tsx`
- omni chat: `frontend/src/admin/pages/AdminOmniChatPage.tsx`

- **Что открывает (сегмент/цена)**: повышает perceived value (покупатели реально платят за “ощущение продукта”), снижает риск пилота.
- **Что менять (точно)**:
  - `frontend/src/shared/ClinicChatAttachments.tsx`, `frontend/src/shared/ChatInlineAudioPlayer.tsx`, `frontend/src/shared/chatAudioCoordinator.ts`
  - унификация: лимиты файлов, сообщения ошибок, поведение “caption + attachment”, одинаковые CTA
- **Критерий готовности (доказательство)**:
  - E2E: запись голоса → отправка → воспроизведение → (если роль owner) доступна загрузка аудио.
  - UX чеклист: одинаковые состояния `Loading/Empty/Error/Success` и одинаковые ограничения (5MB vs staff max).

### P0.5 Док‑пакет “для сделки” (влияние на цену такое же, как код)

- **Что открывает (сегмент/цена)**: покупатель/биржа могут оценить быстро, меньше торга.
- **Что менять (точно)**:
  - `docs/PRODUCT_DOSSIER_BUYER_READY.md` (уже создан)
  - `docs/VALUATION_CODE_BACKED.md` (уже создан)
  - добавить `docs/EXEC_SUMMARY_ONE_PAGER.md` (1 страница)
- **Критерий готовности (доказательство)**:
  - документ на 1 страницу: сегменты, УТП, ограничения (outbound‑каналы), демо‑сценарии.

---

## P1 — усиление “enterprise‑контуров” и монетизации (6–12 недель)

### P1.1 Отдельный “Network Owner” режим в UI для управления клиниками

- **Что открывает (сегмент/цена)**: сети, франшизы, управляющие компании (добавляет к цене, т.к. расширяет рынок).
- **Что менять (точно)**:
  - backend: `src/api/v1/clinic_scope.py` (уже есть механизм `effective_clinic_id` для owner‑кросс‑клиники)
  - фронт: `frontend/src/contexts/AdminClinicContext.tsx` + страницы, где сейчас жёстко “текущая клиника”
  - конкретные admin‑роуты, которые должны поддерживать `effective_clinic_id` (как `admin_rbac_management.py` уже делает)
- **Критерий готовности (доказательство)**:
  - owner может выбрать клинику в UI → видит данные/настройки выбранной клиники без logout/login.

### P1.2 Привести WA/VK inbound к реальным payload формам (или формализовать gateway)

- **Что открывает (сегмент/цена)**: снимает “интеграционный риск” у покупателя.
- **Что менять (точно)**:
  - `src/application/services/integration_gateway_service.py` (`normalize_whatsapp_message`, `normalize_vk_message`)
  - `src/api/v1/routers/integrations_gateway.py`
- **Критерий готовности (доказательство)**:
  - тестовые payload’ы из документации провайдера проходят; ошибки дают структурированный ответ.

### P1.3 Omni‑AI: отчётность/аудит действий и “kill switch” по клинике

- **Что открывает (сегмент/цена)**: клиники, где нужен контроль AI (юр/комплаенс).
- **Что менять (точно)**:
  - `src/application/services/omnichannel_ai_orchestrator.py` (уже пишет `AiToolEvent`; усилить отчёты/сводки)
  - `src/api/v1/routers/admin_ai_reports.py` / `admin_ai_status.py` (подтянуть в единую панель)
  - фронт: страница AI‑статуса/настроек
- **Критерий готовности (доказательство)**:
  - “AI activity log” на клинику/чат: какие tools вызваны, что изменили, trace_id.

### P1.4 Канбан/таски: довести до “продукта уровня Linear”

Канбан у вас уже сильный по коду: `frontend/src/admin/pages/AdminTasksPage.tsx` использует `@dnd-kit/core`, WIP лимиты, статусы, stream’ы, lead‑лог связки.

- **Что открывает (сегмент/цена)**: покупатели платят за операционку “как в SaaS”, а не “табличку”.
- **Что менять (точно)**:
  - `frontend/src/admin/pages/AdminTasksPage.tsx` (perf, hotkeys, массовые операции, стабильность drag&drop)
  - hooks: `frontend/src/hooks/useAdminTasks.ts` (инвалидации/оптимистик)
  - backend: `src/api/v1/routers/admin_tasks.py`, `admin_task_boards.py`, `admin_task_streams.py`
- **Критерий готовности (доказательство)**:
  - E2E: drag card между колонками, WIP предупреждения, массовая смена статуса, автосохранение порядка.

### P1.5 Staff Collab “suite”: feed + chat + calendar + knowledge как единый продукт

По коду видно полноценный набор:

- staff feed (в Dashboard): `frontend/src/admin/pages/AdminDashboardPage.tsx` + hooks `useStaffCollab.ts`
- staff chat: `frontend/src/admin/pages/AdminStaffChatPage.tsx`
- knowledge base: `frontend/src/admin/pages/AdminKnowledgePage.tsx`

- **Что открывает (сегмент/цена)**: продукт воспринимается как “операционная система клиники”.
- **Что менять (точно)**:
  - унификация chrome/навигации/empty states
  - добавить e2e smoke сценарии по staff suite
- **Критерий готовности (доказательство)**:
  - demo‑скрипт: пост → лайк/коммент → вложение → аудио → чат группы → событие календаря → статья базы знаний.

---

## P2 — масштабирование и премиум‑упаковка (12+ недель)

### P2.1 Мультитенант‑аудит “везде” + доказательства из тестов

- **Что открывает (сегмент/цена)**: снижает риски для сетей/партнёров → меньше торга.
- **Что менять (точно)**:
  - расширить tenant‑аудит (у вас уже есть gate `scripts/audit_tenant_columns.py` в CI по `Jenkinsfile`)
  - добавить тесты на cross‑clinic leakage по ключевым модулям
- **Критерий готовности (доказательство)**:
  - тест suite, который пытается получить данные другой клиники и получает 404/403.

### P2.2 Выделение “Integration Gateway” в отдельный сервис (опционально)

- **Что открывает (сегмент/цена)**: проще комплаенс, проще поддержку множества каналов, легче продавать enterprise.
- **Что менять (точно)**:
  - вынести `integrations_gateway.py` + normalize в отдельный деплойный сервис
- **Критерий готовности (доказательство)**:
  - отдельный контейнер/репо/compose‑профиль; контракт DTO стабильный.

### P2.3 “Evidence pack” для покупателя (security/ops)

- **Что открывает (сегмент/цена)**: максимальный чек на сделке.
- **Что менять (точно)**:
  - добавить документы/скрипты, которые генерируют evidence: результаты тестов, список эндпоинтов, модели данных.
- **Критерий готовности (доказательство)**:
  - один архив/папка: отчёт тестов, список API, инфра‑диаграмма, threat model вебхуков.

