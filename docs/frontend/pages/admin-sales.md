# Admin Sales

## Метаданные

- **Path:** `/admin/sales`
- **Зона:** admin
- **Компонент(ы) в App.tsx:** `AdminShellSegmentPage` → `AdminSalesPipelinePage`
- **Файл страницы:** `frontend/src/admin/pages/AdminSalesPipelinePage.tsx`

<!-- AUTO_MANIFEST:BEGIN -->
**Автоинвентарь из кода** (скрипт `scripts/enrich_page_passport_manifest.py`, UTC **2026-04-09 08:03 UTC**).

| Поле | Значение |
|------|----------|
| Источник | `frontend/src/admin/pages/AdminSalesPipelinePage.tsx`<br>`frontend/src/hooks/useCrmLeads.ts ← импорт из frontend/src/admin/pages/AdminSalesPipelinePage.tsx`<br>`frontend/src/components/layout/ThreeColumnLayout.tsx ← импорт из frontend/src/admin/pages/AdminSalesPipelinePage.tsx`<br>`frontend/src/shared/ui/DataSkeleton.tsx ← импорт из frontend/src/admin/pages/AdminSalesPipelinePage.tsx`<br>… +8 файлов |
| Строк (сумма по фрагментам) | 2563 |
| Хуки (эвристика, union) | `useAdminClinic`, `useAdminSession`, `useAiCreateTaskForLead`, `useAiFeatures`, `useAiIgnoreLeadRecommendation`, `useAiLeadSummary`, `useAiSuggestNextStage`, `useAiUpdateLeadStage`, `useAvailableAiTools`, `useBusinessLexicon`, `useClinics`, `useCreateLeadNote`, `useCrmKanbanStageLeadsInfinite`, `useCrmLeadDetails`, `useCrmLeads`, `useCrmPipelines`, `useCrmStages`, `useDraggable`, `useDroppable`, `useInfiniteQuery`, `useMutation`, `usePipelineStageSemantics`, `useQuery`, `useQueryClient`, `useSensor`, `useSensors`, `useUpdateLeadStage`, `useVirtualizer` |
| Пути в строках `/v1/...` | `/v1/admin`, `/v1/admin/ai-status`, `/v1/admin/auth/login`, `/v1/admin/crm/pipelines`, `/v1/admin/omni/available-tools`, `/v1/admin/ui-events`, `/v1/clinics`, `/v1/clinics/`, `/v1/owner/`, `/v1/patient/`, `/v1/patients`, `/v1/payments` |
| Вхождения UI | AdminDrawer: 0, GlassModal: 0, Modal: 0, Menu: 0 |

> Не заменяет паспорт v2 и блоки «Evidence / QA»: это **снимок статического анализа**, может содержать шум. Скриншоты SPA без отдельного e2e-контура с логином **не генерируются**.

<!-- AUTO_MANIFEST:END -->

## Назначение

CRM Kanban по лидам: выбор пайплайна и стадий, виртуализированные колонки с бесконечной подгрузкой карточек (`@tanstack/react-virtual`), DnD перенос между стадиями с учётом семантики стадий (`crmStageSemantics`), правая колонка с деталями лида, заметками, AI-подсказками (summary, suggest stage, apply, create task, ignore), ссылкой на предоплату в буфер обмена, ссылками в omni-чаты.

## Логика и данные

- **Хуки:** `useCrmPipelines`, `useCrmStages`, `useCrmKanbanStageLeadsInfinite`, `useCrmLeadDetails`, `useCreateLeadNote`, `useUpdateLeadStage`, `useAiLeadSummary`, `useAiSuggestNextStage`, `useAiUpdateLeadStage`, `useAiCreateTaskForLead`, `useAiIgnoreLeadRecommendation`, `usePipelineStageSemantics`, `useAvailableAiTools`, `useAiFeatures`, `useAdminClinic`, `useQueryClient`, `useSearchParams`.
- **Типовые API (`/v1/...`):**
  - `GET /v1/admin/crm/pipelines`
  - `GET /v1/admin/crm/stages?pipeline_id=...`
  - `GET /v1/admin/crm/pipelines/{id}/stage-semantics`
  - `GET /v1/admin/crm/leads?...` (в т.ч. `projection=kanban`, курсор для infinite)
  - `GET /v1/admin/crm/leads/{leadId}`
  - `PATCH /v1/admin/crm/leads/{leadId}/stage`
  - `POST /v1/admin/crm/leads/{leadId}/notes`
  - AI: `GET .../ai/summary`, `GET .../ai/suggest-next-stage`, `PATCH .../ai/stage`, `POST .../ai/tasks`, `POST .../ai/recommendations/ignore`

## RBAC / entitlements / edition

- **fact:** Сегмент `sales` → ключ **`crm.pipeline`** в `SEGMENT_ENTITLEMENT`.

## UI-скелет (as-built)

- `ContextBar`, `ThreeColumnLayout` / `AdminDataTableToolbar`, колонки Kanban, выделенная карточка лида.
- Правая панель: детали, AI-блоки с `AiFeatureBadge` и отключением при `stub`, заметки, кнопка копирования ссылки предоплаты.

## Инвентарь поверхностей UI (ось H)

- **AdminDrawer / GlassModal:** нет (**fact:** детали лида — встроенная колонка layout, не выезжающая панель `AdminDrawer`).
- **`Alert`:** ошибки API (в т.ч. `ApiErrorWithCode`) в контексте Kanban/AI.
- **DnD:** `@dnd-kit/core` для перетаскивания карточек между стадиями.

## Целевой UX (target vs as-built)

- *target:* воронка продаж с AI-подсказками и соблюдением семантики стадий.
- *as-built:* тяжёлая страница с виртуализацией и строгими проверками переходов.

## Копирайт

- См. [`docs/COPY_STYLE_POLICY_RU.md`](../../COPY_STYLE_POLICY_RU.md).

## Тесты

- **gap:** e2e на DnD и AI желательны из-за сложности.

## Gap scan (вторая редакция)

- Локальное хранилище `crm-kanban-strict-semantics` влияет на поведение — задокументировать операторам при появлении runbook.
