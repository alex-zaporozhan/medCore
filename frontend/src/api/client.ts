/**
 * Thin API client: base URL /api, Bearer token, error parsing.
 * No caching or business logic — transport only.
 * On 401 for patient session (см. `shouldClearPatientSessionOn401`): очистка пациентских ключей и редирект на главную или `/c/…/sign-in`.
 *
 * Не менять префикс API, семантику `API_STORAGE_KEYS` и правила 401 без согласованного изменения бэкенда/деплоя.
 * Транспорт только: префикс API и семантика 401 — согласованы с бэкендом (`src/main.py`, зависимости auth).
 */

import type { ApiErrorResponseBody } from "@/api/types";
import { ROUTE_PATHS, patientPublicLoginSearch } from "@/routePaths";
import { isPatientLoginPath } from "@/routePathUtils";
import i18n from "@/i18n";

/** Базовый префикс HTTP-моста; dev-прокси в `vite.config.ts` не менять без согласования с деплоем. */
export const API_BASE = "/api";

const BASE = API_BASE;

/**
 * Ключи `localStorage` для API (единый реестр).
 * Не дублировать строки в других модулях: использовать отсюда или `getPatientToken` / админские геттеры.
 */
export const API_STORAGE_KEYS = {
  patientToken: "dental_booking_patient_token",
  patientId: "dental_booking_patient_id",
  adminToken: "dental_booking_admin_token",
  adminId: "dental_booking_admin_id",
  adminClinicId: "dental_booking_admin_clinic_id",
} as const;

/** Корреляция с логами бэкенда для публичных fetch вне `api.*` (маркетинг, embed). */
export function newOutboundRequestId(): string {
  try {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
      return crypto.randomUUID();
    }
  } catch {
    // ignore
  }
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

const PATIENT_TOKEN_KEY = API_STORAGE_KEYS.patientToken;
const PATIENT_ID_KEY = API_STORAGE_KEYS.patientId;
const ADMIN_TOKEN_KEY = API_STORAGE_KEYS.adminToken;
const ADMIN_ID_KEY = API_STORAGE_KEYS.adminId;
/** Persists admin's clinic from login; must stay aligned with JWT `clinic_id` claim. */
const ADMIN_CLINIC_ID_KEY = API_STORAGE_KEYS.adminClinicId;

