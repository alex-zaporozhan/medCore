/**
 * Mirror of BookingStatusService. Admin chrome labels come from bookings.status.*.
 */

import { tNs } from "@/i18n";

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

const STATUS_I18N_KEYS = new Set<string>(BOOKING_STATUS_OPTION_ORDER);

export function bookingStatusLabel(status: string): string {
  if (!STATUS_I18N_KEYS.has(status)) return status;
  return tNs("bookings", `status.${status}`);
}

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
    label: bookingStatusLabel(v),
  }));
}
