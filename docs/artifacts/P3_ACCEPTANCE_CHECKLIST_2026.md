# P3 Omni-Chat Acceptance Checklist (2026-03-25)

> Цель: зафиксировать фактический статус закрытия P3 по критериям фазы `ARCH_PHASE_03_OMNI_CHAT_2026.md`.

## 1) Рабочая станция омниканала

- [x] Чат как основной рабочий экран администратора (`/admin/omni-chat`)
- [x] Быстрая запись из чата без перехода на расписание (центрированная модалка)
- [x] Быстрое создание задачи из контекста чата
- [x] Быстрая отправка анкеты/ссылки пациенту
- [x] Горячие клавиши: поиск, отправка, сворачивание правой панели, quick booking

## 2) Delivery/Read и индикация

- [x] Бэкенд сохраняет `delivery_status` в `source_metadata` для поддерживаемых каналов
  - `TELEGRAM_BOT` (ack от API)
  - `WEB_APP`
  - `WEB_WIDGET`
- [x] API `/admin/omni-chats/{chat_id}/messages` возвращает `delivery_status` / `read_status` (когда доступны)
- [x] UI отображает бейджи `Доставлено` / `Прочитано` для outbound-сообщений
- [ ] Единая сквозная обработка read-receipts для всех внешних провайдеров (post-MVP)

## 3) UX/сплит-панель и edge-cases

- [x] Устойчивый выбор чата при фильтрации/переключении списка (автоподхват первого доступного)
- [x] Коллапс/экспанд правой панели с сохранением состояния
- [x] Центрированные модалки по UI-инварианту
- [ ] Доп. UX polish по большим перепискам (виртуализация/advanced timeline) — вне текущего среза

## 4) AI-метки и контекстные подсказки

- [x] AI-метка в сообщениях (`actor_type=AI`)
- [x] AI-фильтр и AI-режимы на уровне диалога
- [x] Подсказки по состоянию AI-фич (feature gates / tool availability)
- [ ] Финальный продуктовый copy-review всех AI-тултипов (@LEAD/@UX)

## 5) Regression (P3)

- [x] `tests/api/test_admin_omni_chat.py`
- [x] `tests/api/test_owner_omni_channels.py`
- [x] `tests/api/test_owner_omni_audit.py`
- [x] `tests/api/test_owner_omni_ai_settings.py`
- [x] `tests/security/test_security_chats.py`
- [x] `tests/services/test_unified_chat_bridge.py`
- [x] `tests/services/test_omnichannel_ai_orchestrator.py` (после стабилизации фикстур/настроек)

## 6) Итог

- Статус: **P3 закрыт по целевому acceptance-срезу текущего релиза**.
- Остаток в бэклоге: кросс-провайдерные read-receipts и расширенный UX-polish (не блокеры этого Done).
