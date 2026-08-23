/**
 * Overlay landing price labels from the live public catalog.
 * Static LANDING_MONTHLY_PRICE_LABEL stays the paint-ready fallback (SSG-safe).
 */
import { API_BASE, newOutboundRequestId } from "@/api/client";
import {
  formatCatalogUsdLabel,
  isMarketingPlanSlug,
  LANDING_MONTHLY_PRICE_LABEL,
  type MarketingPlanSlug,
} from "@/marketing/marketingPublicPlans";
import { useEffect, useState } from "react";

export function usePublicCatalogPriceLabels(): Record<MarketingPlanSlug, string> {
  const [labels, setLabels] = useState<Record<MarketingPlanSlug, string>>(LANDING_MONTHLY_PRICE_LABEL);

  useEffect(() => {
    const abort = new AbortController();
    const headers = { "X-Request-Id": newOutboundRequestId() };

    void (async () => {
      try {
        const r = await fetch(`${API_BASE}/v1/public/platform/catalog/plans`, {
          headers,
          signal: abort.signal,
        });
        if (!r.ok) return;
        const data: unknown = await r.json();
        if (abort.signal.aborted || !Array.isArray(data)) return;
        const next: Record<MarketingPlanSlug, string> = { ...LANDING_MONTHLY_PRICE_LABEL };
        for (const row of data) {
          if (!row || typeof row !== "object") continue;
          const rec = row as { slug?: unknown; price_monthly_rub?: unknown };
          const slug = typeof rec.slug === "string" ? rec.slug : "";
          if (!isMarketingPlanSlug(slug)) continue;
          const formatted = formatCatalogUsdLabel(
            typeof rec.price_monthly_rub === "string" || typeof rec.price_monthly_rub === "number"
              ? rec.price_monthly_rub
              : null,
          );
          if (formatted) next[slug] = formatted;
        }
        setLabels(next);
      } catch (err: unknown) {
        if (abort.signal.aborted || (err instanceof DOMException && err.name === "AbortError")) return;
        console.error("landing_catalog_prices_overlay_failed", {
          message: err instanceof Error ? err.message : String(err),
        });
      }
    })();

    return () => {
      abort.abort();
    };
  }, []);

  return labels;
}
