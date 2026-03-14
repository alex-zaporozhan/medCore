/**
 * Thin API client: base URL /api, Bearer token, error parsing.
 * No caching or business logic — transport only.
 * On 401 for patient routes: clear patient token and redirect to /login.
 */

const BASE = "/api";

const PATIENT_TOKEN_KEY = "dental_booking_patient_token";
const PATIENT_ID_KEY = "dental_booking_patient_id";
const ADMIN_TOKEN_KEY = "dental_booking_admin_token";

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

export function clearAdminToken(): void {
  try {
    localStorage.removeItem(ADMIN_TOKEN_KEY);
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
  if (typeof window !== "undefined" && window.location.pathname !== "/login") {
    window.location.href = "/login";
  }
}

export interface ApiError {
  detail?: string;
  code?: string;
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
      return "Сервер не принимает этот тип запроса. Если вы входите в админку — попробуйте обновить страницу и войти снова. При повторении обратитесь к администратору.";
    }
    if (looksLikeHtml) {
      return "Сервис временно недоступен или ответ сервера некорректен. Обновите страницу и повторите попытку или обратитесь к администратору.";
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
      return "Сервис временно недоступен. Подождите минуту и обновите страницу. При повторении обратитесь к администратору.";
    }
    if (looksLikeTraceback) {
      return "Внутренняя ошибка сервера. Обратитесь к администратору.";
    }
  }

  return message;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const headers: HeadersInit = {
    ...(options.headers as Record<string, string>),
  };
  const needsAdminToken =
    (path.startsWith("/v1/admin") && !path.includes("/v1/admin/auth/login")) || path.startsWith("/v1/owner/");
  const resolvedToken = token ?? (needsAdminToken ? getAdminToken() : null);
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
  const res = await fetch(url, { ...options, headers });
  const bodyText = await res.text();
  const isAdminOrOwnerUnauthorized =
    (path.includes("/v1/admin") && !path.includes("/v1/admin/auth/login")) || path.startsWith("/v1/owner/");
  if (res.status === 401 && isAdminOrOwnerUnauthorized) {
    clearAdminToken();
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    throw new Error("Требуется авторизация");
  }
  if (res.status === 401 && path.includes("/v1/patient/")) {
    clearPatientAuth();
    let rawMessage: string;
    try {
      const json = JSON.parse(bodyText) as ApiError;
      rawMessage = typeof json.detail === "string" ? json.detail : "Unauthorized";
    } catch {
      rawMessage = "Unauthorized";
    }
    throw new Error(rawMessage);
  }
  if (!res.ok) {
    let rawMessage: string;
    try {
      const json = JSON.parse(bodyText) as ApiError;
      rawMessage = typeof json.detail === "string" ? json.detail : res.statusText;
    } catch {
      rawMessage = bodyText || res.statusText;
    }
    const normalized = normalizeErrorMessage(rawMessage, res.status, res.statusText);
    throw new Error(normalized);
  }
  if (res.status === 204 || !bodyText.trim()) return undefined as T;
  return JSON.parse(bodyText) as T;
}

export const api = {
  get: <T>(path: string, token?: string | null) =>
    request<T>(path, { method: "GET" }, token),
  post: <T>(path: string, body?: object, token?: string | null) =>
    request<T>(
      path,
      { method: "POST", body: body ? JSON.stringify(body) : undefined },
      token
    ),
  put: <T>(path: string, body?: object, token?: string | null) =>
    request<T>(
      path,
      { method: "PUT", body: body ? JSON.stringify(body) : undefined },
      token
    ),
  delete: <T>(path: string, token?: string | null) =>
    request<T>(path, { method: "DELETE" }, token),
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
    post: <T>(path: string, body?: object) => api.post<T>(path, body, token),
    put: <T>(path: string, body?: object) => api.put<T>(path, body, token),
    delete: <T>(path: string) => api.delete<T>(path, token),
    patch: <T>(path: string, body?: object) => api.patch<T>(path, body, token),
  };
}

export default api;
