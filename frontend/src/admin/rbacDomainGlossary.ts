/**
 * Названия и пояснения доменов прав для экрана настроек доступа.
 * Домен в API вычисляется из кода права (префикс до первой «.» или «_») — группировка для навигации по каталогу.
 */

export type UiLocale = "ru" | "en";

export interface DomainGlossaryEntry {
  /** Короткое имя для списков (RU) */
  ruShort: string;
  /** Короткое имя (EN) */
  enShort: string;
  /** Пояснение: что это за группа и зачем она в интерфейсе (RU) */
  ruGentle: string;
  enGentle: string;
  /** Что обычно лежит внутри (RU) */
  ruInside: string;
  enInside: string;
}

const FALLBACK: DomainGlossaryEntry = {
  ruShort: "Служебная группа",
  enShort: "Technical group",
  ruGentle:
    "Так система назвала группу прав по первой части кода. Само по себе имя не описывает ваш отдел — смотрите описание у каждого права в списке.",
  enGentle:
    "The system groups permissions by the first segment of the code. The label is not your org chart—read each permission’s description.",
  ruInside: "Зависит от конкретных прав в каталоге — откройте список и читайте подпись к каждому пункту.",
  enInside: "Depends on the permissions in the catalog—open the list and read each item’s description.",
};

