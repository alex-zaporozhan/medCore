/**
 * Канонические публичные path по зонам. Сегменты `ADMIN_SHELL_ROUTE_SEGMENTS` / `PATIENT_APP_ROUTE_SEGMENTS`
 * — единый источник для `App.tsx` и списка path (см. также `buildDerivedPublicAppPaths`).
 */

export const ROUTE_PATHS = {
  marketing: {
    landing: "/",
    /** Публичная демо-заглушка до запуска песочницы. */
    sandbox: "/sandbox",
    /** Публичная витрина тарифов (каталог + checkout). */
    pricing: "/pricing",
    /** Регистрация клиники: согласия PII + checkout (FE-E1). */
    signup: "/signup",
    /** After YooKassa provision: set owner password from email token. */
    ownerInviteAccept: "/signup/owner-invite",
    legalPrivacy: "/legal/privacy",
    legalTerms: "/legal/terms",
  },
  /** Кабинет Основателя платформы (JWT platform_founder), отдельно от /admin. */
  platform: {
    login: "/platform/login",
    /** Шаг 2 входа основателя (TOTP), после проверки email/пароля. */
    loginMfa: "/platform/login/mfa",
    dashboard: "/platform/dashboard",
    provisionQueue: "/platform/provision-queue",
    /** Заявки на индивидуальное внедрение с публичного сайта. */
    leads: "/platform/leads",
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
    /** Магазин / Commerce (Фаза 4, entitlement commerce.store_network). */
    commerce: "/admin/commerce",
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
    /** API keys и webhook inbox для встраивания (§24, entitlement omni.embed.bundle). */
    embed: "/admin/embed",
    /** Per-org RAG KB (§24.3, entitlement ai.rag.org_kb). */
    ragKb: "/admin/rag-kb",
    /** Экспорт / offboarding для владельца (Phase 1e-F3). */
    dataExport: "/admin/data-export",
    omniVault: "/admin/omni-vault",
    styling: "/admin/styling",
    stickers: "/admin/stickers",
    settings: "/admin/settings",
    /** Подписка SaaS: возможности org + витрина тарифов (апгрейд — без автоного checkout до контура owner). */
    subscription: "/admin/subscription",
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
    store: "/app/store",
  },
  other: {
    /** Legacy: редирект на `/admin/login`, `/platform/login` или главную (пациент). */
    signIn: "/sign-in",
    /** Legacy `/login` → главная с подсказкой для пациента. */
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
  "commerce",
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
  "embed",
  "rag-kb",
  "data-export",
  "omni-vault",
  "styling",
  "stickers",
  "settings",
  "subscription",
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
  "store",
] as const;

export type PatientAppSegment = (typeof PATIENT_APP_ROUTE_SEGMENTS)[number];

/**
 * Фиксированный набор path для регрессионных тестов и проверки уникальности URL.
 * Не включает шаблоны с параметрами (например `/:clinicSlug/doctors/:doctorSlug`) — заданы в `App.tsx` отдельным маршрутом.
 * Канон зон и таблица админ-сегментов — тот же документ §5.2–5.3.
 */
export function buildDerivedPublicAppPaths(): readonly string[] {
  return [
    ROUTE_PATHS.marketing.landing,
    ROUTE_PATHS.marketing.sandbox,
    ROUTE_PATHS.marketing.pricing,
    ROUTE_PATHS.marketing.signup,
    ROUTE_PATHS.marketing.ownerInviteAccept,
    ROUTE_PATHS.marketing.legalPrivacy,
    ROUTE_PATHS.marketing.legalTerms,
    ROUTE_PATHS.platform.login,
    ROUTE_PATHS.platform.loginMfa,
    ROUTE_PATHS.platform.dashboard,
    ROUTE_PATHS.platform.provisionQueue,
    ROUTE_PATHS.platform.leads,
    ROUTE_PATHS.other.signIn,
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

/** Все публичные path для проверок (уникальность, паритет с `ROUTE_PATHS`). */
export const ALL_PUBLIC_APP_PATHS: readonly string[] = buildDerivedPublicAppPaths();

/** Публичная страница `/login`: подсказки для пациента через query `patientEntry`. */
export function patientPublicLoginSearch(patientEntry: string): string {
  return `?${new URLSearchParams({ patientEntry }).toString()}`;
}
