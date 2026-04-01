# ARCH_AUDIT_NEXT — короткие отметки закрытых архитектурных хвостов

| Дата | Тема | Статус |
|------|------|--------|
| 2026-03-21 | Структурированные ошибки Booking/Payments (`BookingErrorResponse`), метрики `booking_errors_total`, OpenAPI, RBAC W7 (manager → ERP/attribution read), карта SEC | Wave 7 (BKG_ERRORS / SEC_RBAC «на потом») зафиксированы в коде и документах; см. `QA_ARCH_BACKLOG_NA_POTOM_UNIFIED` BE*, SR*. |
| 2026-03-21 | QA_ARCH follow-up: `trace_id` в глобальном 500 и webhook; `payment_webhook_failures_total`; complete/retry → `BookingErrorResponse`; инвентарь `sec_rbac_router_permissions.txt` + pytest CI gate; `_emit_booking_api_error` → `NoReturn` | Закрывает пробелы отчёта QA (BE2 частично, SR3, типизация). |
