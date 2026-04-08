# Публичный профиль врача

> **Аудитория:** гость. **Источник:** `frontend/src/marketing/pages/PublicDoctorProfilePage.tsx`.

## URL

`/:clinicSlug/doctors/:doctorSlug` (см. `App.tsx`).

## Содержание

ФИО, специализация, фото при наличии. Кнопка **«Записаться на приём»** ведёт на `/app/booking` с `clinic_id` и `doctor_id` в query. Ошибка загрузки: **«Профиль врача недоступен»**.

## Примечание

Маршрут с параметрами **не** входит в `ALL_PUBLIC_APP_PATHS` (фиксированный список для тестов). См. [PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §5.4.

## См. также

[PATIENT_BOOKING.md](./PATIENT_BOOKING.md) · [MARKETING_LANDING.md](./MARKETING_LANDING.md)
