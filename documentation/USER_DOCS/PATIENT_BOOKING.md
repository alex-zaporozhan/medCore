# Запись на приём (мастер)

> **Аудитория:** пациент.  
> **Источник UI:** `frontend/src/app/pages/BookingWizardPage.tsx`.

## Адрес

`/app/booking`

## Назначение

Пошаговый мастер записи (**«Запись на приём»**). Шаги зависят от числа клиник:

- при **нескольких** клиниках: клиника → услуга → врач → слот → оплата (при необходимости);
- при **одной** клинике шаг «клиника» опускается (см. расчёт `clinicStep` / `payStep` в коде).

Выбор клиники подхватывается из query `?clinic_id=` и из `localStorage` (`app.selectedClinicId`).

## После успешной записи

Возможен переход на сценарий оплаты и страницу успеха — см. `BookingSuccessPage` по маршруту `/booking/success`.

## См. также

- [PATIENT_HOME.md](./PATIENT_HOME.md)  
- [../PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §6.3
