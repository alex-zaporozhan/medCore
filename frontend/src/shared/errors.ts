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

