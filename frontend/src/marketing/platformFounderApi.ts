/**
 * Shared helpers for founder-cabinet HTTP (error envelope + JSON arrays).
 * UI copy is translated at render time (`FounderQueryError`) so a locale switch
 * does not refetch provision/leads queues.
 */

import type { TFunction } from "i18next";

export type FounderFailKind =
  | "session"
  | "unavailable"
  | "http"
  | "wrongToken"
  | "serviceDisabled"
  | "retryConflict"
  | "closeConflict";

export class FounderQueryError extends Error {
  readonly kind: FounderFailKind;
  readonly httpStatus?: number;
  readonly apiDetail?: string;

  constructor(kind: FounderFailKind, opts?: { httpStatus?: number; apiDetail?: string }) {
    super(kind);
    this.name = "FounderQueryError";
    this.kind = kind;
    this.httpStatus = opts?.httpStatus;
    this.apiDetail = opts?.apiDetail;
  }
}

export function founderFailMessage(err: unknown, t: TFunction<"founder">): string {
  if (err instanceof FounderQueryError) {
    const detail = err.apiDetail?.trim();
    if (detail) return detail;
    switch (err.kind) {
      case "http":
        return t("errors.status", { status: err.httpStatus ?? 0 });
      case "session":
        return t("errors.sessionInvalid");
      case "unavailable":
        return t("errors.serviceUnavailable");
      case "wrongToken":
        return t("errors.wrongToken");
      case "serviceDisabled":
        return t("errors.serviceDisabled");
      case "retryConflict":
        return t("errors.retryConflict");
      case "closeConflict":
        return t("errors.closeConflict");
      default:
        return t("errors.loadFailed");
    }
  }
  if (err instanceof Error && err.message.trim()) return err.message;
  return t("errors.loadFailed");
}

export async function formatPlatformFounderApiError(r: Response, fallback: string): Promise<string> {
  try {
    const body: unknown = await r.json();
    if (body && typeof body === "object") {
      const o = body as { detail?: unknown; code?: unknown };
      const topCode = typeof o.code === "string" ? o.code : "";
      const d = o.detail;
      if (typeof d === "string") {
        return topCode ? `${topCode}: ${d}` : d;
      }
      if (d && typeof d === "object" && "message" in d && typeof (d as { message: string }).message === "string") {
        const nested =
          "code" in d && typeof (d as { code?: string }).code === "string"
            ? `${(d as { code: string }).code}: `
            : "";
        const msg = `${nested}${(d as { message: string }).message}`;
        return topCode ? `${topCode}: ${msg}` : msg;
      }
    }
  } catch {
    /* ignore */
  }
  return fallback;
}

export function parseJsonArray<T>(raw: unknown): T[] {
  return Array.isArray(raw) ? (raw as T[]) : [];
}
