import { matchPath } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";

/** Вход пациента по публичному slug клиники: `/c/{slug}/sign-in`. */
export function isClinicScopedPatientSignInPath(pathname: string): boolean {
  return Boolean(
    matchPath({ path: "/c/:clinicSlug/sign-in", end: true }, normalizePathname(pathname)),
  );
}

/** Схлопывает trailing slash для сравнения с каноном (`/login` vs `/login/`). */
export function normalizePathname(pathname: string): string {
  if (pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

/** Совпадение с path-паттерном RR6 (например `/login`, `/admin/login`). */
export function matchesPatternPath(pathname: string, pattern: string): boolean {
  return Boolean(matchPath({ path: pattern, end: true }, normalizePathname(pathname)));
}

/** Страницы входа пациента: legacy `/login` (редирект), витрина `/c/:slug/sign-in`. Глобального `/sign-in` больше нет. */
export function isPatientLoginPath(pathname: string): boolean {
  return (
    matchesPatternPath(pathname, ROUTE_PATHS.other.login) ||
    isClinicScopedPatientSignInPath(pathname)
  );
}

/** Админская страница входа (`/admin/login`) — `AdminAuthGuard`. */
export function isAdminLoginPath(pathname: string): boolean {
  return matchesPatternPath(pathname, ROUTE_PATHS.admin.login);
}
