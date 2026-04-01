# Поддержка: поиск по `trace_id` (BKG_ERRORS_005 / W7 BE7)

## Где берётся `trace_id`

- Ответы API с телом `BookingErrorResponse` содержат поле **`trace_id`** (если middleware OBS заполнил контекст запроса).
- Тот же идентификатор пишется в структурные логи поля **`trace_id`** / **`extra.trace_id`**.

## Как искать

1. Взять `trace_id` из ответа клиента (PWA / админка) или из сообщения пользователя.
2. В Loki / ELK / файлах логов: фильтр `trace_id="<значение>"`.
3. Сопоставить с `clinic_id` из того же лога (не подставлять сырой UUID в Prometheus-лейблы — см. `prometheus_labels.clinic_bucket`).

## Ошибки без `trace_id`

- Если в ответе `trace_id: null`, проверить включение OBS/trace middleware и заголовки прокси.
