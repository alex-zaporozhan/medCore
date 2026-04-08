import type { AdminShellSegment } from "@/routePaths";

/**
 * Редакция сборки (коробка vs Enterprise): `VITE_EDITION` в `.env.example`.
 * В коробке скрыты сегменты `sales` и `retention` (см. `BOX_DISALLOWED_ADMIN_SEGMENTS`; серверный гейт — env `EDITION` на бэкенде).
 */
export function isBoxEdition(): boolean {
  const e = import.meta.env.VITE_EDITION?.toLowerCase()?.trim();
  return e === "basic" || e === "box";
}

/**
 * Сегменты под `/admin/:seg`, недоступные в редакции Box (Smart Retention, CRM-лиды).
 * См. `VITE_EDITION` в `.env.example` и `src/core/edition.py` на бэкенде.
 */
export const BOX_DISALLOWED_ADMIN_SEGMENTS: readonly AdminShellSegment[] = [
  "retention",
  "sales",
  "embed",
  "rag-kb",
  "commerce",
] as const;

export function isAdminSegmentBlockedInBox(segment: AdminShellSegment): boolean {
  if (!isBoxEdition()) return false;
  return (BOX_DISALLOWED_ADMIN_SEGMENTS as readonly string[]).includes(segment);
}

/** Полные path для фильтра сайдбара (совпадают с `ROUTE_PATHS.admin.*`). */
export const BOX_HIDDEN_ADMIN_PATHS: readonly string[] =
  BOX_DISALLOWED_ADMIN_SEGMENTS.map((seg) => `/admin/${seg}`);
