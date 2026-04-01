/**
 * Канонические публичные path по зонам — техпаспорт §2 (`ARCH_FRONTEND_TECH_PASSPORT_DENTAL_BOOKING.md`).
 * Сегменты `ADMIN_SHELL_ROUTE_SEGMENTS` / `PATIENT_APP_ROUTE_SEGMENTS` — единый источник для `App.tsx` и списка path.
 */

export const ROUTE_PATHS = {
  marketing: {
    landing: "/",
  },
  admin: {
    login: "/admin/login",
    dashboard: "/admin",
    /** Внутренний staff/collab чат клиники (не омниканальный инбокс пациентов). */
    staffChat: "/admin/staff-chat",
    /** Личный кабинет сотрудника: фото + «о себе». */
    me: "/admin/me",
    staffCalendar: "/admin/calendar",
    knowledge: "/admin/knowledge",
    clinics: "/admin/clinics",
    services: "/admin/services",
    schedule: "/admin/schedule",
    tasks: "/admin/tasks",
    leadsLog: "/admin/leads-log",
    bookings: "/admin/bookings",
    prepayment: "/admin/prepayment",
    waitlist: "/admin/waitlist",
    recall: "/admin/recall",
    marketing: "/admin/marketing",
    retention: "/admin/retention",
    sales: "/admin/sales",
    attention: "/admin/attention",
    reports: "/admin/reports",
    finance: "/admin/finance",
    loyalty: "/admin/loyalty",
    forms: "/admin/forms",
    doctors: "/admin/doctors",
    doctorSchedule: "/admin/doctor-schedule",
    patients: "/admin/patients",
    /** Единый омниканальный инбокс с пациентами (внешние каналы). Не путать с `staffChat` — внутренний чат персонала. */
    omniChat: "/admin/omni-chat",
    omniChannels: "/admin/omni-channels",
    omniAiSettings: "/admin/omni-ai-settings",
    channels: "/admin/channels",
    integrations: "/admin/integrations",
    omniVault: "/admin/omni-vault",
    styling: "/admin/styling",
    stickers: "/admin/stickers",
    settings: "/admin/settings",
    administrators: "/admin/administrators",
    paymentGateway: "/admin/payment-gateway",
    clientReference: "/admin/client-reference",
    discounts: "/admin/discounts",
    notificationPolicy: "/admin/notification-policy",
    agreements: "/admin/agreements",
    rightsPolicies: "/admin/rights-policies",
  },
  patient: {
    home: "/app",
    feed: "/app/feed",
    booking: "/app/booking",
    history: "/app/history",
    loyalty: "/app/loyalty",
    forms: "/app/forms",
    chat: "/app/chat",
    profile: "/app/profile",
  },
  other: {
    login: "/login",
    oauthResult: "/oauth/result",
    bookingSuccess: "/booking/success",
  },
} as const;

/**
 * Сегменты под `/admin` + `AdminLayout` (как `path="…"` в `App.tsx`), порядок как в дереве маршрутов.
 * Должны совпадать с ключами `ADMIN_SHELL_PAGE_BY_SEGMENT` в `App.tsx`.
 */
export const ADMIN_SHELL_ROUTE_SEGMENTS = [
  "staff-chat",
  "me",
  "calendar",
  "knowledge",
  "clinics",
  "services",
  "schedule",
  "tasks",
  "leads-log",
  "bookings",
  "prepayment",
  "waitlist",
  "recall",
  "marketing",
  "retention",
  "sales",
  "attention",
  "reports",
  "finance",
  "loyalty",
  "forms",
  "doctors",
  "doctor-schedule",
  "patients",
  "omni-chat",
  "omni-channels",
  "omni-ai-settings",
  "channels",
  "integrations",
  "omni-vault",
  "styling",
  "stickers",
  "settings",
  "administrators",
  "payment-gateway",
  "client-reference",
  "discounts",
  "notification-policy",
  "agreements",
  "rights-policies",
] as const;

export type AdminShellSegment = (typeof ADMIN_SHELL_ROUTE_SEGMENTS)[number];

/** Сегменты под `/app` кроме index (`/` → HomePage). */
export const PATIENT_APP_ROUTE_SEGMENTS = [
  "feed",
  "booking",
  "history",
  "loyalty",
  "forms",
  "chat",
  "profile",
] as const;

export type PatientAppSegment = (typeof PATIENT_APP_ROUTE_SEGMENTS)[number];

/** Сборка полного списка публичных path §2 (для тестов и приёмки). */
export function buildDerivedAllTechPassportPaths(): readonly string[] {
  return [
    ROUTE_PATHS.marketing.landing,
    ROUTE_PATHS.admin.login,
    ROUTE_PATHS.admin.dashboard,
    ...ADMIN_SHELL_ROUTE_SEGMENTS.map((s) => `/admin/${s}`),
    ROUTE_PATHS.patient.home,
    ...PATIENT_APP_ROUTE_SEGMENTS.map((s) => `/app/${s}`),
    ROUTE_PATHS.other.login,
    ROUTE_PATHS.other.oauthResult,
    ROUTE_PATHS.other.bookingSuccess,
  ];
}

/** Все path из §2 для проверок (уникальность, паритет с `ROUTE_PATHS`). */
export const ALL_TECH_PASSPORT_PATHS: readonly string[] = buildDerivedAllTechPassportPaths();
