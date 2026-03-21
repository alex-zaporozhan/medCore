import { matchPath } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";

/** Схлопывает trailing slash для сравнения с каноном (`/login` vs `/login/`). */
export function normalizePathname(pathname: string): string {
  if (pathname === "/") return "/";
  return pathname.replace(/\/+$/, "") || "/";
}

/** Совпадение с path-паттерном RR6 (например `/login`, `/admin/login`). */
export function matchesPatternPath(pathname: string, pattern: string): boolean {
  return Boolean(matchPath({ path: pattern, end: true }, normalizePathname(pathname)));
}

/** Пациентская страница входа (`/login`) — guard и `clearPatientAuth` в `client.ts`. */
export function isPatientLoginPath(pathname: string): boolean {
  return matchesPatternPath(pathname, ROUTE_PATHS.other.login);
}

/** Админская страница входа (`/admin/login`) — `AdminAuthGuard`. */
export function isAdminLoginPath(pathname: string): boolean {
  return matchesPatternPath(pathname, ROUTE_PATHS.admin.login);
}
