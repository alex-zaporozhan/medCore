# Пользовательская документация — оглавление

> **Версия:** 2026-04-02  
> **Аудитория:** конечные пользователи продукта (без доступа к коду).  
> **Правило:** тексты сняты с реализации UI в репозитории (компоненты, строки, маршруты). При расхождении с продуктом приоритет у развёрнутого экземпляра; затем — код.

## Объём v1 (QA)

- **Входит:** часто используемые потоки (вход, запись, чат, ключевые разделы админки из сайдбара) и публичные вспомогательные URL.  
- **Пока агрегировано в KB §5.2:** большинство остальных сегментов `/admin/*` (финансы, omni-настройки, интеграции и т.д.) — без отдельного `USER_DOCS` до второй волны @SCRIBE.

## Как читать

1. Выберите роль: **сотрудник клиники (админка)** или **пациент (PWA)** / **гость (маркетинг)**.  
2. Ниже — прямые ссылки на страницы; полный перечень URL сегментов админки — [../PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §5.2.

## Админка (`/admin`)

| Раздел | Документ | Примечание |
|--------|----------|------------|
| Вход | [ADMIN_LOGIN.md](./ADMIN_LOGIN.md) | `/admin/login` |
| Лента (дашборд) | [ADMIN_DASHBOARD.md](./ADMIN_DASHBOARD.md) | `/admin` |
| Записи | [ADMIN_BOOKINGS.md](./ADMIN_BOOKINGS.md) | |
| Расписание | [ADMIN_SCHEDULE.md](./ADMIN_SCHEDULE.md) | |
| Пациенты | [ADMIN_PATIENTS.md](./ADMIN_PATIENTS.md) | право `patients.pii.read` |
| Омниканал (инбокс) | [ADMIN_OMNI_CHAT.md](./ADMIN_OMNI_CHAT.md) | |
| Чат команды | [ADMIN_STAFF_CHAT.md](./ADMIN_STAFF_CHAT.md) | не путать с omni-chat |
| Лиды (лог) | [ADMIN_LEADS_LOG.md](./ADMIN_LEADS_LOG.md) | право `leads.log.view` |
| Формы и документы | [ADMIN_FORMS.md](./ADMIN_FORMS.md) | нет в сайдбаре |
| Права и политики | [../RBAC_RIGHTS_POLICIES_GUIDE.md](../RBAC_RIGHTS_POLICIES_GUIDE.md) | право `rbac.manage` для пункта меню |

Остальные разделы админки (финансы, маркетинг, omni-каналы, настройки и т.д.) описаны агрегированно в **PRODUCT_KNOWLEDGE_BASE** §5.2; по запросу @SCRIBE можно вынести отдельные `USER_DOCS` под тот же шаблон.

## PWA пациента (`/app` и связанные URL)

| Раздел | Документ |
|--------|----------|
| Вход / регистрация | [PATIENT_LOGIN.md](./PATIENT_LOGIN.md) (`/login`) |
| OAuth (соцсети) | [PATIENT_OAUTH_RESULT.md](./PATIENT_OAUTH_RESULT.md) (`/oauth/result`) |
| Главная | [PATIENT_HOME.md](./PATIENT_HOME.md) |
| Лента | [PATIENT_FEED.md](./PATIENT_FEED.md) |
| Запись | [PATIENT_BOOKING.md](./PATIENT_BOOKING.md) |
| История | [PATIENT_HISTORY.md](./PATIENT_HISTORY.md) |
| Лояльность | [PATIENT_LOYALTY.md](./PATIENT_LOYALTY.md) |
| Анкеты | [PATIENT_FORMS.md](./PATIENT_FORMS.md) |
| Чат | [PATIENT_CHAT.md](./PATIENT_CHAT.md) |
| Профиль | [PATIENT_PROFILE.md](./PATIENT_PROFILE.md) |
| Запись оформлена | [BOOKING_SUCCESS.md](./BOOKING_SUCCESS.md) (`/booking/success`) |

## Маркетинг (`/`)

| Раздел | Документ |
|--------|----------|
| Лендинг | [MARKETING_LANDING.md](./MARKETING_LANDING.md) |
| Профиль врача (публично) | [PUBLIC_DOCTOR_PROFILE.md](./PUBLIC_DOCTOR_PROFILE.md) (`/:clinicSlug/doctors/:doctorSlug`) |

---

**Сопровождение:** при изменении подписей или маршрутов — обновить соответствующий файл и таблицу в [../PRODUCT_KNOWLEDGE_BASE.md](../PRODUCT_KNOWLEDGE_BASE.md) §5.

Reference: [../SCRIBE.md](../SCRIBE.md)
