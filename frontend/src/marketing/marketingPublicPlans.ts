/**
 * Единый маркетинговый слой для публичных тарифов (лендинг + /pricing).
 * Slug’и совпадают с `platform_catalog_plans.slug` после миграции каталога.
 */
export type MarketingPlanSlug = "start" | "growth" | "business_os";

export type PublicPlanMarketing = {
  slug: MarketingPlanSlug;
  /** Короткий заголовок карточки (совпадает с брендом тарифа). */
  headline: string;
  /** Подзаголовок / позиционирование. */
  badge: string;
  /** Буллеты для витрины (не технические entitlement_key). */
  bullets: readonly string[];
  /** Выделение на витрине (как «хит продаж»). */
  featured?: boolean;
};

export const PUBLIC_PLAN_MARKETING: Record<MarketingPlanSlug, PublicPlanMarketing> = {
  start: {
    slug: "start",
    headline: "Базовый",
    badge: "База для моно-бизнеса",
    bullets: [
      "1 филиал, до 5 сотрудников",
      "CRM (канбан), онлайн-запись, базовое расписание",
      "PWA-приложение для клиентов",
      "Единый чат (без ИИ)",
    ],
    featured: false,
  },
  growth: {
    slug: "growth",
    headline: "Развитие",
    badge: "Хит продаж для активных",
    bullets: [
      "До 3 филиалов, до 20 сотрудников",
      "ИИ-ассистент в чатах: черновики и маршрутизация",
      "Учёт и финансы: кассы, предоплаты, приём платежей",
      "Скидки, абонементы, рассылки",
    ],
    featured: true,
  },
  business_os: {
    slug: "business_os",
    headline: "Корпоративный",
    badge: "Расширенные возможности",
    bullets: [
      "Сеть до 10 филиалов",
      "Внутренний чат команды и база знаний с поддержкой ИИ",
      "Задачи и поручения: сроки, ответственные и сценарии на базе ИИ",
      "Склад, аналитика маркетинга, расчёт заработной платы",
    ],
    featured: false,
  },
};

/** Порядок колонок на лендинге и в каталоге. */
export const MARKETING_PLAN_ORDER: readonly MarketingPlanSlug[] = ["start", "growth", "business_os"];

/** Зафиксированные цены витрины (согласованы с `platform_catalog_plans` в миграции). */
export const LANDING_MONTHLY_PRICE_LABEL: Record<MarketingPlanSlug, string> = {
  start: "2 900 ₽",
  growth: "5 900 ₽",
  business_os: "14 900 ₽",
};

export function landingPricingCardsForUi() {
  return MARKETING_PLAN_ORDER.map((slug) => {
    const m = PUBLIC_PLAN_MARKETING[slug];
    return {
      slug,
      name: m.headline,
      badge: m.badge,
      price: LANDING_MONTHLY_PRICE_LABEL[slug],
      period: "/ мес",
      features: [...m.bullets],
      featured: Boolean(m.featured),
    };
  });
}

export const ENTERPRISE_PLAN_MARKETING = {
  headline: "Индивидуальное внедрение",
  priceLabel: "от 30 000 ₽",
  priceHint: "индивидуально",
  bullets: [
    "Безлимит по филиалам и сценариям",
    "Собственный бренд в приложении для клиентов",
    "Выделенный сервер или развёртывание на площадке заказчика",
  ],
} as const;

export function marketingOverlayForSlug(slug: string | null | undefined): PublicPlanMarketing | null {
  if (!slug) return null;
  return PUBLIC_PLAN_MARKETING[slug as MarketingPlanSlug] ?? null;
}

/** Число из API (`2900.00`) → «2 900» для карточки. */
export function formatMonthlyRubLabel(priceMonthlyRub: string | null | undefined): string | null {
  if (priceMonthlyRub == null || priceMonthlyRub === "") return null;
  const n = Number.parseFloat(String(priceMonthlyRub).replace(/\s/g, "").replace(",", "."));
  if (!Number.isFinite(n)) return null;
  return `${Math.round(n).toLocaleString("ru-RU")} ₽`;
}

/** Slug → порядок карточек; неизвестные slug — в конце по алфавиту. */
export function sortPublicPlanRowsByMarketingOrder<T extends { slug: string }>(rows: T[]): T[] {
  const order = new Map<string, number>(MARKETING_PLAN_ORDER.map((s, i) => [s, i]));
  return [...rows].sort((a, b) => {
    const ia = order.get(a.slug) ?? 1000;
    const ib = order.get(b.slug) ?? 1000;
    if (ia !== ib) return ia - ib;
    return a.slug.localeCompare(b.slug);
  });
}
