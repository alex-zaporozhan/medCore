import type { AdminShellSegment } from "@/routePaths";

/**
 * Редакция сборки (коробка vs Enterprise) — см. `MASTER_PRODUCT_ROADMAP_2026`, `VITE_EDITION` в `.env.example`.
 * В коробке скрывается вкладка «Лояльность» на `/admin/loyalty`.
 */
export function isBoxEdition(): boolean {
  const e = import.meta.env.VITE_EDITION?.toLowerCase()?.trim();
  return e === "basic" || e === "box";
}

/**
 * Сегменты под `/admin/:seg`, недоступные в редакции Box (Smart Retention, CRM-лиды) — `ARCH_PHASE_06_OWNER_RBAC_2026` §7.
 */
export const BOX_DISALLOWED_ADMIN_SEGMENTS: readonly AdminShellSegment[] = [
  "retention",
  "sales",
] as const;

export function isAdminSegmentBlockedInBox(segment: AdminShellSegment): boolean {
  if (!isBoxEdition()) return false;
  return (BOX_DISALLOWED_ADMIN_SEGMENTS as readonly string[]).includes(segment);
}

/** Полные path для фильтра сайдбара (совпадают с `ROUTE_PATHS.admin.*`). */
export const BOX_HIDDEN_ADMIN_PATHS: readonly string[] =
  BOX_DISALLOWED_ADMIN_SEGMENTS.map((seg) => `/admin/${seg}`);
