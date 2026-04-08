import { ROUTE_PATHS } from "@/routePaths";

/**
 * Безопасный path для редиректа после входа: только относительные пути зон приложения.
 */
export function safeAuthReturnTo(raw: string | null, fallback: string): string {
  if (!raw || typeof raw !== "string") return fallback;
  let decoded: string;
  try {
    decoded = decodeURIComponent(raw.trim());
  } catch {
    return fallback;
  }
  if (!decoded.startsWith("/") || decoded.startsWith("//")) return fallback;
  if (decoded.includes("://")) return fallback;
  if (
    decoded.startsWith("/admin") ||
    decoded.startsWith("/app") ||
    decoded.startsWith("/platform") ||
    decoded.startsWith("/c/")
  ) {
    return decoded;
  }
  return fallback;
}

export function defaultReturnToForTab(
  tab: "patient" | "clinic" | "founder",
): string {
  if (tab === "clinic") return ROUTE_PATHS.admin.dashboard;
  if (tab === "founder") return ROUTE_PATHS.platform.dashboard;
  return ROUTE_PATHS.patient.home;
}
