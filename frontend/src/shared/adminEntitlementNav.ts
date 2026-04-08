import type { AdminShellSegment } from "@/routePaths";
import { ROUTE_PATHS } from "@/routePaths";

/**
 * Пункты сайдбара: path → ключ опции (только когда `entitlement_enforced` в сессии).
 * Должно совпадать с роутерами, где стоит `require_entitlement` — см. ENTITLEMENT_ROUTER_INVENTORY.md.
 */
export const ADMIN_NAV_PATH_ENTITLEMENT_KEY: Record<string, string> = {
  [ROUTE_PATHS.admin.tasks]: "tasks.kanban",
  [ROUTE_PATHS.admin.recall]: "marketing.attribution",
  [ROUTE_PATHS.admin.marketing]: "marketing.attribution",
  [ROUTE_PATHS.admin.retention]: "retention.bundle",
  [ROUTE_PATHS.admin.sales]: "crm.pipeline",
  [ROUTE_PATHS.admin.embed]: "omni.embed.bundle",
  [ROUTE_PATHS.admin.ragKb]: "ai.rag.org_kb",
  [ROUTE_PATHS.admin.commerce]: "commerce.store_network",
};

const SEGMENT_ENTITLEMENT: Partial<Record<AdminShellSegment, string>> = {
  tasks: "tasks.kanban",
  recall: "marketing.attribution",
  marketing: "marketing.attribution",
  retention: "retention.bundle",
  sales: "crm.pipeline",
  embed: "omni.embed.bundle",
  "rag-kb": "ai.rag.org_kb",
  commerce: "commerce.store_network",
};

/** Сегменты админки, для которых до прихода `/admin/auth/session` нельзя решать redirect по entitlements. */
export function adminShellSegmentEntitlementKey(seg: AdminShellSegment): string | undefined {
  return SEGMENT_ENTITLEMENT[seg];
}

/** Блокировка прямого захода на `/admin/:seg` при SaaS-гейте. */
export function isAdminSegmentBlockedByEntitlements(
  segment: AdminShellSegment,
  entitlementEnforced: boolean,
  entitlementKeys: string[] | undefined,
): boolean {
  if (!entitlementEnforced || !entitlementKeys?.length) return false;
  const required = SEGMENT_ENTITLEMENT[segment];
  if (!required) return false;
  return !entitlementKeys.includes(required);
}
