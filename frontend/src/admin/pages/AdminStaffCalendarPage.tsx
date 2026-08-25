import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode, type RefObject } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Box,
  Badge,
  ActionIcon,
  Button,
  Group,
  Modal,
  MultiSelect,
  Popover,
  Select,
  UnstyledButton,
  ScrollArea,
  Stack,
  SimpleGrid,
  Switch,
  Text,
  TextInput,
  Textarea,
  Table,
} from "@mantine/core";
import { IconClock } from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { ContextBar, EmptyState, PageSkeleton, QueryErrorAlert, CompactMonthPicker, PersonNameLink } from "@/shared/ui";
import {
  ADMIN_NAV_SAFE_MODAL_PROPS,
  ADMIN_SHELL_NAVBAR_OFFSET,
  SHELL_MODAL_NAV_INNER_STYLE,
  SHELL_OVERLAY_PROPS,
} from "@/shared/ui/shellPanelStyles";
import { displayPersonName } from "@/shared/ui/personNameFallback";
import {
  useAdminAdmins,
  useAdminSession,
  useCreateStaffCalendarEvent,
  useStaffCalendarEventDetails,
  useStaffCalendarMonthGrid,
  useAckStaffCalendarInvitation,
  useUpdateStaffCalendarEvent,
} from "@/hooks";
import type { StaffCalendarEventResponse } from "@/hooks";
import type { CalendarDayCell } from "@/hooks/useStaffCollab";
import { useAdminTaskDetails } from "@/hooks/useAdminTaskDetails";
import { useAdminTasksList, useAdminTasksMyFocus, useAdminTasksOpen } from "@/hooks/useAdminTasks";
import { getAdminId } from "@/api/client";
import dayjs from "dayjs";

/** Разбить плоский список дней месяца на строки по 7 (Пн–Вс). Недостающие ячейки — null. */
function chunkCalendarWeeks(days: CalendarDayCell[]): (CalendarDayCell | null)[][] {
  const rows: (CalendarDayCell | null)[][] = [];
  for (let i = 0; i < days.length; i += 7) {
    const slice: (CalendarDayCell | null)[] = days.slice(i, i + 7);
    while (slice.length < 7) slice.push(null);
    rows.push(slice);
  }
  return rows;
}

/** LEAD: спокойная палитра (`--staff-cal-*` в index.css) */
function staffEventChipSurface(isReminder: boolean, isUnseen: boolean): CSSProperties {
  const base: CSSProperties = {
    borderRadius: "var(--calendar-slot-radius)",
    border: "1px solid rgba(15, 20, 25, 0.05)",
    boxShadow: "var(--calendar-card-shadow)",
    width: "100%",
    boxSizing: "border-box",
    padding: "var(--space-xs) var(--space-6)",
    borderLeftWidth: "var(--calendar-bar-width)",
    borderLeftStyle: "solid",
  };
  if (isUnseen) {
    return {
      ...base,
      background: "var(--staff-cal-chip-unseen-bg)",
      borderLeftColor: "var(--staff-cal-chip-unseen-bar)",
    };
  }
  if (isReminder) {
    return {
      ...base,
      background: "var(--staff-cal-chip-reminder-bg)",
      borderLeftColor: "var(--staff-cal-chip-reminder-bar)",
    };
  }
  return {
    ...base,
    background: "var(--staff-cal-chip-default-bg)",
    borderLeftColor: "var(--staff-cal-chip-default-bar)",
  };
}

function staffEventTextColor(_isReminder: boolean, _isUnseen: boolean): string {
  return "var(--staff-cal-chip-title)";
}

const COMPLETE_HHMM_RE = /^([01]\d|2[0-3]):[0-5]\d$/;

/** True only for a complete clock value the API can consume (00–23 : 00–59). */
export function isValidHhmm(raw: string): boolean {
  return COMPLETE_HHMM_RE.test(raw || "");
}

/** True when both edges are clocks and end is strictly after start on the same local day. */
export function isReadyTimedRange(start: string, end: string, dayIso: string): boolean {
  if (!isValidHhmm(start) || !isValidHhmm(end)) return false;
  const s = dayjs(`${dayIso}T${start}`);
  const e = dayjs(`${dayIso}T${end}`);
  return s.isValid() && e.isValid() && e.isAfter(s);
}

/** Keep only digits and colon while typing. Never live-pad 3 digits (930 must stay 930 until blur). */
export function filterTimeDraft(raw: string): string {
  return (raw || "").replace(/[^\d:]/g, "").slice(0, 5);
}

/**
 * Keep the HH:mm colon visible while typing a valid hour (00–23).
 * Four digits `0900` become `09:00` immediately (paste / fast type).
 * Does not live-pad 3-digit strings (930 stays 930 until blur).
 * Backspacing the colon off "09:" stays "09" — the colon is not bounced back.
 */
export function formatTimeDraft(raw: string, previous = ""): string {
  const filtered = filterTimeDraft(raw);
  if (filtered.includes(":")) {
    const [h = "", m = ""] = filtered.split(":");
    const hh = h.replace(/\D/g, "").slice(0, 2);
    const mm = m.replace(/\D/g, "").slice(0, 2);
    if (!hh && !mm) return "";
    if (mm) return `${hh}:${mm}`;
    return `${hh}:`;
  }
  const digits = filtered.replace(/\D/g, "").slice(0, 4);
  if (digits.length === 4) {
    const hour = Number(digits.slice(0, 2));
    if (Number.isFinite(hour) && hour >= 0 && hour <= 23) {
      return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
    }
    return digits;
  }
  if (digits.length === 2) {
    const prev = filterTimeDraft(previous);
    if (prev === `${digits}:` || prev.startsWith(`${digits}:`)) {
      return digits;
    }
    const hour = Number(digits);
    if (Number.isFinite(hour) && hour >= 0 && hour <= 23) {
      return `${digits}:`;
    }
  }
  return digits;
}

function clampFourDigitClock(fourDigits: string): string {
  const hh = fourDigits.slice(0, 2);
  const mm = fourDigits.slice(2, 4).padEnd(2, "0");
  const h = Number(hh);
  let m = Number(mm);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return `${hh}:${mm}`;
  if (h > 23) return `${hh}:${mm}`;
  if (m > 59) m = 59;
  return `${hh}:${String(m).padStart(2, "0")}`;
}

/** Blur/submit normalize: 9 → 09:00, 09 → 09:00, 930 → 09:30, 0930 → 09:30. Empty stays empty until submit. */
export function normalizeTimeBlur(raw: string): string {
  const digits = (raw || "").replace(/[^\d]/g, "").slice(0, 4);
  if (!digits) return "";
  if (digits.length === 1) {
    return `0${digits}:00`;
  }
  if (digits.length === 2) {
    const hour = Number(digits);
    if (Number.isFinite(hour) && hour >= 0 && hour <= 23) {
      return `${digits}:00`;
    }
    return digits;
  }
  if (digits.length === 3) {
    return clampFourDigitClock(`0${digits}`);
  }
  return clampFourDigitClock(digits);
}

function clockFromDraft(raw: string): { hour: number; minute: number } | null {
  const normalized = normalizeTimeBlur(raw);
  if (isValidHhmm(normalized)) {
    const [hh, mm] = normalized.split(":");
    return { hour: Number(hh), minute: Number(mm) };
  }
  const withColon = /^(\d{1,2}):(\d{0,2})$/.exec(raw || "");
  if (withColon) {
    const hour = Number(withColon[1]);
    if (hour >= 0 && hour <= 23) {
      const minuteRaw = withColon[2];
      const minute = minuteRaw === "" ? 0 : Number(minuteRaw.padEnd(2, "0"));
      if (Number.isFinite(minute) && minute <= 59) {
        return { hour, minute };
      }
      return { hour, minute: 0 };
    }
  }
  const hourOnly = /^(\d{1,2})$/.exec(raw || "");
  if (hourOnly) {
    const hour = Number(hourOnly[1]);
    if (hour >= 0 && hour <= 23) return { hour, minute: 0 };
  }
  return null;
}

/** Wheel highlight: valid/partial draft, never `930 % 24` wrap. */
export function resolvePickerClock(raw: string, fallback: string): { hour: number; minute: number } {
  return clockFromDraft(raw) ?? clockFromDraft(fallback) ?? { hour: 10, minute: 0 };
}

function centerChildInViewport(viewport: HTMLElement | null, child: HTMLElement | null) {
  if (!viewport || !child) return;
  const next =
    viewport.scrollTop +
    (child.getBoundingClientRect().top - viewport.getBoundingClientRect().top) -
    viewport.clientHeight / 2 +
    child.offsetHeight / 2;
  viewport.scrollTo({ top: Math.max(0, next), behavior: "auto" });
}

/** Shift HH:mm by minutes and clamp to 00:00–23:55 (same day). */
export function shiftHhmm(hhmm: string, deltaMinutes: number): string {
  const parts = hhmm.split(":");
  const h = Number(parts[0]);
  const m = Number(parts[1] ?? 0);
  if (!Number.isFinite(h) || !Number.isFinite(m)) return hhmm;
  const total = Math.max(0, Math.min(23 * 60 + 55, h * 60 + m + deltaMinutes));
  const rh = Math.floor(total / 60);
  const rm = total % 60;
  return `${String(rh).padStart(2, "0")}:${String(rm).padStart(2, "0")}`;
}

