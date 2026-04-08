# Результат входа через соцсеть (OAuth)

> **Аудитория:** пациент.  
> **Источник UI:** `frontend/src/app/pages/OAuthResultPage.tsx`.

## Адрес

`/oauth/result` (query-параметры: `oauth`, `status`, при успехе — `token`, `patient_id`).

## Поведение

- **Успех (`status=ok` + токен и id):** сохраняется сессия пациента, редирект на текущий путь под `/app` или на `/app`.
- **Отмена (`status=cancelled`):** возврат на `/login`.
- **Ошибка** (`error`, `state_invalid`, `provider_error`): сообщение о неудачном входе, через ~3 с — редирект на `/login`.
- Иные случаи — редирект на `/login`.

Подписи провайдера в интерфейсе: **VK**, **Яндекс** или нейтральное «соцсеть» в зависимости от `oauth`.

## См. также

- [PATIENT_LOGIN.md](./PATIENT_LOGIN.md)
