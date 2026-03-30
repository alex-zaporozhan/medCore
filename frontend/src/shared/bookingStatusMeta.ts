/**
 * Зеркало `BookingStatusService` + RU-лейблы (LEAD_BOOKING_STATUS_LIFECYCLE_RU).
 * Допустимые переходы должны совпадать с бэкендом.
 */

/** Порядок отображения в селекте (если статус доступен). */
export const BOOKING_STATUS_OPTION_ORDER = [
  "registered",
  "confirmed",
  "pending",
  "in_progress",
  "completed",
  "no_show",
  "cancelled",
  "awaiting_payment",
] as const;

export const BOOKING_STATUS_LABEL_RU: Record<string, string> = {
  registered: "Зарегистрирован",
  confirmed: "Подтверждён",
  pending: "Ожидает",
  in_progress: "На приёме",
  completed: "Завершён",
  no_show: "Неявка",
  cancelled: "Отмена",
  awaiting_payment: "Ожидает оплату",
};

/** Допустимые цели перехода (включая текущий статус). */
export const BOOKING_STATUS_TRANSITIONS: Record<string, string[]> = {
  pending: [
    "pending",
    "registered",
    "confirmed",
    "in_progress",
    "completed",
    "no_show",
    "cancelled",
  ],
  registered: [
    "registered",
    "confirmed",
    "in_progress",
    "completed",
    "no_show",
    "cancelled",
  ],
  confirmed: [
    "confirmed",
    "in_progress",
    "completed",
    "no_show",
    "cancelled",
  ],
  in_progress: ["in_progress", "completed", "no_show", "cancelled"],
  awaiting_payment: ["awaiting_payment", "confirmed", "cancelled"],
  completed: ["completed"],
  no_show: ["no_show"],
  cancelled: ["cancelled"],
};

export function bookingStatusSelectOptions(current: string): { value: string; label: string }[] {
  const allowed = BOOKING_STATUS_TRANSITIONS[current];
  const values = allowed ?? [current];
  const orderIndex = (v: string) => {
    const i = (BOOKING_STATUS_OPTION_ORDER as readonly string[]).indexOf(v);
    return i === -1 ? 999 : i;
  };
  const sorted = [...values].sort((a, b) => orderIndex(a) - orderIndex(b) || a.localeCompare(b));
  return sorted.map((v) => ({
    value: v,
    label: BOOKING_STATUS_LABEL_RU[v] ?? v,
  }));
}
