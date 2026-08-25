/** TanStack Query / fetch errors — для UI §11 (ARCHITECTURE_EXCELLENCE_PASSPORT). */
export function formatQueryError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === "string" && error.length > 0) return error;
  return "Something went wrong. Refresh the page.";
}

export type BookingErrorCode =
  | "slot_unavailable"
  | "patient_not_found"
  | "payment_failed"
  | "prepayment_required"
  | "validation_error"
  | "service_unavailable"
  | "booking_not_found"
  | "clinic_mismatch"
  | "booking_status_invalid"
  | "payment_not_allowed";

export function apiErrorCode(error: unknown): string | undefined {
  if (!error || typeof error !== "object") return undefined;
  const code = (error as { code?: unknown }).code;
  if (typeof code !== "string") return undefined;
  const trimmed = code.trim();
  return trimmed.length > 0 ? trimmed : undefined;
}

const BOOKING_ERROR_I18N: Record<string, Partial<Record<"booking" | "payment", string>>> = {
  slot_unavailable: { booking: "errors.slotUnavailable" },
  booking_status_invalid: { booking: "errors.statusInvalid" },
  clinic_mismatch: { booking: "errors.clinicMismatch" },
  payment_failed: { payment: "errors.paymentFailed" },
  payment_not_allowed: { payment: "errors.paymentNotAllowed" },
  booking_not_found: { payment: "errors.bookingNotFound" },
};

export function bookingErrorI18nKey(
  code: string | undefined,
  context: "booking" | "payment",
): string | null {
  if (!code) return null;
  return BOOKING_ERROR_I18N[code]?.[context] ?? null;
}

const COMMON_ERROR_CODES = new Set([
  "entitlement_required",
  "box_forbidden",
  "forbidden",
  "unauthorized",
  "not_found",
  "conflict",
  "validation_error",
  "rate_limited",
  "internal_server_error",
  "bad_request",
  "method_not_allowed",
  "html_gateway",
  "service_unavailable",
  "empty_db_no_clinic",
  "clinic_forbidden",
  "invalid_credentials",
  "invalid_totp",
  "invalid_mfa_token",
  "billing_revoked",
  "clinic_context_required",
  "platform_founder_jwt_not_configured",
  "platform_founder_inactive_or_unknown",
  "platform_founder_totp_enrollment_required",
  "platform_founder_token_required",
]);

const COMMON_ERROR_CODE_ALIASES: Record<string, string> = {
  rate_limited: "rate_limited",
  empty_db_no_clinic: "empty_db_no_clinic",
  billing_revoked: "billing_revoked",
};

export function commonErrorI18nKey(code: string | undefined): string | null {
  if (!code) return null;
  const normalized = COMMON_ERROR_CODE_ALIASES[code] ?? code;
  if (!COMMON_ERROR_CODES.has(normalized)) return null;
  return `errors.${normalized}`;
}

export function localizedParsedApiErrorText(
  parsed: { code?: string; rawMessage?: string },
  t: (key: string, options?: Record<string, unknown>) => string,
  fallback: string,
): string {
  const mapped = commonErrorI18nKey(parsed.code);
  if (mapped) return String(t(mapped, { ns: "common" }));
  return parsed.rawMessage?.trim() || fallback;
}

export function localizedApiErrorText(
  error: unknown,
  t: (key: string, options?: Record<string, unknown>) => string,
  fallbackKey: string,
): string {
  const mapped = commonErrorI18nKey(apiErrorCode(error));
  if (mapped) return String(t(mapped, { ns: "common" }));
  if (error instanceof Error && error.message.trim()) return error.message;
  return String(t(fallbackKey));
}

export function isAdminChromePath(pathname: string | undefined): boolean {
  if (!pathname) return false;
  return pathname === "/admin" || pathname.startsWith("/admin/");
}

function errorMessageText(error: unknown): string {
  if (typeof error === "string") return error;
  if (error instanceof Error) return error.message;
  if (error && typeof error === "object" && "message" in error) {
    return String((error as { message?: unknown }).message ?? "");
  }
  return "";
}

export function isEmptyClinicDatabaseError(error: unknown): boolean {
  const code = apiErrorCode(error);
  if (code === "empty_db_no_clinic") return true;
  const message = errorMessageText(error);
  if (/нет ни одной клиник/i.test(message)) return true;
  if (/no clinics in the database/i.test(message)) return true;
  return /\bno clinics?\b/i.test(message);
}

export function adminQueryErrorI18nKey(error: unknown): string | null {
  if (isEmptyClinicDatabaseError(error)) {
    return commonErrorI18nKey("empty_db_no_clinic") ?? "errors.empty_db_no_clinic";
  }
  return commonErrorI18nKey(apiErrorCode(error));
}

export function getBookingErrorMessage(
  code: string | undefined,
  fallbackMessage: string | undefined,
  context: "booking" | "payment"
): string | null {
  if (!code && !fallbackMessage) return null;

  if (context === "booking") {
    if (code === "slot_unavailable") {
      return fallbackMessage || "This slot is already taken. Please choose another time.";
    }
    if (code === "booking_status_invalid") {
      return fallbackMessage || "This booking status is not allowed.";
    }
    if (code === "clinic_mismatch") {
      return fallbackMessage || "Clinic does not match the service or profile. Select the clinic again.";
    }
    return fallbackMessage || "Could not create the booking. Try again.";
  }

  if (code === "payment_not_allowed") {
    return fallbackMessage || "Payment is not available for this booking.";
  }
  if (code === "payment_failed") {
    return fallbackMessage || "Payment did not go through. Try again or choose another payment method.";
  }
  if (code === "booking_not_found") {
    return fallbackMessage || "Booking not found. Refresh the page or create the booking again.";
  }

  return fallbackMessage || "Could not start payment. Try again later.";
}
