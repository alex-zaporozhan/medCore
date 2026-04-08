/**
 * Единая фабрика ключей TanStack Query (клиника, фильтры, домен).
 * Хуки импортируют отсюда, чтобы инвалидация и optimistic-обновления ссылались на те же кортежи.
 */

export const queryKeys = {
  clinics: {
    all: ["clinics"] as const,
    list: (includeDeleted: boolean) => ["clinics", { includeDeleted }] as const,
  },
  staffCollab: {
    feedPosts: () => ["staff-collab", "feed-posts"] as const,
    feedComments: (postId: string | null) => ["staff-collab", "feed-comments", postId] as const,
    chatRooms: () => ["staff-collab", "chat-rooms"] as const,
    chatMessages: (roomId: string | null) => ["staff-collab", "chat-messages", roomId] as const,
    calendarPrefix: ["staff-collab", "calendar"] as const,
    calendarEvents: (fromIso: string, toIso: string) =>
      ["staff-collab", "calendar", fromIso, toIso] as const,
    calendarMonth: (fromIso: string, toIso: string) =>
      ["staff-collab", "calendar-month", fromIso, toIso] as const,
    calendarEventDetails: (eventId: string) => ["staff-collab", "calendar-event-details", eventId] as const,
    knowledgeDocs: () => ["staff-collab", "knowledge"] as const,
  },
  adminTasks: {
    /** Префикс для invalidateQueries — все списки задач админки */
    prefix: ["admin-tasks"] as const,
    list: (
      streamId?: string | null,
      tagIds?: string[],
      completedFrom?: string | null,
      completedTo?: string | null
    ) =>
      [
        "admin-tasks",
        streamId ?? "all",
        ...(tagIds?.length ? [tagIds.slice().sort().join(",")] : []),
        ...(completedFrom ? [`completedFrom:${completedFrom}`] : []),
        ...(completedTo ? [`completedTo:${completedTo}`] : []),
      ] as const,
    myFocus: (adminId: string | null) => ["admin-tasks", "my-focus", adminId] as const,
    ai: () => ["admin-tasks", "ai"] as const,
    /** GET /v1/admin/tasks?status=open — виджет в Omni Chat */
    open: () => ["admin-tasks", "open"] as const,
  },
  adminTaskBoards: {
    list: () => ["admin-task-boards"] as const,
  },
  adminTaskStreams: {
    list: () => ["admin-task-streams"] as const,
  },
  adminTaskTags: {
    list: () => ["admin-task-tags"] as const,
  },
  adminAdmins: {
    list: () => ["admin-admins"] as const,
  },
  /** GET /v1/admin/auth/session — права для скрытия кнопок (лента, collab). */
  adminSession: () => ["admin", "session"] as const,
  adminEmbed: {
    settings: () => ["admin", "embed", "settings"] as const,
    apiKeys: () => ["admin", "embed", "api-keys"] as const,
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
  rbac: {
    prefix: ["admin-rbac"] as const,
    catalog: (effectiveClinicId?: string | null) =>
      ["admin-rbac", "catalog", effectiveClinicId ?? "jwt"] as const,
    users: (effectiveClinicId?: string | null) =>
      ["admin-rbac", "users", effectiveClinicId ?? "jwt"] as const,
    policies: (effectiveClinicId?: string | null) =>
      ["admin-rbac", "policies", effectiveClinicId ?? "jwt"] as const,
    audit: (limit: number, effectiveClinicId?: string | null) =>
      ["admin-rbac", "audit", limit, effectiveClinicId ?? "jwt"] as const,
  },
  staffDirectory: {
    professionCategories: (clinicId: string | null) =>
      ["staff-directory", "profession-categories", clinicId] as const,
    admins: (clinicId: string | null) => ["staff-directory", "admins", clinicId] as const,
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
  adminDataExport: {
    summary: () => ["admin", "data-export", "summary"] as const,
  },
  adminRagKb: {
    documents: () => ["admin", "rag-kb", "documents"] as const,
    document: (id: string) => ["admin", "rag-kb", "document", id] as const,
  },
} as const;
