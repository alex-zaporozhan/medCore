# Omnichannel: медиа, URL в тексте, голос (LEAD)

## Цели

- **Омниканал**: картинки по прямым URL в тексте, вложения от админа (файл + подпись), воспроизведение аудио в ленте.
- **Мост PWA ↔ omni**: вложения пациента/админа из `clinic_chat` отображаются в omni через `source_metadata.clinic_chat_bridge` (скачивание тем же API, что и админский чат с пациентом).
- **Исходящее в WEB_APP**: файлы из omni копируются в `clinic_chat`-вложения к созданному `ChatMessage` (см. `OmnichannelOutboundDispatcher._dispatch_web_app`).
- **Telegram**: для сообщений с `omni_files` в метаданных — `sendPhoto` / `sendVoice` (ogg) / `sendDocument` (остальное).
- **Голос**: запись в браузере (`MediaRecorder`, webm), загрузка существующими эндпоинтами чатов; MIME `audio/*` разрешён для PWA/админского диалога (`ChatService._allowed_clinic_chat_upload_mime`).

## Хранилище omni-файлов

- Каталог: `{staff_chat_upload_root}/{clinic_id}/omni/{attachment_id}_{safe_name}`.
- Метаданные в `omni_messages.source_metadata`:
  - `omni_files`: `[{ id, file_name, content_type, size_bytes, storage_rel }]`
  - `clinic_chat_bridge`: `{ conversation_id, message_id, attachments: [...] }` (входящий мост из PWA).

## API

- `POST /v1/admin/omni-chats/{chat_id}/messages/upload` — `multipart/form-data`: `body`, `file`, опционально `reply_channel_id`.
- `GET /v1/admin/omni-chats/{chat_id}/messages/{message_id}/attachments/{attachment_id}/file` — байты файла из `omni_files`.

## UI

- `OmniMessageRichBody`: Apple-эмодзи, ссылки, превью URL-картинок, `ClinicChatAttachments` для обоих источников вложений.
- `VoiceNoteRecorderButton`: общий компонент для PWA, админ↔пациент, staff-chat, omni (где подключён).

## Ограничения / дальнейшее

- Внешние картинки по URL загружаются браузером клиента (CORS/hotlinking).
- WhatsApp/VK и др. каналы: доставка медиа не расширялась в этом эпике (логи «no adapter» как раньше).
