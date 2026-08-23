/**
 * Public plan slugs, featured flags, and USD list-price labels.
 * Visible copy lives in the `marketing` i18n namespace (not this file).
 */
import { tNs } from "@/i18n";

export type MarketingPlanSlug = "start" | "growth" | "business_os";

export type PublicPlanMarketingMeta = {
  slug: MarketingPlanSlug;
  featured?: boolean;
};

export const PUBLIC_PLAN_MARKETING: Record<MarketingPlanSlug, PublicPlanMarketingMeta> = {
  start: { slug: "start", featured: false },
  growth: { slug: "growth", featured: true },
  business_os: { slug: "business_os", featured: false },
};

/** Column order on the landing and in the catalog. */
export const MARKETING_PLAN_ORDER: readonly MarketingPlanSlug[] = ["start", "growth", "business_os"];

/** Showcase monthly prices (aligned with `platform_catalog_plans` list amounts). */
export const LANDING_MONTHLY_PRICE_LABEL: Record<MarketingPlanSlug, string> = {
  start: "$20",
  growth: "$100",
  business_os: "$200",
};

export function isMarketingPlanSlug(slug: string): slug is MarketingPlanSlug {
  return slug === "start" || slug === "growth" || slug === "business_os";
}

export function marketingOverlayForSlug(slug: string | null | undefined): PublicPlanMarketingMeta | null {
  if (!slug || !isMarketingPlanSlug(slug)) return null;
  return PUBLIC_PLAN_MARKETING[slug];
}

export function marketingPlanCopy(slug: MarketingPlanSlug): {
  headline: string;
  badge: string;
  bullets: string[];
} {
  return {
    headline: tNs("marketing", `plans.${slug}.headline`),
    badge: tNs("marketing", `plans.${slug}.badge`),
    bullets: [0, 1, 2, 3].map((i) => tNs("marketing", `plans.${slug}.bullets.${i}`)),
  };
}

export function parseCatalogAmount(s: string | number | null | undefined): number | null {
  if (s == null || s === "") return null;
  if (typeof s === "number") return Number.isFinite(s) ? s : null;
  const n = Number.parseFloat(String(s).replace(/\s/g, "").replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

/** Number from API (`20.00`) → `$20` for the card. Public catalog is USD. */
export function formatCatalogUsdLabel(amount: string | number | null | undefined): string | null {
  const n = parseCatalogAmount(amount);
  if (n == null) return null;
  const isInt = Math.abs(n - Math.round(n)) < 1e-9;
  const body = isInt
    ? String(Math.round(n))
    : n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return `$${body}`;
}

/** Slug → card order; unknown slugs last, A–Z. */
export function sortPublicPlanRowsByMarketingOrder<T extends { slug: string }>(rows: T[]): T[] {
  const order = new Map<string, number>(MARKETING_PLAN_ORDER.map((s, i) => [s, i]));
  return [...rows].sort((a, b) => {
    const ia = order.get(a.slug) ?? 1000;
    const ib = order.get(b.slug) ?? 1000;
    if (ia !== ib) return ia - ib;
    return a.slug.localeCompare(b.slug);
  });
}
