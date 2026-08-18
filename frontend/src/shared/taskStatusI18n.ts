/**
 * Visible task/priority labels come from `tasks.status.*` / `tasks.priority.*`.
 * Status *codes* stay stable for DnD, board columns, and the API.
 */

import i18n from "@/i18n";

export const TASK_STATUS_CODES = ["open", "in_progress", "on_hold", "review", "done", "cancelled"] as const;
export type TaskStatusCode = (typeof TASK_STATUS_CODES)[number];

export function taskStatusLabel(status: string): string {
  switch (status) {
    case "open":
    case "in_progress":
    case "on_hold":
    case "review":
    case "done":
    case "cancelled":
      return i18n.t(`status.${status}`, { ns: "tasks" });
    default:
      return status;
  }
}

export function taskPriorityLabel(priority: string): string {
  switch (priority) {
    case "low":
    case "medium":
    case "high":
    case "urgent":
      return i18n.t(`priority.${priority}`, { ns: "tasks" });
    default:
      return priority;
  }
}

export function taskStatusSelectOptions(): { value: string; label: string }[] {
  return TASK_STATUS_CODES.map((value) => ({ value, label: taskStatusLabel(value) }));
}

export function leadOutcomeLabel(key: "BOOKED" | "NOT_BOOKED" | "UNKNOWN"): string {
  return i18n.t(`leadOutcome.${key}`, { ns: "tasks" });
}
