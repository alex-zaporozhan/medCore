/**
 * Public platform billing (checkout + shared lead/captcha envelope).
 * User-facing copy follows `ui.locale` via the marketing namespace (not a frozen RU map).
 */

import { parseFastApiErrorBody } from "@/api/client";
import i18n, { tNs } from "@/i18n";

export type PublicCheckoutErrorShape = {
  code: string;
  message: string;
  siteKey: string | null;
  traceId: string | null;
};

export function messageForPlatformCheckoutCode(code: string, fallback: string): string {
  if (!code) return fallback;
  const key = `checkout.errors.${code}`;
  const translated = tNs("marketing", key);
  return translated === key ? fallback : translated;
}

export function catalogFetchErrorMessage(status: number, bodyText: string): string {
  const fallback = tNs("marketing", "checkout.catalogLoadFailed");
  if (status >= 500 || status === 0) return fallback;
  const parsed = parseFastApiErrorBody(bodyText || "{}");
  const msg = parsed.rawMessage?.trim() ?? "";
  if (!msg || msg === "{}" || msg === "[]") return fallback;
  return msg;
}

export function parsePublicCheckoutFailure(
  status: number,
  data: Record<string, unknown>,
): PublicCheckoutErrorShape {
  const parsed = parseFastApiErrorBody(JSON.stringify(data));
  const code = (parsed.code ?? "").trim();
  let message =
    (parsed.rawMessage ?? "").trim() ||
    String(i18n.t("checkout.httpError", { ns: "marketing", status }));
  const details = parsed.details;
  const siteRaw = details?.site_key;
  const siteKey = typeof siteRaw === "string" ? siteRaw : null;
  const traceId = typeof parsed.traceId === "string" && parsed.traceId.trim() ? parsed.traceId.trim() : null;

  if (code) {
    message = messageForPlatformCheckoutCode(code, message);
  }

  return { code, message, siteKey, traceId };
}