/** Известные домены из rbac_matrix и типичных кодов прав */
const DOMAIN_GLOSSARY: Record<string, DomainGlossaryEntry> = {
  all: {
    ruShort: "Все домены",
    enShort: "All domains",
    ruGentle: "Показать все права без фильтра по группе.",
    enGentle: "Show all permissions without filtering by group.",
    ruInside: "Все доступные в каталоге права.",
    enInside: "Every permission in the catalog.",
  },
  general: {
    ruShort: "Общие права",
    enShort: "General",
    ruGentle:
      "Права без точки и подчёркивания в коде. Их мало; смысл всегда в описании строки.",
    enGentle:
      "Permissions whose codes have no dot or underscore. There are few; meaning is always in the row description.",
    ruInside: "Единичные общесистемные разрешения — смотрите текст в списке.",
    enInside: "Rare global flags—read the label next to each code.",
  },
  view: {
    ruShort: "Просмотр (по префиксу кода)",
    enShort: "View (code prefix)",
    ruGentle:
      "Это не «отдел просмотра», а удобная группировка: в коде права стоит префикс «view_». Внутри могут быть разные зоны бизнеса — дашборд, отчёты, финансы, CRM. Чтобы понять, на что именно вы даёте доступ, читайте описание у каждой строки.",
    enGentle:
      "Not a department—permissions whose codes start with `view_`. They span different business areas; read each permission’s description.",
    ruInside:
      "Обычно: просмотр дашборда, отчётов, финансов, зарплаты, склада, CRM, задач, лояльности, форм, маркетинга, AI-настроек, коллаборации персонала и др. — всё с префиксом «view_».",
    enInside:
      "Typically: dashboard, reports, finance, payroll, inventory, CRM, tasks, loyalty, forms, marketing, AI settings, staff collab, etc.—anything with the `view_` prefix.",
  },
  manage: {
    ruShort: "Управление (по префиксу кода)",
    enShort: "Manage (code prefix)",
    ruGentle:
      "Группа прав с префиксом «manage_» — обычно это создание и изменение данных, а не только просмотр. Название домена не заменяет чтение конкретной строки: там написано, что именно можно менять.",
    enGentle:
      "Permissions with the `manage_` prefix—usually create/update, not just read. The domain name does not replace the per-row description.",
    ruInside:
      "Финансы, зарплата, склад, CRM, задачи, лояльность, формы, маркетинг, AI-настройки, коллаборация — в зависимости от того, какие «manage_*» есть в каталоге.",
    enInside:
      "Finance, payroll, inventory, CRM, tasks, loyalty, forms, marketing, AI settings, collab—whatever `manage_*` codes exist in your catalog.",
  },
  run: {
    ruShort: "Запуск операций (по префиксу кода)",
    enShort: "Run / execute (code prefix)",
    ruGentle:
      "Права, в коде которых первая часть — «run_». Обычно это активное действие «выполнить» (например запуск кампании), а не просмотр отчёта.",
    enGentle:
      "Permissions whose codes start with `run_`—typically an active “execute” action (e.g. launch a campaign), not viewing a report.",
    ruInside: "Например: run_loyalty_campaigns.",
    enInside: "E.g. `run_loyalty_campaigns`.",
  },
  assign: {
    ruShort: "Назначение задач",
    enShort: "Task assignment",
    ruGentle:
      "Права на делегирование задач другим людям (отдельно от «просто смотреть» или «редактировать свои»).",
    enGentle: "Permissions to assign work to others, separate from view/edit alone.",
    ruInside: "Например: назначение задач коллегам.",
    enInside: "E.g. assigning tasks to teammates.",
  },
  invite: {
    ruShort: "Приглашения в календарь",
    enShort: "Calendar invites",
    ruGentle:
      "Кто может приглашать участников на события общего календаря (совещания), а не только вести личные записи.",
    enGentle: "Who can invite participants to shared calendar events vs personal-only.",
    ruInside: "Приглашения на события календаря персонала.",
    enInside: "Invites for staff calendar events.",
  },
  export: {
    ruShort: "Экспорт данных",
    enShort: "Export",
    ruGentle: "Выгрузка данных (например форм и подписей) в файл или внешнюю систему.",
    enGentle: "Exporting data (e.g. forms/signatures) to files or external tools.",
    ruInside: "Экспорт форм и подписей пациента и схожие операции.",
    enInside: "Export of forms/patient signatures and similar.",
  },
  patients: {
    ruShort: "Пациенты и ПДн",
    enShort: "Patients & personal data",
    ruGentle:
      "Доступ к персональным данным пациентов: карточки, контакты, списки. Это чувствительная зона — выдавайте только тем, кому это нужно по работе.",
    enGentle:
      "Access to patient personal data—cards, contacts, lists. Sensitive—grant only where legally and operationally required.",
    ruInside:
      "Просмотр и изменение ПДн в рамках кода прав с доменом «patients» (например patients.pii.read).",
    enInside: "PII-related permissions such as `patients.pii.read`—see exact wording in the list.",
  },
  tasks: {
    ruShort: "Задачи (детальные операции)",
    enShort: "Tasks (detailed)",
    ruGentle:
      "Права с кодом «tasks.…» — тонкая настройка: смена статуса, снятие блокировки, массовые действия, приоритет. Это про операционную дисциплину, не про «видеть список».",
    enGentle:
      "Codes like `tasks.*`—status changes, unblock, bulk, priority. Operational detail beyond merely viewing the list.",
    ruInside: "Статусы, разблокировка, массовая смена, переприоритизация и т.п.",
    enInside: "Status, unblock, bulk updates, reprioritize, etc.",
  },
  erp: {
    ruShort: "ERP и отчёты владельца",
    enShort: "ERP & owner reports",
    ruGentle:
      "Расширенные отчёты для владельца: выручка, зарплата, склад, сводные витрины. Обычно это стратегическая картина бизнеса.",
    enGentle: "Owner-level ERP-style reports—revenue, payroll, inventory, rollups.",
    ruInside: "Например: erp.owner_reports.read — читайте описание в списке.",
    enInside: "E.g. `erp.owner_reports.read`—see the catalog description.",
  },
  attribution: {
    ruShort: "Атрибуция и ROI",
    enShort: "Attribution & ROI",
    ruGentle:
      "Отчёты по источникам лидов и окупаемости маркетинга. Помогает понимать, откуда приходят пациенты.",
    enGentle: "Lead source and marketing ROI reporting.",
    ruInside: "Чтение отчётов атрибуции (например attribution.reports.read).",
    enInside: "Reading attribution reports (e.g. `attribution.reports.read`).",
  },
  booking: {
    ruShort: "Запись и AI у приёма",
    enShort: "Booking & AI tools",
    ruGentle:
      "Инструменты онлайн-записи и AI-помощники для слотов, переносов и отмен — чтобы администраторы быстрее вели расписание.",
    enGentle: "Online booking helpers and AI for slots, moves, cancellations.",
    ruInside: "Например: booking.ai_tools.use.",
    enInside: "E.g. `booking.ai_tools.use`.",
  },
  ai: {
    ruShort: "Искусственный интеллект",
    enShort: "Artificial intelligence",
    ruGentle:
      "Настройки AI и фоновые AI-процессы (например анализ внимания и генерация задач). Отдельно от «обычных» экранов клиники.",
    enGentle: "AI settings and background AI flows (e.g. attention analysis, task generation).",
    ruInside: "Например: ai.tasks.run и связанные коды.",
    enInside: "E.g. `ai.tasks.run` and related codes.",
  },
  omni: {
    ruShort: "Омниканал",
    enShort: "Omnichannel inbox",
    ruGentle:
      "Единая линия диалогов с пациентами: назначение ответственных, статусы, шаблоны быстрых ответов.",
    enGentle: "Unified patient conversations—ownership, statuses, quick replies.",
    ruInside: "Например: omni.inbox.manage.",
    enInside: "E.g. `omni.inbox.manage`.",
  },
  leads: {
    ruShort: "Лиды (лог)",
    enShort: "Leads (log)",
    ruGentle:
      "Права на страницу логов обращений из omni‑чата: кто может смотреть историю закрытых диалогов и исходы (записался/не записался).",
    enGentle:
      "Permissions for the omni-chat lead log page: who can view resolved conversation history and outcomes.",
    ruInside: "Например: leads.log.view.",
    enInside: "E.g. `leads.log.view`.",
  },
  rbac: {
    ruShort: "Управление доступами",
    enShort: "Access control",
    ruGentle:
      "Кто может менять роли, персональные права и политики — то есть этот экран и связанные настройки безопасности.",
    enGentle: "Who can change roles, overrides, and policies—this screen and related security.",
    ruInside: "Например: rbac.manage.",
    enInside: "E.g. `rbac.manage`.",
  },
  staff: {
    ruShort: "Сотрудники (HR)",
    enShort: "Staff (HR)",
    ruGentle: "Кадровые данные и операции по персоналу клиники, если такие коды есть в каталоге.",
    enGentle: "HR-style staff data if such codes exist in your catalog.",
    ruInside: "Зависит от фактических прав с доменом staff.",
    enInside: "Depends on actual `staff.*` permissions.",
  },
  appointments: {
    ruShort: "Записи и приём",
    enShort: "Appointments",
    ruGentle: "Расписание приёма, визиты пациентов — если в каталоге есть права с таким доменом.",
    enGentle: "Appointments and visits if your catalog uses this domain.",
    ruInside: "Смотрите конкретные строки в списке.",
    enInside: "See each row in the list.",
  },
  schedule: {
    ruShort: "График и слоты",
    enShort: "Schedule & slots",
    ruGentle: "Настройка рабочего графика, слотов и ресурсов кресла/кабинета.",
    enGentle: "Working hours, slots, chair/room resources.",
    ruInside: "Права с доменом schedule в вашем каталоге.",
    enInside: "Permissions with the `schedule` domain in your catalog.",
  },
  patient: {
    ruShort: "Пациенты",
    enShort: "Patients",
    ruGentle: "Синонимичная группировка к «patients» — ориентируйтесь на описание строки.",
    enGentle: "Variant grouping related to patients—read the row description.",
    ruInside: "См. домен patients при сомнениях.",
    enInside: "Cross-check with `patients` domain.",
  },
  finance: {
    ruShort: "Финансы",
    enShort: "Finance",
    ruGentle: "Доходы, счета, платежи, финансовая аналитика — если коды сгруппированы так.",
    enGentle: "Revenue, billing, payments—if your codes use this domain.",
    ruInside: "Зависит от каталога.",
    enInside: "Catalog-dependent.",
  },
  billing: {
    ruShort: "Биллинг",
    enShort: "Billing",
    ruGentle: "Выставление счетов и связанные операции.",
    enGentle: "Invoicing and related operations.",
    ruInside: "Смотрите описания прав.",
    enInside: "Read each permission description.",
  },
  payments: {
    ruShort: "Платежи",
    enShort: "Payments",
    ruGentle: "Приём и учёт платежей.",
    enGentle: "Payment capture and accounting.",
    ruInside: "Смотрите описания прав.",
    enInside: "Read each permission description.",
  },
  crm: {
    ruShort: "CRM и лиды",
    enShort: "CRM & leads",
    ruGentle: "Воронка, лиды, стадии, коммуникации до записи.",
    enGentle: "Pipeline, leads, stages, pre-appointment comms.",
    ruInside: "Права view_crm, manage_crm и аналоги — в списке с описанием.",
    enInside: "`view_crm`, `manage_crm`, etc.—see catalog.",
  },
  notifications: {
    ruShort: "Уведомления",
    enShort: "Notifications",
    ruGentle: "SMS, push, email и прочие уведомления пациентам и персоналу.",
    enGentle: "SMS, push, email to patients and staff.",
    ruInside: "По мере появления кодов в каталоге.",
    enInside: "As codes appear in the catalog.",
  },
  reports: {
    ruShort: "Отчёты",
    enShort: "Reports",
    ruGentle: "Сводки и выгрузки по работе клиники.",
    enGentle: "Operational and management reports.",
    ruInside: "Например view_reports и др.",
    enInside: "E.g. `view_reports` and others.",
  },
  analytics: {
    ruShort: "Аналитика",
    enShort: "Analytics",
    ruGentle: "Показатели и дашборды для анализа работы.",
    enGentle: "Metrics and dashboards.",
    ruInside: "Смотрите конкретные коды.",
    enInside: "See specific codes.",
  },
  loyalty: {
    ruShort: "Лояльность",
    enShort: "Loyalty",
    ruGentle: "Программы лояльности, бонусы, кампании удержания.",
    enGentle: "Loyalty programs, bonuses, retention campaigns.",
    ruInside: "Просмотр и управление программами, кампании.",
    enInside: "View/manage programs and campaigns.",
  },
  inventory: {
    ruShort: "Склад",
    enShort: "Inventory",
    ruGentle: "Материалы, расходники, остатки.",
    enGentle: "Supplies and stock levels.",
    ruInside: "view_inventory, manage_inventory и т.д.",
    enInside: "`view_inventory`, `manage_inventory`, etc.",
  },
  marketing: {
    ruShort: "Маркетинг",
    enShort: "Marketing",
    ruGentle: "Рекламные кампании и маркетинговая аналитика.",
    enGentle: "Campaigns and marketing analytics.",
    ruInside: "view_marketing_analytics, manage_marketing_campaigns и др.",
    enInside: "`view_marketing_analytics`, `manage_marketing_campaigns`, etc.",
  },
  integrations: {
    ruShort: "Интеграции",
    enShort: "Integrations",
    ruGentle: "Подключение внешних сервисов (телефония, мессенджеры, обмен данными).",
    enGentle: "External services—telephony, messengers, data exchange.",
    ruInside: "По мере кодов в каталоге.",
    enInside: "As present in the catalog.",
  },
  admin: {
    ruShort: "Администрирование",
    enShort: "Administration",
    ruGentle: "Системные настройки клиники, не относящиеся к одному пациенту.",
    enGentle: "Clinic-wide settings not tied to a single patient.",
    ruInside: "Зависит от каталога.",
    enInside: "Catalog-dependent.",
  },
};

export function getDomainGlossary(domain: string): DomainGlossaryEntry {
  const key = domain.trim().toLowerCase();
  return DOMAIN_GLOSSARY[key] ?? {
    ...FALLBACK,
    ruShort: `Группа «${domain}»`,
    enShort: `Group “${domain}”`,
  };
}

/** Основная подпись домена в списке (RU или EN). */
export function getDomainPrimaryLabel(domain: string, locale: UiLocale): string {
  const g = getDomainGlossary(domain);
  if (domain === "all") return g.ruShort;
  return locale === "ru" ? g.ruShort : g.enShort;
}

/**
 * Строка для поля Select (без HTML): сначала смысловое имя, в конце — технический ключ группы (менее заметен визуально через renderOption).
 */
export function getDomainPlainSelectLabel(domain: string, locale: UiLocale): string {
  const primary = getDomainPrimaryLabel(domain, locale);
  if (domain === "all") return primary;
  return `${primary} · ${domain}`;
}
