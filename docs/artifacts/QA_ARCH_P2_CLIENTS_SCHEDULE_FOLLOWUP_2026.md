# Мини-эпик P2 — Clients & Schedule (follow-up @QA_ARCH)

> **Назначение:** зафиксировать **рекомендации после ревью качества** по объёму фазы P2 (расписание, пациенты, `/admin/loyalty`), не смешивая с полным сводным бэклогом `QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md`.  
> **Связь:** `ARCH_PHASE_02_CLIENTS_SCHEDULE_2026.md` §9; продуктовый контекст — `MASTER_PRODUCT_ROADMAP_2026.md` (фаза 2).

**Статус:** пункты **P2-FU1–FU7** закрыты в коде в рамках ревью @QA_ARCH (2026-03-24); **403 cross-tenant PATCH** остаётся покрытием общих multitenancy-тестов при необходимости.

---

## Критичность и суть

| ID | Критичность | Суть | Намётка |
|----|-------------|------|---------|
| **P2-FU1** | Высокая (контракт API) | **PATCH** `/admin/bookings/{id}`: различать *поле не передано* и *передано `null`* для `notes`, чтобы **можно было очистить** комментарий. Сейчас при `notes: null` обновление может не применяться. | `BookingPatchAdmin` + сервис: `model_dump(exclude_unset=True)` и установка `booking.notes` при наличии ключа `notes`. |
| **P2-FU2** | Средняя (безопасность / модель доступа) | **GET** `/v1/patients` с фильтром по визитам расширяет поверхность; при отсутствии явной админской авторизации на роуте — **решить политику** (только admin JWT, internal network, или оставить как есть с осознанным риском). | Аудит `patients.py` + S-02; при необходимости — `Depends(get_current_admin)` или отдельный admin-префикс. |
| **P2-FU3** | Средняя (UX + данные) | Фильтр **визит с / по**: валидация `visited_from <= visited_to`; сообщение при перепутанных датах. | Backend 422 или фронт; не молчаливый пустой список. |
| **P2-FU4** | Средняя (UX) | После успешного PATCH `notes` — **обновить** отображаемую запись в drawer (ответ мутации в state / инвалидация + подстановка). | `usePatchBookingAdmin` + `SchedulePage` / drawer props. |
| **P2-FU5** | Низкая (тесты) | Расширить тесты: **403** при PATCH записи другой клиники; сценарий **очистки** `notes`; при необходимости — негативные кейсы фильтра пациентов. | `tests/api/test_p2_clients_schedule.py` или новый модуль. |
| **P2-FU6** | Низкая (UX) | Deep link **`?patient_id=`** на `/admin/patients`: если пациент не в текущей выборке — **подсказка** («сбросьте фильтры»), а не молчаливое отсутствие карточки. | Копирайт + условный `Alert`/`Text`. |
| **P2-FU7** | Низкая (UX) | **`/admin/loyalty`**: в таблицах абонементов показывать **имя пакета** вместо «голого» UUID (где возможно без N+1). | Маппинг пакетов из `useLoyaltyPackages` + подпись колонки. |

### Выполнено (код)

| ID | Где |
|----|-----|
| P2-FU1 | `booking_service.patch_booking_admin`: `model_dump(exclude_unset=True)`; тест очистки `notes` |
| P2-FU2 | `patients.py`: GET/GET by id/PUT/DELETE с `get_current_admin`, клиника из JWT; `POST` без auth сохранён; `client.ts`: `isPatientsPublicCreatePost` |
| P2-FU3 | `patient_service.get_patients`: `visited_from > visited_to` → `ValueError` → 422 |
| P2-FU4 | `BookingEntityDrawer` + `SchedulePage`: `onBookingNotesSaved` |
| P2-FU5 | `test_p2_clients_schedule.py`: 401, 422, очистка `notes` |
| P2-FU6 | `AdminPatientsPage`: `Alert` при `patient_id` в URL и не в списке |
| P2-FU7 | `AdminLoyaltyPage`: `packageNameById` для колонки пакета |

---

## Отложено по продукту (не этот мини-эпик)

- **`resource_id` на слоте** расписания — отдельная миграция и контракт API; см. `ARCH_PHASE_02_CLIENTS_SCHEDULE_2026.md` §3 и IA салона.

---

## Где ещё лежат «рекомендации на будущее» по проекту

| Документ | Назначение |
|----------|------------|
| **`QA_ARCH_BACKLOG_NA_POTOM_UNIFIED.md`** | Единый сводный бэклог «на потом» (perf, ERP, Omni, waves) — **inventorизация + triage**. |
| **`docs/operations/BACKLOG_NFR.md`** | Идеи NFR и ops после коробки v1 (не смешивать с первым прогоном @LEAD). |
| **`QA_ARCH_POST_WAVES_FUNDAMENTALS_BACKLOG.md`** | Пост-waves фундамент, пересечение с Wave 4/5/7. |
| **`DEV_PROMPT_QA_ARCH_UNIFIED_BACKLOG.md`** | Промпт/структура волн QA_ARCH (если используется в команде). |

---

## История

| Дата | Изменение |
|------|-----------|
| 2026-03-24 | Первая версия мини-эпика по ревью @QA_ARCH после закрытия объёма P2 в коде. |
| 2026-03-24 | Закрытие P2-FU1–FU7 в репозитории; таблица «Выполнено» |
