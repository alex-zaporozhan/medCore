# Соответствие CRM реализации DEV_PROMPTS_CRM_KANBAN

> Проверка: @DEV. Дата: 2026-03. Источник: `DEV_PROMPTS_CRM_KANBAN.md`.

---

## 1. Backend — модель данных и миграции

| Требование | Статус | Примечание |
|------------|--------|------------|
| Сущности: `lead_pipeline.py`, `lead_stage.py`, `lead_card.py`, `lead_note.py` | ✅ | Все в `src/domain/entities/` |
| LeadPipeline: id, clinic_id, name, description, is_default, timestamps | ✅ | |
| LeadStage: id, pipeline_id, order, code, name, probability, color | ✅ | + clinic_id в модели |
| LeadCard: перечисленные поля + primary_booking_id, status, estimated/actual_value | ✅ | + visit_attribution_id, utm_* |
| LeadNote: id, lead_id, author_admin_id, created_at, text | ✅ | + clinic_id |
| Таблицы и индексы Alembic | ✅ | По текущим сущностям |

---

## 2. Backend — сервисы и события

| Требование | Статус | Примечание |
|------------|--------|------------|
| `lead_repository.py` (интерфейс) | ✅ | `src/domain/interfaces/repositories/lead_repository.py` |
| LeadRepositoryImpl | ✅ | `src/infrastructure/database/lead_repo_impl.py` |
| create_lead_from_contact | ✅ | LeadService |
| update_stage / change_lead_stage | ✅ | Реализовано как `change_lead_stage` |
| attach_booking | ✅ | LeadService |
| attach_payment | ✅ | Реализовано как `apply_payment_to_lead` |
| list_leads(filters, pagination) | ✅ | + patient_id, booking_id |
| get_lead_details(lead_id) | ✅ | |
| add_lead_note(lead_id, admin_id, text) | ✅ | |
| Обработчики: ContactCreated, BookingCreated, PaymentSuccess, BookingCompleted | ✅ | `lead_event_handlers.py`, поиск по primary_booking_id |

---

## 3. Backend — API админки

| Требование | Статус | Примечание |
|------------|--------|------------|
| GET /admin/crm/pipelines | ✅ | |
| GET /admin/crm/stages?pipeline_id= | ✅ | |
| GET /admin/crm/leads (stage_id, status, date_from/to, source, search, page, page_size) | ✅ | + patient_id, booking_id |
| GET /admin/crm/leads/{id} | ✅ | Детали + заметки |
| PATCH /admin/crm/leads/{id}/stage | ✅ | RBAC manage_crm |
| POST /admin/crm/leads/{id}/notes | ✅ | RBAC manage_crm |
| view_crm / manage_crm | ✅ | Роутер и PATCH/POST |

---

## 4. Frontend — Kanban

| Требование | Статус | Примечание |
|------------|--------|------------|
| Маршрут /admin/sales | ✅ | В роутинге админки |
| Страница AdminSalesPipelinePage | ✅ | |
| Левая панель: фильтры (стадия, период, источник) | ✅ | Pipeline, стадия, статус, поиск |
| Краткие показатели (кол-во лидов, суммы по этапам) | ⚠️ | Кол-во по колонкам есть; сводные суммы по этапам — при желании расширить |
| Центр: Kanban, столбцы = LeadStage, карточки = LeadCard | ✅ | leadsByStage, KanbanColumn |
| Карточки: имя/контакт, канал, стадия, оценка/факт, метки | ✅ | title, source, estimated_value, actual_value, status |
| drag&drop между столбцами → PATCH /leads/{id}/stage | ✅ | Реализовано на @dnd-kit: карточки перетаскиваются в колонки стадий, при дропе вызывается `useUpdateLeadStage` (PATCH /leads/{id}/stage). Подсветка колонки при перетаскивании (isOver). |
| Правая панель: детали лида, заметки, форма добавления заметки | ✅ | |

---

## 5. Хуки и типы (Frontend)

| Требование | Статус | Примечание |
|------------|--------|------------|
| Типы: LeadPipeline, LeadStage, LeadCard, LeadNote, фильтры, ответы | ✅ | `useCrmLeads.ts` |
| useCrmPipelines, useCrmStages, useCrmLeads, useCrmLeadDetails | ✅ | |
| useUpdateLeadStage, useCreateLeadNote | ✅ | |

---

## 6. OmniChat и AI

| Требование | Статус | Примечание |
|------------|--------|------------|
| Стадия и estimated_value/actual_value в правой панели | ✅ | AdminOmniChatPage |
| Кнопка «Открыть лид» → /admin/sales?lead_id= | ✅ | |

---

## 7. Итог

- **Соответствие DEV_PROMPTS:** в целом полное. Расхождение по названиям: `update_stage` → `change_lead_stage`, `attach_payment` → `apply_payment_to_lead` (эквивалентная функциональность).
- **Необязательные отличия:**
  - Фильтр «ответственный» в API/UI не добавлен (в промпте опционально).
  - Полноценный drag&drop между колонками Kanban не реализован; смена стадии делается через выбор в деталях лида и вызов PATCH.

Реализовано: на странице используется @dnd-kit (DndContext, useDraggable для карточек, useDroppable для колонок). При дропе карточки в другую колонку вызывается PATCH /leads/{id}/stage, после успеха инвалидируются запросы списка лидов.