export function getPatientToken(): string | null {
  try {
    return localStorage.getItem(PATIENT_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function getAdminToken(): string | null {
  try {
    return localStorage.getItem(ADMIN_TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setAdminToken(token: string): void {
  try {
    localStorage.setItem(ADMIN_TOKEN_KEY, token);
  } catch {
    // ignore
  }
}

export function getAdminId(): string | null {
  try {
    return localStorage.getItem(ADMIN_ID_KEY);
  } catch {
    return null;
  }
}

export function setAdminId(adminId: string): void {
  try {
    localStorage.setItem(ADMIN_ID_KEY, adminId);
  } catch {
    // ignore
  }
}

export function getAdminClinicId(): string | null {
  try {
    return localStorage.getItem(ADMIN_CLINIC_ID_KEY);
  } catch {
    return null;
  }
}

export function setAdminClinicId(clinicId: string): void {
  try {
    localStorage.setItem(ADMIN_CLINIC_ID_KEY, clinicId);
  } catch {
    // ignore
  }
}

/** Read `clinic_id` from admin JWT payload (no crypto verify — transport already trusted after login). */
export function parseAdminJwtClinicId(token: string | null): string | null {
  if (!token) return null;
  try {
    const parts = token.split(".");
    if (parts.length < 2) return null;
    let b64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const pad = b64.length % 4;
    if (pad) b64 += "=".repeat(4 - pad);
    const payload = JSON.parse(atob(b64)) as { clinic_id?: string };
    return typeof payload.clinic_id === "string" ? payload.clinic_id : null;
  } catch {
    return null;
  }
}

/** Source of truth for admin UI scope: storage from login, else JWT claim. */
export function getBoundAdminClinicId(): string | null {
  return getAdminClinicId() ?? parseAdminJwtClinicId(getAdminToken());
}

export function clearAdminToken(): void {
  try {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
    localStorage.removeItem(ADMIN_ID_KEY);
    localStorage.removeItem(ADMIN_CLINIC_ID_KEY);
  } catch {
    // ignore
  }
}

function clearPatientAuth(): void {
  try {
    localStorage.removeItem(PATIENT_TOKEN_KEY);
    localStorage.removeItem(PATIENT_ID_KEY);
  } catch {
    // ignore
  }
  if (typeof window !== "undefined" && !isPatientLoginPath(window.location.pathname)) {
    const path = window.location.pathname;
    const scoped = path.match(/^\/c\/([^/]+)\//);
    window.location.href = scoped
      ? `/c/${scoped[1]}/sign-in`
      : `${ROUTE_PATHS.other.login}${patientPublicLoginSearch("session-expired")}`;
  }
}

/**
 * 401 с пациентской сессией: не только `/v1/patient/*`, но и эндпоинты с тем же JWT (например `POST /v1/payments`).
 * Для `/v1/patient/*` очистка только если есть признак сессии (Bearer в запросе или токен в storage),
 * чтобы не сбрасывать storage при «чужом» 401 без пациентского контекста.
 */
export function shouldClearPatientSessionOn401(
  path: string,
  resolvedToken: string | null
): boolean {
  const sessionHint = Boolean(resolvedToken) || Boolean(getPatientToken());
  if (path.includes("/v1/patient/")) return sessionHint;
  if (path.startsWith("/v1/payments")) return Boolean(resolvedToken);
  return Boolean(resolvedToken && resolvedToken === getPatientToken());
}

export interface ParsedApiFailureBody {
  rawMessage: string;
  code?: string;
  traceId?: string;
  details: Record<string, unknown> | null;
}

/** FastAPI 422: `detail` — массив `{ loc, msg, type }`. */
function formatValidationDetailArray(detail: unknown[]): string {
  const parts: string[] = [];
  for (const item of detail) {
    if (typeof item === "string") {
      parts.push(item);
      continue;
    }
    if (item && typeof item === "object" && "msg" in item) {
      const rec = item as { msg?: string; loc?: unknown[] };
      const msg = String(rec.msg ?? "").trim();
      if (!msg) continue;
      const loc = Array.isArray(rec.loc) ? rec.loc.map(String) : [];
      const tail = loc.length ? loc[loc.length - 1] : "";
      if (tail && tail !== "body" && tail !== "query") {
        parts.push(`${tail}: ${msg}`);
      } else {
        parts.push(msg);
      }
    }
  }
  return parts.join("; ");
}

export function parseFastApiErrorBody(bodyText: string): ParsedApiFailureBody {
  let rawMessage = bodyText || "";
  let code: string | undefined;
  let traceId: string | undefined;
  let details: Record<string, unknown> | null = null;
  try {
    const json = JSON.parse(bodyText) as ApiErrorResponseBody;
    code = json.code;
    if (typeof json.trace_id === "string" && json.trace_id.trim()) {
      traceId = json.trace_id.trim();
    }
    if (json.details && typeof json.details === "object" && !Array.isArray(json.details)) {
      details = { ...(details ?? {}), ...json.details };
    }
    if (Array.isArray(json.detail)) {
      rawMessage = formatValidationDetailArray(json.detail);
      if (!rawMessage.trim()) {
        rawMessage = bodyText || "";
      }
    } else if (typeof json.detail === "string") {
      rawMessage = json.detail;
    } else if (json.detail && typeof json.detail === "object") {
      const d = json.detail as {
        message?: string;
        detail?: string;
        code?: string;
        trace_id?: string;
        details?: Record<string, unknown>;
      };
      const nestedText =
        typeof d.message === "string" && d.message.trim()
          ? d.message
          : typeof d.detail === "string" && d.detail.trim()
            ? d.detail
            : "";
      rawMessage = nestedText || rawMessage;
      code = d.code ?? json.code;
      traceId = d.trace_id;
      const nestedDetails =
        d.details && typeof d.details === "object" && !Array.isArray(d.details) ? d.details : null;
      if (nestedDetails) {
        details = { ...(details ?? {}), ...nestedDetails };
      }
    } else if (typeof json.message === "string" && json.message.trim()) {
      rawMessage = json.message;
    }
  } catch {
    // keep defaults
  }
  return { rawMessage, code, traceId, details };
}

export type ApiError = ApiErrorResponseBody;

export class ApiErrorWithCode extends Error {
  code?: string;
  traceId?: string;
  details?: Record<string, unknown> | null;

  constructor(message: string, code?: string, traceId?: string, details?: Record<string, unknown> | null) {
    super(message);
    this.name = "ApiErrorWithCode";
    this.code = code;
    this.traceId = traceId;
    this.details = details ?? null;
  }
}

function normalizeErrorMessage(raw: string, status: number, statusText: string) {
  const message = raw.trim() || statusText || "Request failed";

  // Для 4xx обычно важно сохранить бизнес-сообщение (например, EMPTY_DB_NO_CLINIC),
  // но если нам вернули HTML (например, от nginx), то показываем аккуратное описание,
  // а не «полотно» разметки.
  const looksLikeHtml =
    message.startsWith("<!DOCTYPE html") ||
    message.startsWith("<html") ||
    message.includes("<html") ||
    message.includes("<head") ||
    message.includes("<body");

  if (status >= 400 && status < 500) {
    // 405 Method Not Allowed — часто от прокси, когда бэкенд недоступен или метод не разрешён
    if (status === 405) {
      return i18n.t("errors.method_not_allowed", { ns: "common" });
    }
    if (looksLikeHtml) {
      return i18n.t("errors.html_gateway", { ns: "common" });
    }
    return message;
  }

  // Для 5xx не показываем пользователю гигантский traceback
  const looksLikeTraceback =
    message.includes("Traceback (most recent call last)") ||
    message.includes("File \"") ||
    message.length > 400;

  if (status >= 500) {
    if (status === 502 || status === 503) {
      return i18n.t("errors.service_unavailable", { ns: "common" });
    }
    if (looksLikeTraceback) {
      return i18n.t("errors.internal_server_error", { ns: "common" });
    }
  }

  return message;
}

/** POST /v1/patients без JWT (default clinic); остальные /v1/patients* — с админским токеном (P2-FU2). */
function isPatientsPublicCreatePost(path: string, method: string): boolean {
  const m = (method || "GET").toUpperCase();
  const base = path.split("?")[0];
  return m === "POST" && base === "/v1/patients";
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  const hasRequestId = Boolean(
    headers["X-Request-Id"] ?? headers["x-request-id"],
  );
  if (!hasRequestId) {
    headers["X-Request-Id"] = newOutboundRequestId();
  }
  const method = options.method || "GET";
  const barePath = path.split("?")[0];
  const isClinicsTenantPath =
    barePath === "/v1/clinics" || barePath.startsWith("/v1/clinics/");
  const adminTok = getAdminToken();
  const needsAdminToken =
    (path.startsWith("/v1/admin") && !path.includes("/v1/admin/auth/login")) ||
    path.startsWith("/v1/owner/") ||
    (path.startsWith("/v1/patients") && !isPatientsPublicCreatePost(path, method));
  const resolvedToken =
    token ?? (needsAdminToken ? adminTok : null) ?? (isClinicsTenantPath && adminTok ? adminTok : null);
  if (resolvedToken) {
    headers["Authorization"] = `Bearer ${resolvedToken}`;
  }
  if (
    options.body &&
    typeof options.body === "string" &&
    !headers["Content-Type"]
  ) {
    headers["Content-Type"] = "application/json";
  }
  const res = await fetch(url, { ...options, headers: headers as HeadersInit });
  const bodyText = await res.text();
  const sentAdminOnClinics =
    isClinicsTenantPath && Boolean(resolvedToken && resolvedToken === adminTok);
  const isAdminOrOwnerUnauthorized =
    (path.includes("/v1/admin") && !path.includes("/v1/admin/auth/login")) ||
    path.startsWith("/v1/owner/") ||
    (path.startsWith("/v1/patients") && !isPatientsPublicCreatePost(path, method)) ||
    sentAdminOnClinics;
  if (res.status === 401 && isAdminOrOwnerUnauthorized) {
    clearAdminToken();
    if (typeof window !== "undefined") {
      window.location.href = ROUTE_PATHS.admin.login;
    }
    throw new ApiErrorWithCode(i18n.t("errors.unauthorized", { ns: "common" }), "unauthorized");
  }
  if (res.status === 401 && shouldClearPatientSessionOn401(path, resolvedToken)) {
    clearPatientAuth();
    const { rawMessage, code, traceId, details } = parseFastApiErrorBody(bodyText);
    const normalized = normalizeErrorMessage(
      rawMessage.trim() || "Unauthorized",
      res.status,
      res.statusText
    );
    throw new ApiErrorWithCode(normalized, code, traceId, details);
  }
  if (!res.ok) {
    const { rawMessage, code, traceId, details } = parseFastApiErrorBody(bodyText);
    const normalized = normalizeErrorMessage(
      rawMessage.trim() || res.statusText || bodyText,
      res.status,
      res.statusText
    );
    throw new ApiErrorWithCode(normalized, code, traceId, details);
  }
  if (res.status === 204 || !bodyText.trim()) return undefined as T;
  return JSON.parse(bodyText) as T;
}

/** POST multipart (без выставления Content-Type — boundary задаёт браузер). Ответ — JSON. */
async function requestFormJson<T>(
  path: string,
  formData: FormData,
  token?: string | null,
  method: "POST" | "PATCH" = "POST"
): Promise<T> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const headers: Record<string, string> = {
    "X-Request-Id": newOutboundRequestId(),
  };
  const needsAdminToken =
    (path.startsWith("/v1/admin") && !path.includes("/v1/admin/auth/login")) ||
    path.startsWith("/v1/owner/");
  const resolvedToken = token ?? (needsAdminToken ? getAdminToken() : null);
  if (resolvedToken) {
    headers["Authorization"] = `Bearer ${resolvedToken}`;
  }
  const res = await fetch(url, { method, body: formData, headers });
  const bodyText = await res.text();
  const isAdminOrOwnerUnauthorized =
    (path.includes("/v1/admin") && !path.includes("/v1/admin/auth/login")) ||
    path.startsWith("/v1/owner/");
  if (res.status === 401 && isAdminOrOwnerUnauthorized) {
    clearAdminToken();
    if (typeof window !== "undefined") {
      window.location.href = ROUTE_PATHS.admin.login;
    }
    throw new ApiErrorWithCode(i18n.t("errors.unauthorized", { ns: "common" }), "unauthorized");
  }
  if (res.status === 401 && shouldClearPatientSessionOn401(path, resolvedToken)) {
    clearPatientAuth();
    const { rawMessage, code, traceId, details } = parseFastApiErrorBody(bodyText);
    const normalized = normalizeErrorMessage(
      rawMessage.trim() || "Unauthorized",
      res.status,
      res.statusText
    );
    throw new ApiErrorWithCode(normalized, code, traceId, details);
  }
  if (!res.ok) {
    const { rawMessage, code, traceId, details } = parseFastApiErrorBody(bodyText);
    const normalized = normalizeErrorMessage(
      rawMessage.trim() || res.statusText || bodyText,
      res.status,
      res.statusText
    );
    throw new ApiErrorWithCode(normalized, code, traceId, details);
  }
  if (res.status === 204 || !bodyText.trim()) return undefined as T;
  return JSON.parse(bodyText) as T;
}

/** GET бинарного ответа (вложения и т.п.). */
async function requestBlob(path: string, token?: string | null): Promise<Blob> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const headers: Record<string, string> = {
    "X-Request-Id": newOutboundRequestId(),
  };
  const needsAdminToken =
    (path.startsWith("/v1/admin") && !path.includes("/v1/admin/auth/login")) ||
    path.startsWith("/v1/owner/");
  const resolvedToken = token ?? (needsAdminToken ? getAdminToken() : null);
  if (resolvedToken) {
    headers["Authorization"] = `Bearer ${resolvedToken}`;
  }
  const res = await fetch(url, { method: "GET", headers });
  const isAdminOrOwnerUnauthorized =
    (path.includes("/v1/admin") && !path.includes("/v1/admin/auth/login")) ||
    path.startsWith("/v1/owner/");
  if (res.status === 401 && isAdminOrOwnerUnauthorized) {
    clearAdminToken();
    if (typeof window !== "undefined") {
      window.location.href = ROUTE_PATHS.admin.login;
    }
    throw new ApiErrorWithCode(i18n.t("errors.unauthorized", { ns: "common" }), "unauthorized");
  }
  if (!res.ok) {
    const bodyText = await res.text();
    if (res.status === 401 && shouldClearPatientSessionOn401(path, resolvedToken)) {
      clearPatientAuth();
      const { rawMessage, code, traceId, details } = parseFastApiErrorBody(bodyText);
      const normalized = normalizeErrorMessage(
        rawMessage.trim() || "Unauthorized",
        res.status,
        res.statusText
      );
      throw new ApiErrorWithCode(normalized, code, traceId, details);
    }
    const { rawMessage, code, traceId, details } = parseFastApiErrorBody(bodyText);
    const normalized = normalizeErrorMessage(
      rawMessage.trim() || res.statusText || bodyText,
      res.status,
      res.statusText
    );
    throw new ApiErrorWithCode(normalized, code, traceId, details);
  }
  return res.blob();
}

export const api = {
  get: <T>(path: string, token?: string | null) =>
    request<T>(path, { method: "GET" }, token),
  post: <T>(
    path: string,
    body?: object,
    token?: string | null,
    extraHeaders?: Record<string, string>
  ) =>
    request<T>(
      path,
      {
        method: "POST",
        body: body ? JSON.stringify(body) : undefined,
        headers: extraHeaders,
      },
      token
    ),
  postFormData: <T>(path: string, formData: FormData, token?: string | null) =>
    requestFormJson<T>(path, formData, token),
  patchFormData: <T>(path: string, formData: FormData, token?: string | null) =>
    requestFormJson<T>(path, formData, token, "PATCH"),
  getBlob: (path: string, token?: string | null) => requestBlob(path, token),
  put: <T>(path: string, body?: object, token?: string | null) =>
    request<T>(
      path,
      { method: "PUT", body: body ? JSON.stringify(body) : undefined },
      token
    ),
  delete: <T>(
    path: string,
    token?: string | null,
    extraHeaders?: Record<string, string>
  ) =>
    request<T>(path, { method: "DELETE", headers: extraHeaders }, token),
  patch: <T>(path: string, body?: object, token?: string | null) =>
    request<T>(
      path,
      { method: "PATCH", body: body ? JSON.stringify(body) : undefined },
      token
    ),
};

export function authApi(token: string | null) {
  return {
    get: <T>(path: string) => api.get<T>(path, token),
    post: <T>(path: string, body?: object, extraHeaders?: Record<string, string>) =>
      api.post<T>(path, body, token, extraHeaders),
    postFormData: <T>(path: string, formData: FormData) =>
      api.postFormData<T>(path, formData, token),
    getBlob: (path: string) => api.getBlob(path, token),
    put: <T>(path: string, body?: object) => api.put<T>(path, body, token),
    delete: <T>(path: string, extraHeaders?: Record<string, string>) =>
      api.delete<T>(path, token, extraHeaders),
    patch: <T>(path: string, body?: object) => api.patch<T>(path, body, token),
  };
}

export default api;
