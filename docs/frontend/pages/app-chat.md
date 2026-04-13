# App Chat

## Метаданные

- **Path:** `/app/chat` и зеркало `/c/:clinicSlug/app/chat`
- **Зона:** app (пациент)
- **Компонент(ы) в App.tsx:** `ChatPage` в `PATIENT_APP_PAGE_BY_SEGMENT`
- **Файл страницы:** `frontend/src/app/pages/ChatPage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/app/pages/ChatPage.tsx`<br>`frontend/src/contexts/PatientAuthContext.tsx ← импорт из frontend/src/app/pages/ChatPage.tsx`<br>`frontend/src/hooks/usePatientChat.ts ← импорт из frontend/src/app/pages/ChatPage.tsx`<br>`frontend/src/hooks/useStickers.ts ← импорт из frontend/src/app/pages/ChatPage.tsx`<br>… +9 файлов |
| Строк (сумма по фрагментам) | 2055 |
| Хуки (эвристика, union) | `useDeletePatientMessage`, `useMutation`, `usePatientAuth`, `usePatientChat`, `usePatientChatMessages`, `usePatientConversation`, `usePatientMarkRead`, `useQuery`, `useQueryClient`, `useSendPatientMessage`, `useSendPatientMessageWithFile`, `useStickerSets`, `useStickers` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/auth/login`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments`, `/v1/stickers/sets` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 1, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

Чат пациента с клиникой: беседа и последние сообщения, текст, стикеры и вложения до 5 МБ, голосовые заметки, blob для вложений, удаление своих сообщений и массовая очистка с подтверждением в модалке.

## Логика и данные

- **Хуки:** `usePatientAuth`; из `usePatientChat` — conversation, messages, send, sendWithFile, markRead, deleteMessage; `useStickerSets` из `useStickers`; `authApi` для файла вложения.
- **queryKey:** `patient-chat-conversation` с patientId; `patient-chat-messages` с patientId; `stickers-sets`.
- **API:** GET conversation и messages с query `patient_id`; POST сообщения и upload; DELETE сообщения; POST mark-read; GET вложения по id; публичный GET `/v1/stickers/sets`.

## RBAC / entitlements / edition

- Нужны токен и patientId; иначе заглушка (**fact**).

## UI-скелет (as-built)

Лента в `ScrollArea`, композер с `AppleEmojiOverlayTextarea`, микрофон, эмодзи, вложения, кнопка отправки, `Popover` со стикерами.

## Инвентарь поверхностей UI (ось H)

- **Modal:** подтверждение очистки своих сообщений.
- **Popover:** выбор стикера.
- **AdminDrawer, GlassModal:** нет.

## Целевой UX (target vs as-built)

- *target:* бесконечная история, ответы на сообщение.
- *as-built:* лимит сообщений в запросе, mark-read при открытии.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- Выделенных vitest под страницу не найдено.

## Gap scan (вторая редакция)

- Очистка «моих» — цикл отдельных DELETE.
- Ошибки отправки файла только кратким текстом под композером.
