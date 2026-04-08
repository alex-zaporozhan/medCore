/**
 * Семантика карточек задач Kanban / деталей — тот же каркас, что у слотов расписания
 * (`--calendar-card-border`, `--calendar-card-shadow`, левая полоса + фон по статусу).
 * Семантика статусов задач для UI — константы ниже; при смене правил обновлять тесты и подписи в админке.
 */
import type { CSSProperties } from "react";

const SLOT_FRAME: CSSProperties = {
  borderRadius: "var(--calendar-slot-radius)",
  border: "1px solid var(--calendar-card-border)",
  boxShadow: "var(--calendar-card-shadow)",
  borderLeftWidth: "var(--calendar-bar-width)",
  borderLeftStyle: "solid",
};

export function taskStatusCardSurface(status: string): CSSProperties {
  const s = String(status).toLowerCase();
  switch (s) {
    case "open":
      return {
        ...SLOT_FRAME,
        background: "var(--calendar-scheduled-bg)",
        borderLeftColor: "var(--calendar-scheduled-bar)",
      };
    case "in_progress":
      return {
        ...SLOT_FRAME,
        background: "var(--calendar-in-progress-bg)",
        borderLeftColor: "var(--calendar-in-progress-bar)",
      };
    case "on_hold":
      return {
        ...SLOT_FRAME,
        background: "var(--calendar-system-bg)",
        borderLeftColor: "var(--calendar-system-bar)",
      };
    case "review":
      return {
        ...SLOT_FRAME,
        background: "var(--calendar-attention-denim-bg)",
        borderLeftColor: "var(--calendar-attention-denim-bar)",
      };
    case "done":
      return {
        ...SLOT_FRAME,
        background: "var(--calendar-completed-bg)",
        borderLeftColor: "var(--calendar-completed-bar)",
      };
    case "cancelled":
      return {
        ...SLOT_FRAME,
        background: "var(--calendar-negative-bg)",
        borderLeftColor: "var(--calendar-negative-bar)",
      };
    default:
      return {
        ...SLOT_FRAME,
        background: "var(--calendar-scheduled-bg)",
        borderLeftColor: "var(--calendar-scheduled-bar)",
      };
  }
}

export function taskStatusTextColors(status: string): { title: string; meta: string } {
  const s = String(status).toLowerCase();
  if (s === "in_progress") {
    return { title: "var(--calendar-in-progress-title)", meta: "var(--calendar-in-progress-meta)" };
  }
  if (s === "on_hold") {
    return { title: "var(--calendar-system-title)", meta: "var(--calendar-system-meta)" };
  }
  if (s === "review") {
    return { title: "var(--calendar-attention-denim-title)", meta: "var(--calendar-attention-denim-meta)" };
  }
  if (s === "done") {
    return { title: "var(--calendar-completed-title)", meta: "var(--calendar-completed-meta)" };
  }
  if (s === "cancelled") {
    return { title: "var(--calendar-negative-title)", meta: "var(--calendar-negative-meta)" };
  }
  return { title: "var(--calendar-scheduled-title)", meta: "var(--calendar-scheduled-meta)" };
}

type BadgeRoot = { root: CSSProperties };

/** Бейдж статуса — те же токены, что у слотов «ожидает / в работе / …». */
export function taskStatusBadgeStyles(status: string): BadgeRoot {
  const s = String(status).toLowerCase();
  switch (s) {
    case "open":
      return {
        root: {
          backgroundColor: "var(--calendar-scheduled-badge-bg)",
          color: "var(--calendar-scheduled-badge-text)",
        },
      };
    case "in_progress":
      return {
        root: {
          backgroundColor: "var(--calendar-in-progress-badge-bg)",
          color: "var(--calendar-in-progress-badge-text)",
          border: "1px solid var(--calendar-in-progress-badge-border)",
        },
      };
    case "on_hold":
      return {
        root: {
          backgroundColor: "var(--calendar-system-badge-bg)",
          color: "var(--calendar-system-badge-text)",
        },
      };
    case "review":
      return {
        root: {
          backgroundColor: "var(--calendar-attention-denim-badge-bg)",
          color: "var(--calendar-attention-denim-badge-text)",
        },
      };
    case "done":
      return {
        root: {
          backgroundColor: "var(--calendar-completed-badge-bg)",
          color: "var(--calendar-completed-badge-text)",
        },
      };
    case "cancelled":
      return {
        root: {
          backgroundColor: "var(--calendar-negative-badge-bg)",
          color: "var(--calendar-negative-badge-text)",
        },
      };
    default:
      return {
        root: {
          backgroundColor: "var(--calendar-scheduled-badge-bg)",
          color: "var(--calendar-scheduled-badge-text)",
        },
      };
  }
}

export function priorityBadgeColor(priority: string): "red" | "orange" | "yellow" | "gray" {
  if (priority === "urgent") return "red";
  if (priority === "high") return "orange";
  if (priority === "medium") return "yellow";
  return "gray";
}
