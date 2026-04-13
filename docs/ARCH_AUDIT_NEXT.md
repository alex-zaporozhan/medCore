# ARCH_AUDIT_NEXT — короткие отметки закрытых архитектурных хвостов

| Дата | Тема | Статус |
|------|------|--------|
| 2026-04-03 | Пошаговая архитектурная карта репозитория | Каталог [architecture/INDEX.md](architecture/INDEX.md): runtime, backend/frontend по слоям, данные, кэш/очереди, метрики, матрица тестов; журнал неясностей `architecture/UNRESOLVED_AND_CONFUSION_LOG.md`. |
| 2026-03-21 | Структурированные ошибки Booking/Payments (`BookingErrorResponse`), метрики `booking_errors_total`, OpenAPI, RBAC W7 (manager → ERP/attribution read), карта SEC | Wave 7 зафиксированы в коде и документах; детали — git history до консолидации artifacts. |
| 2026-03-21 | QA_ARCH follow-up: `trace_id` в глобальном 500 и webhook; `payment_webhook_failures_total`; complete/retry → `BookingErrorResponse`; инвентарь `sec_rbac_router_permissions.txt` + pytest CI gate; `_emit_booking_api_error` → `NoReturn` | Закрывает пробелы отчёта QA (BE2 частично, SR3, типизация). |
