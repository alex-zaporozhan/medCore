/**
 * Единая фабрика ключей TanStack Query (техпаспорт §5.1 — клиника, фильтры, домен).
 * Хуки импортируют отсюда, чтобы инвалидация и optimistic-обновления ссылались на те же кортежи.
 */

export const queryKeys = {
  clinics: {
    all: ["clinics"] as const,
    list: (includeDeleted: boolean) => ["clinics", { includeDeleted }] as const,
  },
  adminTasks: {
    /** Префикс для invalidateQueries — все списки задач админки */
    prefix: ["admin-tasks"] as const,
    list: () => ["admin-tasks"] as const,
    myFocus: (adminId: string | null) => ["admin-tasks", "my-focus", adminId] as const,
    ai: () => ["admin-tasks", "ai"] as const,
    /** GET /v1/admin/tasks?status=open — виджет в Omni Chat */
    open: () => ["admin-tasks", "open"] as const,
  },
  adminAdmins: {
    list: () => ["admin-admins"] as const,
  },
  attentionFeed: (clinicId: string | null) =>
    ["admin", "clinics", clinicId, "attention-feed"] as const,
  adminDiscounts: (clinicId: string | null) => ["admin-discounts", clinicId] as const,
  adminClientReference: () => ["admin-client-reference"] as const,
  adminNotificationPolicy: (clinicId: string | null) =>
    ["admin-notification-policy", clinicId] as const,
  agreementSettings: (clinicId: string | null) => ["agreement-settings", clinicId] as const,
  integrationSettings1c: (clinicId: string) => ["integration-settings", clinicId, "1c"] as const,
  adminRetention: {
    segments: (clinicId: string) => ["admin", "retention", "segments", clinicId] as const,
    campaignsRoi: (clinicId: string) => ["admin", "retention", "campaigns-roi", clinicId] as const,
  },
  omniVault: {
    media: (clinicId: string, filters: { type?: string; date_from?: string }) =>
      ["admin", "omni-vault", "media", clinicId, filters] as const,
    exportPresets: (clinicId: string) => ["admin", "omni-vault", "export-presets", clinicId] as const,
    backup: (clinicId: string) => ["admin", "omni-vault", "backup", clinicId] as const,
  },
  adminAiReports: {
    conflicts: (dateFrom: string, dateTo: string) =>
      ["admin-ai-reports-conflicts", dateFrom, dateTo] as const,
  },
  /** Глобальный статус AI + настройки клиники (страница AI Settings). */
  adminAi: {
    clinicSettings: (clinicId: string | null) =>
      ["admin", "clinics", clinicId, "ai-settings"] as const,
    status: () => ["admin", "ai-status"] as const,
  },
  /** CRM / Kanban — единый префикс для инвалидации списков лидов. */
  crm: {
    pipelines: () => ["crm-pipelines"] as const,
    stages: (pipelineId: string | null) => ["crm-stages", pipelineId] as const,
    pipelineSemantics: (pipelineId: string | null) =>
      ["crm-pipeline-stage-semantics", pipelineId] as const,
    leadsListPrefix: ["crm-leads"] as const,
    kanbanInfinite: (
      stageId: string,
      status: string,
      search: string,
      pageSize: number
    ) => ["crm-leads-kanban", stageId, status, search, pageSize] as const,
    kanbanPrefix: ["crm-leads-kanban"] as const,
    leadDetails: (leadId: string | null) => ["crm-lead-details", leadId] as const,
    leadAiSummary: (leadId: string | null) => ["crm-lead-ai-summary", leadId] as const,
    leadAiSuggest: (leadId: string | null) =>
      ["crm-lead-ai-suggest-stage", leadId] as const,
  },
} as const;
