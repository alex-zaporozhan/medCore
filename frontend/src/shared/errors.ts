/** TanStack Query / fetch errors — для UI §11 (ARCHITECTURE_EXCELLENCE_PASSPORT). */
export function formatQueryError(error: unknown): string {
  if (error instanceof Error && error.message) return error.message;
  if (typeof error === "string" && error.length > 0) return error;
  return "Произошла ошибка. Попробуйте обновить страницу.";
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
  "empty_db_no_clinic",
  "clinic_forbidden",
]);

export function commonErrorI18nKey(code: string | undefined): string | null {
  if (!code || !COMMON_ERROR_CODES.has(code)) return null;
  return `errors.${code}`;
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
  if (apiErrorCode(error) === "empty_db_no_clinic") return true;
  const message = errorMessageText(error);
  if (/нет ни одной клиник/i.test(message)) return true;
  return /\bno clinics?\b/i.test(message);
}

export function adminQueryErrorI18nKey(error: unknown): string | null {
  if (isEmptyClinicDatabaseError(error)) return "errors.empty_db_no_clinic";
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
      return "Выбранный слот уже занят. Пожалуйста, выберите другое время.";
    }
    if (code === "booking_status_invalid") {
      return fallbackMessage || "Недопустимый статус записи.";
    }
    if (code === "clinic_mismatch") {
      return fallbackMessage || "Клиника не совпадает с услугой или профилем. Выберите клинику заново.";
    }
    // Для остальных кодов по умолчанию доверяем сообщению сервера,
    // чтобы не терять бизнес‑смысл из patient_messages.py.
    return fallbackMessage || "Не удалось создать запись. Повторите попытку.";
  }

  // context === "payment"
  if (code === "payment_not_allowed") {
    return fallbackMessage || "Оплата недоступна для этой записи.";
  }
  if (code === "payment_failed") {
    return (
      fallbackMessage ||
      "Платёж не прошёл. Попробуйте ещё раз или выберите другой способ оплаты."
    );
  }
  if (code === "booking_not_found") {
    return (
      fallbackMessage ||
      "Запись не найдена. Обновите страницу или создайте запись заново."
    );
  }

  return fallbackMessage || "Не удалось инициировать оплату. Попробуйте позже.";
}