function TimeClockPopover({
  opened,
  onOpenChange,
  ariaLabel,
  children,
}: {
  opened: boolean;
  onOpenChange: (open: boolean) => void;
  ariaLabel: string;
  children: ReactNode;
}) {
  return (
    <Box style={{ flexShrink: 0 }}>
      <Popover
        opened={opened}
        onChange={onOpenChange}
        position="bottom-end"
        shadow="md"
        radius="md"
        withinPortal
        zIndex={450}
        trapFocus
        withArrow
        middlewares={{ flip: true, shift: true }}
        transitionProps={{ duration: 0 }}
      >
        <Popover.Target>
          <ActionIcon
            variant="light"
            size={36}
            radius="md"
            aria-label={ariaLabel}
            aria-expanded={opened}
            aria-haspopup="dialog"
            onClick={() => onOpenChange(!opened)}
            style={{ boxShadow: "var(--shadow-soft-sm)", flexShrink: 0 }}
          >
            <IconClock size={18} stroke={1.5} />
          </ActionIcon>
        </Popover.Target>
        <Popover.Dropdown p="sm" role="dialog" aria-label={ariaLabel}>
          {opened ? children : null}
        </Popover.Dropdown>
      </Popover>
    </Box>
  );
}

function StaffCalTimeWheel({
  hourOptions,
  minuteOptions,
  pickerHour,
  selectedMinute,
  hoursViewportRef,
  minutesViewportRef,
  onPick,
  onClear,
  onDone,
  title,
  hint,
  hoursLabel,
  minutesLabel,
  clearLabel,
  doneLabel,
}: {
  hourOptions: number[];
  minuteOptions: number[];
  pickerHour: number;
  selectedMinute: number;
  hoursViewportRef: RefObject<HTMLDivElement | null>;
  minutesViewportRef: RefObject<HTMLDivElement | null>;
  onPick: (hour: number, minute: number) => void;
  onClear: () => void;
  onDone: () => void;
  title: string;
  hint: string;
  hoursLabel: string;
  minutesLabel: string;
  clearLabel: string;
  doneLabel: string;
}) {
  return (
    <Stack gap="sm" style={{ minWidth: 228, width: 260 }}>
      <Group justify="space-between" gap="xs" align="flex-start" wrap="nowrap">
        <Stack gap={2} style={{ flex: 1, minWidth: 0 }}>
          <Text size="sm" fw={700}>
            {title}
          </Text>
          <Text size="xs" c="dimmed">
            {hint}
          </Text>
        </Stack>
        <Button variant="light" size="xs" onClick={onClear} style={{ flexShrink: 0 }}>
          {clearLabel}
        </Button>
      </Group>
      <Group grow gap="xs" align="stretch" wrap="nowrap">
        <Stack gap={6} style={{ minWidth: 0 }}>
          <Text size="xs" c="dimmed" ta="center" fw={600}>
            {hoursLabel}
          </Text>
          <ScrollArea
            viewportRef={hoursViewportRef}
            className="staff-cal-time-scroll"
            style={{
              height: 240,
              borderRadius: "var(--radius-md)",
              background: "var(--bg-card-soft)",
              border: "1px solid var(--input-border)",
            }}
          >
            <Stack gap={6} p={10}>
              {hourOptions.map((h) => {
                const isSel = h === pickerHour;
                return (
                  <UnstyledButton
                    type="button"
                    key={h}
                    data-hour={h}
                    data-selected={isSel ? "true" : undefined}
                    aria-pressed={isSel}
                    className="staff-cal-time-slot"
                    onClick={() => onPick(h, selectedMinute)}
                  >
                    <Text
                      size="sm"
                      fw={700}
                      className="staff-cal-time-slot-label"
                      style={{
                        color: isSel ? "var(--staff-cal-time-selected-text)" : undefined,
                      }}
                    >
                      {String(h).padStart(2, "0")}
                    </Text>
                  </UnstyledButton>
                );
              })}
            </Stack>
          </ScrollArea>
        </Stack>
        <Stack gap={6} style={{ minWidth: 0 }}>
          <Text size="xs" c="dimmed" ta="center" fw={600}>
            {minutesLabel}
          </Text>
          <ScrollArea
            viewportRef={minutesViewportRef}
            className="staff-cal-time-scroll"
            style={{
              height: 240,
              borderRadius: "var(--radius-md)",
              background: "var(--bg-card-soft)",
              border: "1px solid var(--input-border)",
            }}
          >
            <Stack gap={6} p={10}>
              {minuteOptions.map((m5) => {
                const isSel = m5 === selectedMinute;
                return (
                  <UnstyledButton
                    type="button"
                    key={m5}
                    data-minute={m5}
                    data-selected={isSel ? "true" : undefined}
                    aria-pressed={isSel}
                    className="staff-cal-time-slot"
                    onClick={() => onPick(pickerHour, m5)}
                  >
                    <Text
                      size="sm"
                      fw={700}
                      className="staff-cal-time-slot-label"
                      style={{
                        color: isSel ? "var(--staff-cal-time-selected-text)" : undefined,
                      }}
                    >
                      {String(m5).padStart(2, "0")}
                    </Text>
                  </UnstyledButton>
                );
              })}
            </Stack>
          </ScrollArea>
        </Stack>
      </Group>
      <Group justify="flex-end">
        <Button onClick={onDone}>{doneLabel}</Button>
      </Group>
    </Stack>
  );
}

const WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

const CALENDAR_MODAL_STYLES = {
  overlay: { left: ADMIN_SHELL_NAVBAR_OFFSET },
  inner: { ...SHELL_MODAL_NAV_INNER_STYLE },
  content: {
    maxWidth: "100%",
    marginInline: "auto",
    flexShrink: 1,
    pointerEvents: "auto" as const,
  },
};

const CALENDAR_MODAL_NAV_SAFE = {
  ...ADMIN_NAV_SAFE_MODAL_PROPS,
  overlayProps: SHELL_OVERLAY_PROPS,
  styles: CALENDAR_MODAL_STYLES,
};

type CalendarModalState =
  | null
  | { mode: "create" }
  | { mode: "edit"; event: StaffCalendarEventResponse }
  | { mode: "details"; eventId: string };

export default function AdminStaffCalendarPage() {
  const { t } = useTranslation("schedule");
  const [searchParams, setSearchParams] = useSearchParams();
  const taskIdFromUrl = searchParams.get("task_id")?.trim() || "";
  const openCreateFromTask = searchParams.get("open_create") === "1";

  const [monthAnchor, setMonthAnchor] = useState(() => dayjs().startOf("month"));
  const fromIso = useMemo(
    // Send local wall-clock boundaries without timezone suffix.
    // Using toISOString() shifts date in UTC and can move month grid by one day.
    () => monthAnchor.startOf("month").startOf("day").format("YYYY-MM-DDTHH:mm:ss"),
    [monthAnchor]
  );
  const toIso = useMemo(
    () => monthAnchor.endOf("month").endOf("day").format("YYYY-MM-DDTHH:mm:ss"),
    [monthAnchor]
  );

  const { data: monthGrid, isLoading, isError, error } = useStaffCalendarMonthGrid(fromIso, toIso);
  const calendarWeekRows = useMemo(
    () => (monthGrid?.days?.length ? chunkCalendarWeeks(monthGrid.days) : []),
    [monthGrid?.days]
  );
  const createMut = useCreateStaffCalendarEvent();
  const updateMut = useUpdateStaffCalendarEvent();
  const ackMut = useAckStaffCalendarInvitation();
  const { data: adminSession } = useAdminSession();
  const canInviteParticipants =
    adminSession?.permissions?.includes("invite_staff_calendar_participants") ?? false;
  const canEditCalendar = adminSession?.permissions?.includes("manage_staff_collab") ?? false;
  const canViewTasks = adminSession?.permissions?.includes("view_tasks") ?? false;
  const myAdminId = getAdminId();
  const { data: admins = [], isLoading: adminsLoading } = useAdminAdmins();
  const participantOptions = useMemo(
    () =>
      admins
        .filter((a) => a.employment_status === "active")
        .map((a) => ({
          value: a.id,
          label: displayPersonName(a.full_name?.trim() || a.email, a.id),
        })),
    [admins]
  );

  const hourOptions = useMemo(() => Array.from({ length: 24 }, (_, i) => i), []);
  const minuteOptions = useMemo(() => Array.from({ length: 12 }, (_, i) => i * 5), []);

  const [modal, setModal] = useState<CalendarModalState>(null);
  const [autoOpenedFromTaskId, setAutoOpenedFromTaskId] = useState<string | null>(null);
  const [lastCreatedEvent, setLastCreatedEvent] = useState<{ dayIso: string; title: string } | null>(null);

  const shouldFetchTaskDetails = openCreateFromTask && !!taskIdFromUrl && canViewTasks;
  const { data: taskDetails, isLoading: taskDetailsLoading } = useAdminTaskDetails(
    shouldFetchTaskDetails ? taskIdFromUrl : null
  );

  const [dayDrawerDate, setDayDrawerDate] = useState<string | null>(null);
  const dayForDrawer = useMemo(() => {
    if (!dayDrawerDate) return null;
    return monthGrid?.days.find((d) => d.date === dayDrawerDate) ?? null;
  }, [dayDrawerDate, monthGrid]);

  const detailsEventId = modal?.mode === "details" ? modal.eventId : null;
  const {
    data: eventDetails,
    isLoading: detailsLoading,
    isError: detailsIsError,
    error: detailsError,
  } = useStaffCalendarEventDetails(detailsEventId);

  const [flashUntilMs, setFlashUntilMs] = useState<number>(0);
  const lastSignalsRef = useRef<{ unseen: number; remindersDueNow: number } | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const seenReminderEventIdsRef = useRef<Set<string>>(new Set());
  const [soundEnabled, setSoundEnabled] = useState(() => {
    if (typeof window === "undefined") return false;
    return window.localStorage.getItem("staff_cal_sound_enabled") === "true";
  });

  const playSound3x = () => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = audioCtxRef.current ?? new AudioCtx();
      audioCtxRef.current = ctx;
      void ctx.resume?.();

      const beep = (freq: number, durationMs: number) => {
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = "sine";
        osc.frequency.value = freq;
        gain.gain.value = 0.0001;
        osc.connect(gain);
        gain.connect(ctx.destination);

        const t0 = ctx.currentTime;
        gain.gain.setValueAtTime(0.08, t0);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + durationMs / 1000);
        osc.start(t0);
        osc.stop(t0 + durationMs / 1000);
      };

      // "sound 3 + visual": 3 short beeps.
      [0, 700, 1400].forEach((delay, idx) => {
        window.setTimeout(() => beep(880 + idx * 40, 120), delay);
      });
    } catch {
      // Autoplay restrictions may block WebAudio; silently ignore.
    }
  };

  const enableSound = () => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) {
        setSoundEnabled(false);
        return;
      }
      const ctx = audioCtxRef.current ?? new AudioCtx();
      audioCtxRef.current = ctx;
      void ctx.resume?.();
      window.localStorage.setItem("staff_cal_sound_enabled", "true");
      setSoundEnabled(true);
      // User-gesture beep (short, quiet) to confirm audio is unblocked.
      playSound3x();
    } catch {
      setSoundEnabled(false);
    }
  };

  useEffect(() => {
    lastSignalsRef.current = null;
    seenReminderEventIdsRef.current = new Set();
  }, [fromIso, toIso]);

  useEffect(() => {
    if (!monthGrid) return;
    const { unseen_invites_count, reminders_due_now_count } = monthGrid.notification_signals;
    const prev = lastSignalsRef.current;
    if (!prev) {
      lastSignalsRef.current = { unseen: unseen_invites_count, remindersDueNow: reminders_due_now_count };
      return;
    }

    const unseenIncreased = unseen_invites_count > prev.unseen;
    const remindersIncreased = reminders_due_now_count > prev.remindersDueNow;
    if (unseenIncreased || remindersIncreased) setFlashUntilMs(Date.now() + 4000);
    lastSignalsRef.current = { unseen: unseen_invites_count, remindersDueNow: reminders_due_now_count };
  }, [
    monthGrid?.notification_signals.unseen_invites_count,
    monthGrid?.notification_signals.reminders_due_now_count,
    monthGrid,
  ]);

  useEffect(() => {
    if (!monthGrid) return;
    if (!soundEnabled) return;
    // Beep once per reminder event id.
    const dueNowIds = new Set<string>();
    for (const day of monthGrid.days ?? []) {
      for (const id of day.reminder_event_ids ?? []) dueNowIds.add(String(id));
    }
    const seen = seenReminderEventIdsRef.current;
    let hasNew = false;
    for (const id of dueNowIds) {
      if (!seen.has(id)) {
        seen.add(id);
        hasNew = true;
      }
    }
    if (hasNew) {
      setFlashUntilMs(Date.now() + 4000);
      playSound3x();
    }
  }, [monthGrid, soundEnabled]);

  useEffect(() => {
    if (!lastCreatedEvent) return;
    const t = window.setTimeout(() => setLastCreatedEvent(null), 3500);
    return () => window.clearTimeout(t);
  }, [lastCreatedEvent]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [allDay, setAllDay] = useState(false);
  /** Строка минут: "0" — без напоминания; иначе число минут до начала (Celery). */
  const [reminderMinutes, setReminderMinutes] = useState<string>("15");
  /** Связь с задачей: только при создании; при редактировании только просмотр (PATCH без task_id). */
  const [linkedTaskId, setLinkedTaskId] = useState<string>("");
  const [linkedTaskTitle, setLinkedTaskTitle] = useState<string>("");
  const [linkTaskOpen, setLinkTaskOpen] = useState(false);
  const [taskSearch, setTaskSearch] = useState("");
  const [taskSource, setTaskSource] = useState<"open" | "my" | "all">("open");
  /** Приглашённые сотрудники (нужно право invite_staff_calendar_participants). */
  const [participantAdminIds, setParticipantAdminIds] = useState<string[]>([]);
  const [formError, setFormError] = useState<string | null>(null);
  const [createSelectedDayIso, setCreateSelectedDayIso] = useState(() => dayjs().format("YYYY-MM-DD"));
  const [createMonthAnchor, setCreateMonthAnchor] = useState(() => dayjs().startOf("month"));
  const [createStartTime, setCreateStartTime] = useState<string>("");
  const [createEndTime, setCreateEndTime] = useState<string>("");
  const [timeConflictWarning, setTimeConflictWarning] = useState<string | null>(null);
  const [timePickerKind, setTimePickerKind] = useState<"start" | "end" | null>(null);
  const [hideCreateMonthPicker, setHideCreateMonthPicker] = useState(false);

  const createDayForOverlap = useMemo(() => {
    return monthGrid?.days.find((d) => d.date === createSelectedDayIso) ?? null;
  }, [monthGrid, createSelectedDayIso]);

  const dayEventsCount = dayForDrawer?.events.length ?? 0;
  const dayDrawerSize = dayEventsCount === 0 ? "sm" : dayEventsCount >= 10 ? "lg" : "md";
  const dayDrawerScrollHeight = dayEventsCount === 0 ? 320 : Math.min(720, 260 + dayEventsCount * 70);

  const openCreateWithDayAndStartHour = (dayIso: string, hour: number) => {
    resetForm();
    setCreateSelectedDayIso(dayIso);
    setCreateMonthAnchor(dayjs(dayIso).startOf("month"));
    setAllDay(false);
    const start = dayjs(dayIso).hour(hour).minute(0).second(0).millisecond(0);
    const end = start.add(1, "hour");
    // Clamp to keep same day and valid range.
    const endClamped = end.isSame(start, "day") ? end : start.hour(23).minute(45);
    setCreateStartTime(start.format("HH:mm"));
    setCreateEndTime(endClamped.format("HH:mm"));
    setHideCreateMonthPicker(true);
    setModal({ mode: "create" });
  };

  useEffect(() => {
    if (!taskIdFromUrl) return;
    setLinkedTaskId(taskIdFromUrl);
    if (taskDetails?.title) setLinkedTaskTitle(taskDetails.title);
  }, [taskIdFromUrl, taskDetails?.title]);

  const resetForm = useCallback((initialDayIso?: string) => {
    const dayIso = initialDayIso ?? dayjs().format("YYYY-MM-DD");
    setTitle("");
    setDescription("");
    setAllDay(false);
    setReminderMinutes("15");
    setLinkedTaskId("");
    setLinkedTaskTitle("");
    setParticipantAdminIds([]);
    setFormError(null);
    setCreateSelectedDayIso(dayIso);
    setCreateMonthAnchor(dayjs(dayIso).startOf("month"));
    setCreateStartTime("");
    setCreateEndTime("");
    setTimeConflictWarning(null);
    setTimePickerKind(null);
    setHideCreateMonthPicker(false);
    setTaskSearch("");
    setTaskSource("open");
  }, []);

  const openCreate = useCallback(() => {
    const today = dayjs();
    const initialDayIso = monthAnchor.isSame(today, "month")
      ? today.format("YYYY-MM-DD")
      : monthAnchor.startOf("month").format("YYYY-MM-DD");
    resetForm(initialDayIso);
    setHideCreateMonthPicker(false);
    setModal({ mode: "create" });
  }, [monthAnchor, resetForm]);

  const openCreateWithDay = useCallback((dayIso: string) => {
    resetForm(dayIso);
    setCreateSelectedDayIso(dayIso);
    setCreateMonthAnchor(dayjs(dayIso).startOf("month"));
    // Время оставляем пустым: пользователь выбирает через поле/«часики».
    setCreateStartTime("");
    setCreateEndTime("");
    // День уже выбран по клику — сворачиваем выбор месяца, оставляя только "Дата".
    setHideCreateMonthPicker(true);
    setModal({ mode: "create" });
  }, [resetForm]);

  // Kanban "В календарь" -> открыть modal create и предзаполнить (task_id, дата, участники).
  useEffect(() => {
    if (!openCreateFromTask) return;
    if (!taskIdFromUrl) return;
    if (autoOpenedFromTaskId === taskIdFromUrl) return;
    if (isLoading) return;
    if (!monthGrid) return;
    if (shouldFetchTaskDetails && taskDetailsLoading) return;
    if (canInviteParticipants && adminsLoading) return;

    const dueDayIso = taskDetails?.due_at ? dayjs(taskDetails.due_at).format("YYYY-MM-DD") : null;

    if (dueDayIso) {
      const dueMonthAnchor = dayjs(dueDayIso).startOf("month");
      if (!monthAnchor.isSame(dueMonthAnchor, "month")) {
        // Чтобы overlap-дизейблы работали для предзаполненного дня, загрузим month-grid нужного месяца.
        setMonthAnchor(dueMonthAnchor);
        return;
      }
      openCreateWithDay(dueDayIso);
    } else {
      openCreate();
    }

    setLinkedTaskId(taskIdFromUrl);

    if (canInviteParticipants && taskDetails) {
      const assigneeIds = (taskDetails.assignee_ids && taskDetails.assignee_ids.length > 0)
        ? taskDetails.assignee_ids
        : taskDetails.assignee_id
          ? [taskDetails.assignee_id]
          : [];
      const allowedActiveAdminIds = new Set(participantOptions.map((p) => p.value));
      setParticipantAdminIds(assigneeIds.filter((id) => allowedActiveAdminIds.has(id)));
    } else {
      setParticipantAdminIds([]);
    }

    setAutoOpenedFromTaskId(taskIdFromUrl);
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.delete("open_create");
        return next;
      },
      { replace: true },
    );
  }, [
    openCreateFromTask,
    taskIdFromUrl,
    autoOpenedFromTaskId,
    openCreate,
    openCreateWithDay,
    isLoading,
    monthGrid,
    monthAnchor,
    shouldFetchTaskDetails,
    taskDetailsLoading,
    canInviteParticipants,
    adminsLoading,
    taskDetails,
    participantOptions,
  ]);

  const openDetails = (eventId: string) => {
    setModal({ mode: "details", eventId });
  };

  const openEdit = (ev: StaffCalendarEventResponse) => {
    setFormError(null);
    setTitle(ev.title);
    setDescription(ev.description ?? "");
    const startStamp = dayjs(ev.starts_at).format("YYYY-MM-DDTHH:mm");
    const endStamp = dayjs(ev.ends_at).format("YYYY-MM-DDTHH:mm");
    const [startDate, startTime] = startStamp.split("T");
    const [, endTime] = endStamp.split("T");
    setCreateSelectedDayIso(startDate);
    setCreateMonthAnchor(dayjs(startDate).startOf("month"));
    setCreateStartTime(ev.all_day ? "" : (startTime ?? ""));
    setCreateEndTime(ev.all_day ? "" : (endTime ?? ""));
    setHideCreateMonthPicker(true);
    setTimePickerKind(null);
    setAllDay(ev.all_day);
    const r = ev.reminder_minutes_before;
    setReminderMinutes(
      r == null || r <= 0 ? "0" : String(r)
    );
    setLinkedTaskId(ev.task_id ?? "");
    setLinkedTaskTitle("");
    setParticipantAdminIds(ev.participants?.map((p) => p.id) ?? []);
    setModal({ mode: "edit", event: ev });
  };

  const closeModal = () => {
    setModal(null);
    setFormError(null);
    setTimePickerKind(null);
  };

  const submitModal = () => {
    if (createMut.isPending || updateMut.isPending) return;
    setFormError(null);
    const eventDateIso = createSelectedDayIso;
    let starts: dayjs.Dayjs;
    let ends: dayjs.Dayjs;

    if (!title.trim()) {
      setFormError(t("staffCal.errors.titleRequired"));
      return;
    }

    if (allDay) {
      starts = dayjs(eventDateIso)
        .hour(0)
        .minute(0)
        .second(0)
        .millisecond(0);
      // All-day is still stored as a time range in the DB.
      ends = dayjs(eventDateIso)
        .hour(23)
        .minute(45)
        .second(0)
        .millisecond(0);
    } else {
      const startHmm = normalizeTimeBlur(createStartTime);
      const endHmm = normalizeTimeBlur(createEndTime);
      if (startHmm !== createStartTime) setCreateStartTime(startHmm);
      if (endHmm !== createEndTime) setCreateEndTime(endHmm);
      if (!startHmm || !endHmm) {
        setFormError(t("staffCal.errors.needTimes"));
        return;
      }
      if (!isValidHhmm(startHmm) || !isValidHhmm(endHmm)) {
        setFormError(t("staffCal.errors.badTime"));
        return;
      }
      starts = dayjs(`${eventDateIso}T${startHmm}`);
      ends = dayjs(`${eventDateIso}T${endHmm}`);
    }

    if (!starts.isValid() || !ends.isValid()) {
      setFormError(t("staffCal.errors.badTime"));
      return;
    }
    if (ends.isBefore(starts) || ends.isSame(starts)) {
      setFormError(t("staffCal.errors.endAfterStart"));
      return;
    }

    // Same rule as backend `_assert_calendar_event_no_overlap` (edit excludes self).
    // Inputs stay enabled (D4 warning); save still refuses a colliding interval.
    if (eventsOverlap(starts, ends)) {
      setFormError(t("staffCal.errors.overlap"));
      return;
    }

    const r = Number.parseInt(reminderMinutes, 10);
    const reminder_minutes_before = Number.isFinite(r) ? r : 15;
    const tid = linkedTaskId.trim();

    if (modal?.mode === "create") {
      createMut.mutate(
        {
          title: title.trim(),
          description: description.trim() || null,
          starts_at: starts.toISOString(),
          ends_at: ends.toISOString(),
          all_day: allDay,
          reminder_minutes_before,
          task_id: tid || null,
          ...(canInviteParticipants && participantAdminIds.length > 0
            ? { participant_admin_ids: participantAdminIds }
            : {}),
        },
        {
          onSuccess: (created) => {
            const createdStarts = dayjs(created.starts_at);
            const createdDayIso = createdStarts.format("YYYY-MM-DD");
            setMonthAnchor(createdStarts.startOf("month"));
            setDayDrawerDate(createdDayIso);
            setLastCreatedEvent({ dayIso: createdDayIso, title: created.title });
            setFlashUntilMs(Date.now() + 4000);
            closeModal();
            resetForm();
            if (taskIdFromUrl) {
              setSearchParams((prev) => {
                const next = new URLSearchParams(prev);
                next.delete("task_id");
                return next;
              });
            }
          },
          onError: (e: unknown) => {
            const err = e as any;
            const base = e instanceof Error ? e.message : t("staffCal.errors.createFailed");
            const traceId: string | undefined = err?.traceId ?? err?.details?.trace_id ?? err?.details?.traceId;
            setFormError(traceId ? `${base} (trace_id: ${traceId})` : base);
          },
        }
      );
      return;
    }

    if (modal?.mode === "edit") {
      const body: {
        title: string;
        description: string | null;
        starts_at: string;
        ends_at: string;
        all_day: boolean;
        reminder_minutes_before: number;
        task_id: string | null;
        participant_admin_ids?: string[];
      } = {
        title: title.trim(),
        description: description.trim() || null,
        starts_at: starts.toISOString(),
        ends_at: ends.toISOString(),
        all_day: allDay,
        reminder_minutes_before: reminder_minutes_before <= 0 ? 0 : reminder_minutes_before,
        task_id: tid || null,
      };
      if (canInviteParticipants) {
        body.participant_admin_ids = participantAdminIds;
      }
      updateMut.mutate(
        { eventId: modal.event.id, body },
        {
          onSuccess: () => {
            closeModal();
            resetForm();
          },
          onError: (e: unknown) => {
            const err = e as any;
            const base = e instanceof Error ? e.message : t("staffCal.errors.saveFailed");
            const traceId: string | undefined = err?.traceId ?? err?.details?.trace_id ?? err?.details?.traceId;
            setFormError(traceId ? `${base} (trace_id: ${traceId})` : base);
          },
        }
      );
    }
  };

  const pending = createMut.isPending || updateMut.isPending;

  const tasksOpenQ = useAdminTasksOpen({
    enabled: linkTaskOpen && canViewTasks && taskSource === "open",
  });
  const tasksMyQ = useAdminTasksMyFocus(myAdminId || null, {
    enabled: linkTaskOpen && canViewTasks && taskSource === "my",
  });
  const tasksAllQ = useAdminTasksList(undefined, {
    enabled: linkTaskOpen && canViewTasks && taskSource === "all",
  });

  const taskCandidates = useMemo(() => {
    if (!canViewTasks) return [];
    if (taskSource === "open") return tasksOpenQ.data ?? [];
    if (taskSource === "my") return tasksMyQ.data ?? [];
    return tasksAllQ.data ?? [];
  }, [canViewTasks, taskSource, tasksOpenQ.data, tasksMyQ.data, tasksAllQ.data]);

  const filteredTaskCandidates = useMemo(() => {
    const q = taskSearch.trim().toLowerCase();
    if (!q) return taskCandidates;
    return taskCandidates.filter((t: any) => String(t.title ?? "").toLowerCase().includes(q));
  }, [taskCandidates, taskSearch]);

  const isDetailsModalCreator = useMemo(() => {
    if (modal?.mode !== "details" || !eventDetails?.event?.created_by?.id || !myAdminId) return false;
    return String(eventDetails.event.created_by.id) === String(myAdminId);
  }, [modal?.mode, eventDetails, myAdminId]);

  const createDayEventsForOverlap = createDayForOverlap?.events ?? [];

  const hoursPickerScrollRef = useRef<HTMLDivElement | null>(null);
  const minutesPickerScrollRef = useRef<HTMLDivElement | null>(null);

  const eventsOverlap = (rangeStart: dayjs.Dayjs, rangeEnd: dayjs.Dayjs) => {
    // Half-open interval overlap: [start, end)
    if (!rangeStart.isValid() || !rangeEnd.isValid()) return true;
    if (!rangeEnd.isAfter(rangeStart)) return true;
    const editingId = modal?.mode === "edit" ? String(modal.event.id) : null;
    return createDayEventsForOverlap.some((ev) => {
      if (editingId && String(ev.id) === editingId) return false;
      const es = dayjs(ev.starts_at);
      const ee = dayjs(ev.ends_at);
      return rangeStart.isBefore(ee) && rangeEnd.isAfter(es);
    });
  };

  const updateTimeConflictWarning = (nextStart: string, nextEnd: string) => {
    if (!nextStart || !nextEnd) {
      setTimeConflictWarning(null);
      return;
    }
    const s = dayjs(`${createSelectedDayIso}T${nextStart}`);
    const e = dayjs(`${createSelectedDayIso}T${nextEnd}`);
    if (!isValidHhmm(nextStart) || !isValidHhmm(nextEnd) || !s.isValid() || !e.isValid() || !e.isAfter(s)) {
      setTimeConflictWarning(null);
      return;
    }
    setTimeConflictWarning(eventsOverlap(s, e) ? t("staffCal.overlapWarning") : null);
  };

  const pickerTimeStr =
    timePickerKind === "start"
      ? createStartTime
      : timePickerKind === "end"
        ? createEndTime
        : "";

  let pickerFallback = "10:00";
  if (timePickerKind === "end" && createStartTime) {
    const startNorm = normalizeTimeBlur(createStartTime);
    if (isValidHhmm(startNorm)) pickerFallback = shiftHhmm(startNorm, 60);
  }
  if (timePickerKind === "start" && createEndTime) {
    const endNorm = normalizeTimeBlur(createEndTime);
    if (isValidHhmm(endNorm)) pickerFallback = shiftHhmm(endNorm, -60);
  }

  const pickerClock = resolvePickerClock(pickerTimeStr, pickerFallback);
  const pickerHour = pickerClock.hour;
  const pickerMinute = pickerClock.minute;
  const pickerMinuteIndex = ((Math.round(pickerMinute / 5) % 12) + 12) % 12;

  const applyPickerTime = (nextHour: number, nextMinute: number) => {
    const hh = String((nextHour + 24) % 24).padStart(2, "0");
    const mm = String((nextMinute + 60) % 60).padStart(2, "0");
    const next = `${hh}:${mm}`;
    if (timePickerKind === "start") {
      setCreateStartTime(next);
      const endNorm = normalizeTimeBlur(createEndTime);
      const endUsable = isValidHhmm(endNorm) ? endNorm : "";
      const endNext = !endUsable || endUsable <= next ? shiftHhmm(next, 60) : endUsable;
      if (endNext !== createEndTime) setCreateEndTime(endNext);
      updateTimeConflictWarning(next, endNext);
    }
    if (timePickerKind === "end") {
      setCreateEndTime(next);
      const startNorm = normalizeTimeBlur(createStartTime);
      const startUsable = isValidHhmm(startNorm) ? startNorm : "";
      const startNext = !startUsable || startUsable >= next ? shiftHhmm(next, -60) : startUsable;
      if (startNext !== createStartTime) setCreateStartTime(startNext);
      updateTimeConflictWarning(startNext, next);
    }
    setHideCreateMonthPicker(true);
  };

  useEffect(() => {
    if ((modal?.mode !== "create" && modal?.mode !== "edit") || timePickerKind === null) return;
    let inner = 0;
    const outer = window.requestAnimationFrame(() => {
      inner = window.requestAnimationFrame(() => {
        const hoursRoot = hoursPickerScrollRef.current;
        const minutesRoot = minutesPickerScrollRef.current;
        const hourEl = hoursRoot?.querySelector(`[data-hour="${pickerHour}"]`) as HTMLElement | null;
        const minuteEl = minutesRoot?.querySelector(
          `[data-minute="${pickerMinuteIndex * 5}"]`,
        ) as HTMLElement | null;
        centerChildInViewport(hoursRoot, hourEl);
        centerChildInViewport(minutesRoot, minuteEl);
      });
    });
    return () => {
      window.cancelAnimationFrame(outer);
      window.cancelAnimationFrame(inner);
    };
    // Center once when the popover opens or the field switches. Native list scroll stays free after that.
    // pickerHour/minute used only as an open-time snapshot (intentional narrow deps).
  }, [modal?.mode, timePickerKind]);

  return (
    <Stack gap="md" className="staff-cal-page">
      <ContextBar title={t("staffCal.title")} />
      <Text size="sm" c="dimmed">{t("staffCal.intro")}</Text>
      <Group gap="xs" wrap="wrap">
        <Badge variant="light" color={soundEnabled ? "teal" : "gray"}>
          {soundEnabled ? t("staffCal.soundOn") : t("staffCal.soundOff")}
        </Badge>
        {!soundEnabled ? (
          <Button size="xs" variant="light" onClick={enableSound}>
            {t("staffCal.enableSound")}
          </Button>
        ) : null}
      </Group>
      {lastCreatedEvent ? (
        <Text size="sm" c="dimmed" style={{ color: "var(--accent-teal)" }}>
          {t("staffCal.createdEvent", { title: lastCreatedEvent.title, date: dayjs(lastCreatedEvent.dayIso).format("DD.MM.YYYY") })}
        </Text>
      ) : null}
      <Box className="staff-cal-toolbar">
        <Group gap="xs">
          <Button variant="default" radius="md" onClick={() => setMonthAnchor((m) => m.subtract(1, "month"))}>
            {"<<"}
          </Button>
          <Button variant="default" radius="md" onClick={() => setMonthAnchor(dayjs().startOf("month"))}>
            {t("staffCal.today")}
          </Button>
        </Group>
        <Text size="sm" fw={700} style={{ letterSpacing: "0.02em" }}>
          {monthAnchor.format("MMMM YYYY")}
        </Text>
        <Group gap="xs">
          <Button variant="default" radius="md" onClick={() => setMonthAnchor((m) => m.add(1, "month"))}>
            {">>"}
          </Button>
          <Button radius="md" onClick={openCreate}>
            {t("staffCal.newEvent")}
          </Button>
        </Group>
      </Box>

      {isLoading ? (
        <PageSkeleton variant="table" rows={10} />
      ) : isError ? (
        <QueryErrorAlert error={error} />
      ) : !monthGrid?.days?.length ? (
        <EmptyState title={t("staffCal.emptyTitle")} description={t("staffCal.emptyHint")} />
      ) : (
        <Stack gap="xs">
          <Box className="staff-cal-month-shell" style={{ overflow: "auto" }}>
            <Table
              withTableBorder
              withRowBorders
              striped={false}
              horizontalSpacing={6}
              verticalSpacing={6}
              style={{ tableLayout: "fixed", width: "100%" }}
            >
              <Table.Thead>
                <Table.Tr>
                  {WEEKDAY_KEYS.map((d) => (
                    <Table.Th key={d} style={{ width: `${100 / 7}%` }}>
                      <Text size="xs" c="dimmed" fw={600} ta="center">
                        {t(`calendar.weekdays.${d}`, { ns: "common" })}
                      </Text>
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {calendarWeekRows.map((week, wi) => (
                  <Table.Tr key={wi}>
                    {week.map((day, di) =>
                      day === null ? (
                        <Table.Td
                          key={`pad-${wi}-${di}`}
                          style={{
                            height: 120,
                            verticalAlign: "top",
                            padding: "var(--space-xs)",
                            backgroundColor: "var(--mantine-color-gray-0)",
                          }}
                        />
                      ) : (() => {
                        const sortedDayEvents = day.events
                          .slice()
                          .sort((a, b) => {
                            if (a.all_day !== b.all_day) return a.all_day ? -1 : 1;
                            return a.starts_at.localeCompare(b.starts_at);
                          });
                        const previewLines = sortedDayEvents.slice(0, 3);
                        const extraTotal = Math.max(0, sortedDayEvents.length - 3);
                        const flashDay =
                          flashUntilMs > Date.now() &&
                          (day.unseen_invite_count > 0 || day.reminder_event_ids.length > 0);
                        return (
                          <Table.Td
                            key={day.date}
                            className={`staff-cal-day-cell${flashDay ? " staff-cal-day-cell--flash" : ""}`}
                            style={{
                              height: 120,
                              minHeight: 120,
                              verticalAlign: "top",
                              padding: "var(--space-sm)",
                              cursor: "pointer",
                              backgroundColor: flashDay
                                ? undefined
                                : day.is_in_current_month
                                  ? "var(--bg-card)"
                                  : "var(--mantine-color-gray-0)",
                            }}
                            onClick={() => setDayDrawerDate(day.date)}
                          >
                            <Group justify="space-between" align="flex-start" wrap="nowrap" gap={4}>
                              <Text size="sm" fw={700} c="dark">
                                {day.is_in_current_month
                                  ? dayjs(day.date).date()
                                  : dayjs(day.date).format("D MMM")}
                              </Text>
                              <Group gap={4} wrap="nowrap">
                                {day.events.length > 0 ? (
                                  <Badge
                                    size="xs"
                                    variant="transparent"
                                    styles={{
                                      root: {
                                        backgroundColor: "var(--staff-cal-badge-count-bg)",
                                        color: "var(--staff-cal-badge-count-text)",
                                      },
                                    }}
                                  >
                                    {day.events.length}
                                  </Badge>
                                ) : null}
                                {day.unseen_invite_count > 0 ? (
                                  <Badge
                                    size="xs"
                                    variant="transparent"
                                    styles={{
                                      root: {
                                        backgroundColor: "var(--staff-cal-badge-unseen-bg)",
                                        color: "var(--staff-cal-badge-unseen-text)",
                                      },
                                    }}
                                  >
                                    {`+${day.unseen_invite_count}`}
                                  </Badge>
                                ) : null}
                                {day.reminder_event_ids.length > 0 ? (
                                  <Badge
                                    size="xs"
                                    variant="transparent"
                                    styles={{
                                      root: {
                                        backgroundColor: "var(--staff-cal-badge-reminder-bg)",
                                        color: "var(--staff-cal-badge-reminder-text)",
                                      },
                                    }}
                                    style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
                                  >
                                    <IconClock size={12} />
                                    {day.reminder_event_ids.length}
                                  </Badge>
                                ) : null}
                              </Group>
                            </Group>
                            {previewLines.length > 0 ? (
                              <Stack gap={4} mt={6}>
                                {previewLines.map((ev) => {
                                  const isUnseen = day.unseen_invite_event_ids.includes(ev.id);
                                  const isReminder = day.reminder_event_ids.includes(ev.id);
                                  const tc = staffEventTextColor(isReminder, isUnseen);
                                  return (
                                    <Box
                                      key={ev.id}
                                      className="staff-cal-event-chip"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        openDetails(ev.id);
                                      }}
                                      style={{
                                        ...staffEventChipSurface(isReminder, isUnseen),
                                        cursor: "pointer",
                                      }}
                                    >
                                      <Group gap={6} wrap="nowrap" align="center">
                                        {isReminder ? (
                                          <IconClock size={12} color="var(--staff-cal-chip-reminder-bar)" />
                                        ) : null}
                                        {isUnseen ? (
                                          <Badge
                                            size="xs"
                                            variant="transparent"
                                            styles={{
                                              root: {
                                                backgroundColor: "var(--staff-cal-badge-unseen-bg)",
                                                color: "var(--staff-cal-badge-unseen-text)",
                                              },
                                            }}
                                          >
                                            {t("staffCal.newBadge")}
                                          </Badge>
                                        ) : null}
                                        <Text
                                          size="xs"
                                          fw={600}
                                          lineClamp={1}
                                          style={{
                                            flex: 1,
                                            minWidth: 0,
                                            color: tc,
                                          }}
                                        >
                                          {ev.all_day ? t("staffCal.allDay") : dayjs(ev.starts_at).format("HH:mm")}{" "}
                                          {ev.title}
                                        </Text>
                                      </Group>
                                    </Box>
                                  );
                                })}
                                {extraTotal > 0 ? (
                                  <Text size="xs" c="dimmed">
                                    +{extraTotal}
                                  </Text>
                                ) : null}
                              </Stack>
                            ) : null}
                          </Table.Td>
                        );
                      })()
                    )}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Box>
        </Stack>
      )}

      <Modal
        {...CALENDAR_MODAL_NAV_SAFE}
        opened={!!dayDrawerDate}
        onClose={() => setDayDrawerDate(null)}
        title={dayDrawerDate ? t("staffCal.eventsOn", { date: dayjs(dayDrawerDate).format("DD MMM YYYY") }) : t("staffCal.events")}
        centered
        size={dayDrawerSize}
        radius="lg"
        classNames={{ content: "staff-cal-modal-content" }}
      >
        <Stack>
          {dayForDrawer ? (
            <Group justify="space-between" align="center">
              <Text size="sm" c="dimmed">
                {t("staffCal.quickAction")}
              </Text>
              <Button
                variant="filled"
                size="sm"
                radius="md"
                onClick={() => {
                  openCreateWithDay(dayForDrawer.date);
                  setDayDrawerDate(null);
                }}
              >
                {t("staffCal.addEvent")}
              </Button>
            </Group>
          ) : null}
          {!dayForDrawer ? (
            <PageSkeleton variant="table" rows={5} />
          ) : dayForDrawer.events.length === 0 ? (
            <Stack>
              <EmptyState title={t("staffCal.emptyDayTitle")} description={t("staffCal.emptyDayHint")} />
              <Text size="xs" c="dimmed" fw={700} mt={2}>
                {t("staffCal.quickHour")}
              </Text>
              <SimpleGrid cols={4} spacing={6} mt={4} style={{ marginLeft: "auto", marginRight: "auto" }}>
                {Array.from({ length: 23 }, (_, i) => i).map((h) => (
                  <Button
                    key={h}
                    size="xs"
                    variant="default"
                    onClick={() => {
                      openCreateWithDayAndStartHour(dayForDrawer.date, h);
                      setDayDrawerDate(null);
                    }}
                  >
                    {String(h).padStart(2, "0")}:00
                  </Button>
                ))}
              </SimpleGrid>
            </Stack>
          ) : (
            <ScrollArea className="staff-cal-time-scroll" style={{ height: dayDrawerScrollHeight }}>
              <Stack gap="xs">
                {dayForDrawer.events
                  .slice()
                  .sort((a, b) => a.starts_at.localeCompare(b.starts_at))
                  .map((ev) => {
                    const isReminder = dayForDrawer.reminder_event_ids.includes(ev.id);
                    const isUnseen = dayForDrawer.unseen_invite_event_ids.includes(ev.id);

                    const dayStart = dayjs(dayForDrawer.date).startOf("day");
                    const dayEnd = dayStart.add(1, "day");
                    const evStart = dayjs(ev.starts_at);
                    const evEnd = dayjs(ev.ends_at);
                    const clippedStart = evStart.isBefore(dayStart) ? dayStart : evStart;
                    const clippedEnd = evEnd.isAfter(dayEnd) ? dayEnd : evEnd;

                    const tc = staffEventTextColor(isReminder, isUnseen);
                    return (
                      <Box
                        key={ev.id}
                        className="staff-cal-event-chip"
                        onClick={() => openDetails(ev.id)}
                        style={{
                          ...staffEventChipSurface(isReminder, isUnseen),
                          cursor: "pointer",
                          padding: "var(--space-sm) var(--space-10)",
                        }}
                      >
                        <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
                          <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                            <Text fw={600} size="sm" lineClamp={2} style={{ color: tc }}>
                              {ev.title}
                            </Text>
                            <Text size="xs" c="dimmed" lineClamp={1}>
                              {ev.all_day
                                ? t("staffCal.allDay")
                                : `${clippedStart.format("DD.MM.YYYY HH:mm")} — ${clippedEnd.format("HH:mm")}`}
                            </Text>
                            <Group gap={6} wrap="wrap">
                              {isReminder ? (
                                <Badge
                                  size="xs"
                                  variant="light"
                                  color="gray"
                                  styles={{
                                    root: {
                                      backgroundColor: "var(--staff-cal-badge-reminder-bg)",
                                      color: "var(--staff-cal-badge-reminder-text)",
                                    },
                                  }}
                                >
                                  <IconClock size={12} style={{ marginRight: 6 }} />
                                  {t("staffCal.reminder")}
                                </Badge>
                              ) : null}
                              {isUnseen ? (
                                <Badge
                                  size="xs"
                                  variant="light"
                                  color="gray"
                                  styles={{
                                    root: {
                                      backgroundColor: "var(--staff-cal-badge-unseen-bg)",
                                      color: "var(--staff-cal-badge-unseen-text)",
                                    },
                                  }}
                                >
                                  {t("staffCal.newForMe")}
                                </Badge>
                              ) : null}
                            </Group>
                          </Stack>

                          {isUnseen &&
                          myAdminId &&
                          String(ev.created_by_admin_id) !== String(myAdminId) ? (
                            <Button
                              size="xs"
                              variant="default"
                              loading={ackMut.isPending}
                              onClick={(e) => {
                                e.stopPropagation();
                                ackMut.mutate(ev.id);
                              }}
                            >
                              {t("staffCal.acknowledge")}
                            </Button>
                          ) : null}
                        </Group>
                      </Box>
                    );
                  })}
              </Stack>
            </ScrollArea>
          )}
        </Stack>
      </Modal>

      <Modal
        {...CALENDAR_MODAL_NAV_SAFE}
        opened={modal !== null}
        onClose={closeModal}
        title={
          modal?.mode === "edit"
            ? t("staffCal.editEvent")
            : modal?.mode === "create"
              ? t("staffCal.newEvent")
              : t("staffCal.event")
        }
        centered
        size={modal?.mode === "details" ? "lg" : "56rem"}
        radius="lg"
        classNames={{ content: "staff-cal-modal-content" }}
        styles={{
          ...CALENDAR_MODAL_STYLES,
          content: {
            ...CALENDAR_MODAL_STYLES.content,
            display: "flex",
            flexDirection: "column",
          },
          body: {
            padding: 0,
          },
        }}
      >
        <Stack gap="sm" px="xl" pt="md" pb="xl">
              {modal?.mode === "details" ? (
                detailsLoading ? (
                  <PageSkeleton variant="table" rows={4} />
                ) : detailsIsError ? (
                  <QueryErrorAlert error={detailsError} />
                ) : !eventDetails ? null : (
                  <Stack gap="xs">
                    <Text fw={800} size="md">
                      {eventDetails.event.title}
                    </Text>
                    <Text size="sm" c="dimmed">
                      {dayjs(eventDetails.event.starts_at).format("DD.MM.YYYY HH:mm")} —{" "}
                      {dayjs(eventDetails.event.ends_at).format("DD.MM.YYYY HH:mm")}
                    </Text>
                    {eventDetails.event.description ? <Text size="sm">{eventDetails.event.description}</Text> : null}

                    <Group gap="xs" wrap="wrap">
                      {eventDetails.event.all_day ? <Badge size="sm">{t("staffCal.allDay")}</Badge> : null}
                      {eventDetails.event.task_id ? <Badge size="sm" color="teal">{t("staffCal.task")}</Badge> : null}
                      {eventDetails.reminder.reminder_minutes_before != null &&
                      eventDetails.reminder.reminder_minutes_before > 0 ? (
                        <Badge size="sm" variant="light" color="blue">
                          {t("staffCal.reminderIn", { count: eventDetails.reminder.reminder_minutes_before })}
                        </Badge>
                      ) : (
                        <Badge size="sm" variant="light" color="gray">
                          {t("staffCal.reminderOff")}
                        </Badge>
                      )}
                    </Group>

                    {eventDetails.event.participants?.length ? (
                      <Text size="sm" c="dimmed">
                        {t("staffCal.participants", { names: "" })}
                        {eventDetails.event.participants.map((p, idx) => (
                          <span key={p.id}>
                            <PersonNameLink kind="staff" id={p.id} label={p.full_name} />
                            {idx < (eventDetails.event.participants?.length ?? 0) - 1 ? ", " : ""}
                          </span>
                        ))}
                      </Text>
                    ) : null}

                    {eventDetails.creator_ack_summary ? (
                      <Text size="sm" c="dimmed">
                        {t("staffCal.acked", {
                          done: eventDetails.creator_ack_summary.acknowledged_participants,
                          total: eventDetails.creator_ack_summary.total_participants,
                        })}
                      </Text>
                    ) : null}
                  </Stack>
                )
              ) : (
                <>
                  {formError ? (
                    <Text size="sm" c="red">
                      {formError}
                    </Text>
                  ) : null}

                  <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
                    <Stack gap="sm">
                      <TextInput label={t("staffCal.eventTitle")} value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
                      <Textarea
                        label={t("staffCal.description")}
                        value={description}
                        onChange={(e) => setDescription(e.currentTarget.value)}
                        minRows={6}
                      />
                      {canInviteParticipants ? (
                        <MultiSelect
                          label={t("staffCal.meetingParticipants")}
                          description={
                            modal?.mode === "edit"
                              ? t("staffCal.replaceListHint")
                              : t("staffCal.whoSeesHint")
                          }
                          placeholder={t("staffCal.staffPlaceholder")}
                          data={participantOptions}
                          value={participantAdminIds}
                          onChange={setParticipantAdminIds}
                          searchable
                          hidePickedOptions
                          clearable
                          comboboxProps={{ withinPortal: true }}
                        />
                      ) : (
                        <Text size="xs" c="dimmed">
                          {t("staffCal.inviteNeedRight")}
                        </Text>
                      )}
                      <Switch
                        label={t("staffCal.allDay")}
                        aria-label={t("staffCal.allDay")}
                        checked={allDay}
                        onChange={(e) => {
                          const checked = e.currentTarget.checked;
                          setAllDay(checked);
                          if (!checked) {
                            setCreateStartTime("");
                            setCreateEndTime("");
                          }
                        }}
                      />
                      <Select
                        label={t("staffCal.reminderLabel")}
                        description={t("staffCal.reminderHint")}
                        data={[
                          { value: "0", label: t("staffCal.remindNone") },
                          { value: "5", label: t("staffCal.remind5") },
                          { value: "15", label: t("staffCal.remind15") },
                          { value: "30", label: t("staffCal.remind30") },
                          { value: "60", label: t("staffCal.remind60") },
                          { value: "120", label: t("staffCal.remind120") },
                          { value: "1440", label: t("staffCal.remind1440") },
                        ]}
                        value={reminderMinutes}
                        onChange={(v) => setReminderMinutes(v ?? "15")}
                      />
                    </Stack>

                    <Stack gap="sm">
                      {hideCreateMonthPicker ? (
                            <Group justify="space-between" align="center">
                              <Stack gap={0}>
                                <Text size="sm" fw={700}>
                                  {t("staffCal.date")}
                                </Text>
                                <Text size="xs" c="dimmed">
                                  {dayjs(createSelectedDayIso).format("DD.MM.YYYY")}
                                </Text>
                              </Stack>
                              <Button
                                variant="subtle"
                                size="xs"
                                onClick={() => setHideCreateMonthPicker(false)}
                                style={{ background: "var(--bg-card)", boxShadow: "var(--shadow-soft-sm)" }}
                              >
                                {t("staffCal.change")}
                              </Button>
                            </Group>
                          ) : (
                            <>
                              <Text size="sm" fw={700}>
                                {t("staffCal.date")}
                              </Text>
                              <Box mt={6}>
                                <CompactMonthPicker
                                  value={createSelectedDayIso}
                                  onChange={(iso) => {
                                    setCreateSelectedDayIso(iso);
                                    setCreateMonthAnchor(dayjs(iso).startOf("month"));
                                  }}
                                  monthAnchor={createMonthAnchor}
                                  onMonthAnchorChange={setCreateMonthAnchor}
                                  size="comfortable"
                                />
                              </Box>
                            </>
                          )}

                          {allDay ? (
                            <Text size="xs" c="dimmed">
                              {t("staffCal.allDayNoTime")}
                            </Text>
                          ) : (
                            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                              <Box>
                                <Text size="sm" fw={700}>
                                  {t("staffCal.startTime")}
                                </Text>
                                <Group mt={6} grow align="flex-end" gap="xs" wrap="nowrap">
                                  <TextInput
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="off"
                                    spellCheck={false}
                                    maxLength={5}
                                    placeholder="09:30"
                                    value={createStartTime}
                                    onChange={(e) => {
                                      const next = formatTimeDraft(e.currentTarget.value || "", createStartTime);
                                      setCreateStartTime(next);
                                      if (!next) {
                                        setTimeConflictWarning(null);
                                        return;
                                      }
                                      updateTimeConflictWarning(next, createEndTime);
                                    }}
                                    onBlur={() => {
                                      const next = normalizeTimeBlur(createStartTime);
                                      setCreateStartTime(next);
                                      updateTimeConflictWarning(next, createEndTime);
                                    }}
                                    styles={{
                                      root: { flex: 1, minWidth: 0 },
                                      input: {
                                        background: "var(--bg-card)",
                                        borderRadius: "var(--radius-md)",
                                        boxShadow: "var(--shadow-soft-sm)",
                                        fontVariantNumeric: "tabular-nums",
                                        height: 36,
                                      },
                                    }}
                                  />
                                  <TimeClockPopover
                                    opened={timePickerKind === "start"}
                                    onOpenChange={(open) => setTimePickerKind(open ? "start" : null)}
                                    ariaLabel={t("staffCal.pickStartTime")}
                                  >
                                    {timePickerKind === "start" ? (
                                      <StaffCalTimeWheel
                                        hourOptions={hourOptions}
                                        minuteOptions={minuteOptions}
                                        pickerHour={pickerHour}
                                        selectedMinute={pickerMinuteIndex * 5}
                                        hoursViewportRef={hoursPickerScrollRef}
                                        minutesViewportRef={minutesPickerScrollRef}
                                        onPick={applyPickerTime}
                                        onClear={() => {
                                          setCreateStartTime("");
                                          setTimePickerKind(null);
                                        }}
                                        onDone={() => setTimePickerKind(null)}
                                        title={t("staffCal.startTime")}
                                        hint={t("staffCal.wheelHint")}
                                        hoursLabel={t("staffCal.wheelHours")}
                                        minutesLabel={t("staffCal.wheelMinutes")}
                                        clearLabel={t("staffCal.clear")}
                                        doneLabel={t("staffCal.done")}
                                      />
                                    ) : null}
                                  </TimeClockPopover>
                                </Group>
                              </Box>

                              <Box>
                                <Text size="sm" fw={700}>
                                  {t("staffCal.endTime")}
                                </Text>
                                <Group mt={6} grow align="flex-end" gap="xs" wrap="nowrap">
                                  <TextInput
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="off"
                                    spellCheck={false}
                                    maxLength={5}
                                    placeholder="09:30"
                                    value={createEndTime}
                                    onChange={(e) => {
                                      const next = formatTimeDraft(e.currentTarget.value || "", createEndTime);
                                      setCreateEndTime(next);
                                      if (!next) {
                                        setTimeConflictWarning(null);
                                        return;
                                      }
                                      updateTimeConflictWarning(createStartTime, next);
                                    }}
                                    onBlur={() => {
                                      const next = normalizeTimeBlur(createEndTime);
                                      setCreateEndTime(next);
                                      updateTimeConflictWarning(createStartTime, next);
                                    }}
                                    styles={{
                                      root: { flex: 1, minWidth: 0 },
                                      input: {
                                        background: "var(--bg-card)",
                                        borderRadius: "var(--radius-md)",
                                        boxShadow: "var(--shadow-soft-sm)",
                                        fontVariantNumeric: "tabular-nums",
                                        height: 36,
                                      },
                                    }}
                                  />
                                  <TimeClockPopover
                                    opened={timePickerKind === "end"}
                                    onOpenChange={(open) => setTimePickerKind(open ? "end" : null)}
                                    ariaLabel={t("staffCal.pickEndTime")}
                                  >
                                    {timePickerKind === "end" ? (
                                      <StaffCalTimeWheel
                                        hourOptions={hourOptions}
                                        minuteOptions={minuteOptions}
                                        pickerHour={pickerHour}
                                        selectedMinute={pickerMinuteIndex * 5}
                                        hoursViewportRef={hoursPickerScrollRef}
                                        minutesViewportRef={minutesPickerScrollRef}
                                        onPick={applyPickerTime}
                                        onClear={() => {
                                          setCreateEndTime("");
                                          setTimePickerKind(null);
                                        }}
                                        onDone={() => setTimePickerKind(null)}
                                        title={t("staffCal.endTime")}
                                        hint={t("staffCal.wheelHint")}
                                        hoursLabel={t("staffCal.wheelHours")}
                                        minutesLabel={t("staffCal.wheelMinutes")}
                                        clearLabel={t("staffCal.clear")}
                                        doneLabel={t("staffCal.done")}
                                      />
                                    ) : null}
                                  </TimeClockPopover>
                                </Group>
                              </Box>
                            </SimpleGrid>
                          )}

                          {timeConflictWarning ? (
                            <Text size="xs" c="orange" mt={6}>
                              {t("staffCal.conflictContinue", { warning: timeConflictWarning })}
                            </Text>
                          ) : null}
                      {canViewTasks ? (
                        <Stack gap={6}>
                          <Text size="sm" fw={700}>
                            {t("staffCal.taskLink")}
                          </Text>
                          {linkedTaskId ? (
                            <Group justify="space-between" align="center" wrap="wrap" gap="sm">
                              <Group gap="xs" wrap="wrap">
                                <Badge color="teal" variant="light">
                                  {t("staffCal.task")}
                                </Badge>
                                <Text size="sm" fw={600}>
                                  {linkedTaskTitle?.trim() || t("staffCal.taskPicked")}
                                </Text>
                              </Group>
                              <Group gap="xs">
                                <Button variant="default" size="sm" onClick={() => setLinkTaskOpen(true)}>
                                  {t("staffCal.change")}
                                </Button>
                                <Button
                                  variant="subtle"
                                  color="red"
                                  size="sm"
                                  onClick={() => {
                                    setLinkedTaskId("");
                                    setLinkedTaskTitle("");
                                  }}
                                >
                                  {t("staffCal.unlink")}
                                </Button>
                              </Group>
                            </Group>
                          ) : (
                            <Group justify="space-between" align="center" wrap="wrap" gap="sm">
                              <Text size="sm" c="dimmed">
                                {t("staffCal.linkHint")}
                              </Text>
                              <Button size="sm" onClick={() => setLinkTaskOpen(true)}>
                                {t("staffCal.linkTask")}
                              </Button>
                            </Group>
                          )}
                        </Stack>
                      ) : (
                        <Text size="xs" c="dimmed">
                          {t("staffCal.needTasksRight")}
                        </Text>
                      )}
                    </Stack>
                  </SimpleGrid>
                </>
              )}
        </Stack>

        <Box
          px="xl"
          pt="sm"
          pb="md"
          style={{
            position: "sticky",
            bottom: 0,
            borderTop: "1px solid var(--divider)",
            background: "var(--overlay-glass-surface)",
            zIndex: 2,
          }}
        >
          {modal?.mode === "details" ? (
            <Group justify="space-between">
              {!isDetailsModalCreator ? (
                eventDetails?.invitation_acknowledged_at ? (
                  <Badge color="green" size="sm">
                    {t("staffCal.youAcked")}
                  </Badge>
                ) : eventDetails?.event?.id ? (
                  <Button
                    onClick={() =>
                      ackMut.mutate(eventDetails.event.id, {
                        onSuccess: () => closeModal(),
                      })
                    }
                    loading={ackMut.isPending}
                  >
                    {t("staffCal.ackSeen")}
                  </Button>
                ) : (
                  <Box />
                )
              ) : (
                <Box />
              )}

              <Group gap="xs">
                {canEditCalendar && eventDetails?.event ? (
                  <Button variant="light" onClick={() => openEdit(eventDetails.event)}>
                    {t("staffCal.change")}
                  </Button>
                ) : null}
                <Button variant="default" onClick={closeModal}>
                  {t("staffCal.close")}
                </Button>
              </Group>
            </Group>
          ) : (
            <Group justify="flex-end">
              <Button variant="default" onClick={closeModal}>
                {t("staffCal.cancel")}
              </Button>
              <Button
                onClick={submitModal}
                loading={pending}
                disabled={
                  pending ||
                  !title.trim() ||
                  (!allDay && !isReadyTimedRange(createStartTime, createEndTime, createSelectedDayIso))
                }
              >
                {modal?.mode === "edit" ? t("staffCal.save") : t("staffCal.create")}
              </Button>
            </Group>
          )}
        </Box>
      </Modal>

      <Modal
        {...CALENDAR_MODAL_NAV_SAFE}
        opened={linkTaskOpen}
        onClose={() => setLinkTaskOpen(false)}
        title={t("staffCal.linkTaskTitle")}
        centered
        size="lg"
        radius="lg"
        classNames={{ content: "staff-cal-modal-content" }}
      >
        <Stack gap="sm">
          <Group grow>
            <Select
              label={t("staffCal.list")}
              value={taskSource}
              onChange={(v) => setTaskSource((v as any) || "open")}
              data={[
                { value: "open", label: t("staffCal.openTasks") },
                { value: "my", label: t("staffCal.myTasks") },
                { value: "all", label: t("staffCal.allTasks") },
              ]}
              comboboxProps={{ withinPortal: true }}
            />
            <TextInput
              label={t("staffCal.search")}
              placeholder={t("staffCal.searchTaskPlaceholder")}
              value={taskSearch}
              onChange={(e) => setTaskSearch(e.currentTarget.value)}
            />
          </Group>

          <ScrollArea h={420} className="staff-cal-time-scroll">
            <Stack gap={6}>
              {filteredTaskCandidates.length === 0 ? (
                <EmptyState title={t("staffCal.nothingFound")} description={t("staffCal.nothingFoundHint")} />
              ) : (
                filteredTaskCandidates.slice(0, 200).map((taskRow: any) => (
                  <Button
                    key={taskRow.id}
                    variant={taskRow.id === linkedTaskId ? "filled" : "default"}
                    style={{ justifyContent: "space-between" }}
                    onClick={() => {
                      setLinkedTaskId(String(taskRow.id));
                      setLinkedTaskTitle(String(taskRow.title || "").trim());
                      setLinkTaskOpen(false);
                    }}
                  >
                    <span style={{ textAlign: "left", flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {String(taskRow.title || t("staffCal.task"))}
                    </span>
                    {"status" in taskRow && taskRow.status ? (
                      <Badge variant="light" color="gray" style={{ marginLeft: 10 }}>
                        {String(taskRow.status)}
                      </Badge>
                    ) : null}
                  </Button>
                ))
              )}
            </Stack>
          </ScrollArea>

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setLinkTaskOpen(false)}>
              {t("staffCal.close")}
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
