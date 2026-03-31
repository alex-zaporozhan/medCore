import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { useSearchParams } from "react-router-dom";
import {
  Box,
  Badge,
  ActionIcon,
  Button,
  Group,
  Modal,
  MultiSelect,
  Select,
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
import { ContextBar, EmptyState, PageSkeleton, QueryErrorAlert, CompactMonthPicker } from "@/shared/ui";
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
import { getAdminId } from "@/api/client";
import dayjs from "dayjs";
import "dayjs/locale/ru";

dayjs.locale("ru");

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

function formatTimeHHMMInput(raw: string): string {
  const digits = (raw || "").replace(/[^\d]/g, "").slice(0, 4);
  if (!digits) return "";
  // Common UX: "930" -> "09:30"
  const normalized = digits.length === 3 ? `0${digits}` : digits;
  if (normalized.length <= 2) return normalized;
  return `${normalized.slice(0, 2)}:${normalized.slice(2)}`;
}

type CalendarModalState =
  | null
  | { mode: "create" }
  | { mode: "edit"; event: StaffCalendarEventResponse }
  | { mode: "details"; eventId: string };

export default function AdminStaffCalendarPage() {
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
          label: a.full_name || a.email || a.id.slice(0, 8),
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

  useEffect(() => {
    lastSignalsRef.current = null;
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
    if (unseenIncreased || remindersIncreased) {
      setFlashUntilMs(Date.now() + 4000);
      playSound3x();
    }
    lastSignalsRef.current = { unseen: unseen_invites_count, remindersDueNow: reminders_due_now_count };
  }, [
    monthGrid?.notification_signals.unseen_invites_count,
    monthGrid?.notification_signals.reminders_due_now_count,
    monthGrid,
  ]);

  useEffect(() => {
    if (!lastCreatedEvent) return;
    const t = window.setTimeout(() => setLastCreatedEvent(null), 3500);
    return () => window.clearTimeout(t);
  }, [lastCreatedEvent]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startsLocal, setStartsLocal] = useState(() => dayjs().format("YYYY-MM-DDTHH:mm"));
  const [endsLocal, setEndsLocal] = useState(() => dayjs().add(1, "hour").format("YYYY-MM-DDTHH:mm"));
  const [allDay, setAllDay] = useState(false);
  /** Строка минут: "0" — без напоминания; иначе число минут до начала (Celery). */
  const [reminderMinutes, setReminderMinutes] = useState<string>("15");
  /** Связь с задачей: только при создании; при редактировании только просмотр (PATCH без task_id). */
  const [linkedTaskId, setLinkedTaskId] = useState<string>("");
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
    if (taskIdFromUrl) setLinkedTaskId(taskIdFromUrl);
  }, [taskIdFromUrl]);

  const resetForm = (initialDayIso?: string) => {
    const dayIso = initialDayIso ?? dayjs().format("YYYY-MM-DD");
    setTitle("");
    setDescription("");
    setStartsLocal(dayjs().format("YYYY-MM-DDTHH:mm"));
    setEndsLocal(dayjs().add(1, "hour").format("YYYY-MM-DDTHH:mm"));
    setAllDay(false);
    setReminderMinutes("15");
    setLinkedTaskId("");
    setParticipantAdminIds([]);
    setFormError(null);
    setCreateSelectedDayIso(dayIso);
    setCreateMonthAnchor(dayjs(dayIso).startOf("month"));
    setCreateStartTime("");
    setCreateEndTime("");
    setTimeConflictWarning(null);
    setTimePickerKind(null);
    setHideCreateMonthPicker(false);
  };

  const openCreate = () => {
    const today = dayjs();
    const initialDayIso = monthAnchor.isSame(today, "month")
      ? today.format("YYYY-MM-DD")
      : monthAnchor.startOf("month").format("YYYY-MM-DD");
    resetForm(initialDayIso);
    setHideCreateMonthPicker(false);
    setModal({ mode: "create" });
  };

  const openCreateWithDay = (dayIso: string) => {
    resetForm(dayIso);
    setCreateSelectedDayIso(dayIso);
    setCreateMonthAnchor(dayjs(dayIso).startOf("month"));
    // Время оставляем пустым: пользователь выбирает через поле/«часики».
    setCreateStartTime("");
    setCreateEndTime("");
    // День уже выбран по клику — сворачиваем выбор месяца, оставляя только "Дата".
    setHideCreateMonthPicker(true);
    setModal({ mode: "create" });
  };

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
    setSearchParams((prev) => {
      const next = new URLSearchParams(prev);
      next.delete("open_create");
      return next;
    });
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
    setStartsLocal(dayjs(ev.starts_at).format("YYYY-MM-DDTHH:mm"));
    setEndsLocal(dayjs(ev.ends_at).format("YYYY-MM-DDTHH:mm"));
    setAllDay(ev.all_day);
    const r = ev.reminder_minutes_before;
    setReminderMinutes(
      r == null || r <= 0 ? "0" : String(r)
    );
    setLinkedTaskId(ev.task_id ?? "");
    setParticipantAdminIds(ev.participants?.map((p) => p.id) ?? []);
    setModal({ mode: "edit", event: ev });
  };

  const closeModal = () => {
    setModal(null);
    setFormError(null);
    setTimePickerKind(null);
  };

  const submitModal = () => {
    setFormError(null);
    let starts = dayjs(startsLocal);
    let ends = dayjs(endsLocal);

    if (modal?.mode === "create") {
      if (!title.trim()) {
        setFormError("Введите заголовок.");
        return;
      }

      if (allDay) {
        starts = dayjs(createSelectedDayIso)
          .hour(0)
          .minute(0)
          .second(0)
          .millisecond(0);
        // "Весь день" в БД всё равно хранится как промежуток времени.
        ends = dayjs(createSelectedDayIso)
          .hour(23)
          .minute(45)
          .second(0)
          .millisecond(0);
      } else {
        if (!createStartTime || !createEndTime) {
          setFormError("Выберите время начала и окончания.");
          return;
        }
        starts = dayjs(`${createSelectedDayIso}T${createStartTime}`);
        ends = dayjs(`${createSelectedDayIso}T${createEndTime}`);
      }
    } else {
      if (!title.trim()) {
        setFormError("Введите заголовок.");
        return;
      }
    }

    if (!starts.isValid() || !ends.isValid()) {
      setFormError("Некорректное время.");
      return;
    }
    if (ends.isBefore(starts) || ends.isSame(starts)) {
      setFormError("Время окончания должно быть позже начала.");
      return;
    }

    // Prevent overlaps client-side too (backend is authoritative).
    if (modal?.mode === "create" && eventsOverlap(starts, ends)) {
      setFormError("Выбранный интервал пересекается с другим событием.");
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
            const base = e instanceof Error ? e.message : "Не удалось создать событие";
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
            const base = e instanceof Error ? e.message : "Не удалось сохранить изменения";
            const traceId: string | undefined = err?.traceId ?? err?.details?.trace_id ?? err?.details?.traceId;
            setFormError(traceId ? `${base} (trace_id: ${traceId})` : base);
          },
        }
      );
    }
  };

  const pending = createMut.isPending || updateMut.isPending;

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
    return createDayEventsForOverlap.some((ev) => {
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
    if (!s.isValid() || !e.isValid() || !e.isAfter(s)) {
      setTimeConflictWarning(null);
      return;
    }
    setTimeConflictWarning(eventsOverlap(s, e) ? "Интервал пересекается с другим событием в этот день." : null);
  };

  /** Блокируется слот, если выбранный интервал пересекается с другим событием или невалиден по краям. */
  const isPickerSlotDisabled = (hour: number, minute5: number) => {
    if (!timePickerKind) return true;
    const hh = String((hour + 24) % 24).padStart(2, "0");
    const mm = String(minute5).padStart(2, "0");
    const cand = dayjs(`${createSelectedDayIso}T${hh}:${mm}`);
    if (!cand.isValid()) return true;
    const dayStart = dayjs(`${createSelectedDayIso}T00:00`);
    const dayEndExclusive = dayStart.add(1, "day");

    if (timePickerKind === "start") {
      const endBound = createEndTime
        ? dayjs(`${createSelectedDayIso}T${createEndTime}`)
        : cand.add(1, "hour");
      if (createEndTime && !cand.isBefore(endBound)) return true;
      if (!createEndTime && cand.add(1, "hour").isAfter(dayEndExclusive)) return true;
      return eventsOverlap(cand, endBound);
    }

    const startBound = createStartTime
      ? dayjs(`${createSelectedDayIso}T${createStartTime}`)
      : (() => {
          const t = cand.subtract(1, "hour");
          return t.isBefore(dayStart) ? dayStart : t;
        })();
    if (!cand.isAfter(startBound)) return true;
    return eventsOverlap(startBound, cand);
  };

  const pickerTimeStr =
    timePickerKind === "start"
      ? createStartTime
      : timePickerKind === "end"
        ? createEndTime
        : "";

  // Если пользователь ещё не выбрал время (например, end пустой),
  // подставляем "адекватный" дефолт относительно уже выбранного другого края.
  let pickerFallback = "10:00";
  if (timePickerKind === "end" && createStartTime && createSelectedDayIso) {
    const start = dayjs(`${createSelectedDayIso}T${createStartTime}`);
    if (start.isValid()) {
      let end = start.add(1, "hour").second(0).millisecond(0);
      const rounded = Math.ceil(end.minute() / 5) * 5;
      if (rounded >= 60) {
        end = end.add(1, "hour").minute(0);
      } else {
        end = end.minute(rounded);
      }
      pickerFallback = end.format("HH:mm");
    }
  }
  if (timePickerKind === "start" && createEndTime && createSelectedDayIso) {
    const end = dayjs(`${createSelectedDayIso}T${createEndTime}`);
    if (end.isValid()) {
      let start = end.subtract(1, "hour").second(0).millisecond(0);
      const rounded = Math.floor(start.minute() / 5) * 5;
      start = start.minute(rounded);
      if (!start.isBefore(end)) {
        start = end.subtract(5, "minute");
      }
      pickerFallback = start.format("HH:mm");
    }
  }

  const pickerTime = timePickerKind ? pickerTimeStr || pickerFallback : pickerFallback;
  const pickerParts = pickerTime.split(":");
  const pickerHour = Number(pickerParts[0] ?? 0);
  const pickerMinute = Number(pickerParts[1] ?? 0);
  const pickerMinuteIndex = ((Math.round(pickerMinute / 5) % 12) + 12) % 12; // 0..11

  const applyPickerTime = (nextHour: number, nextMinute: number) => {
    const hh = String((nextHour + 24) % 24).padStart(2, "0");
    const mm = String((nextMinute + 60) % 60).padStart(2, "0");
    const next = `${hh}:${mm}`;
    if (isPickerSlotDisabled(nextHour, nextMinute)) return;
    if (timePickerKind === "start") {
      setCreateStartTime(next);
      updateTimeConflictWarning(next, createEndTime);
    }
    if (timePickerKind === "end") {
      setCreateEndTime(next);
      updateTimeConflictWarning(createStartTime, next);
    }
    // Время уже выбрано — не показываем выбор месяца (достаточно выбранной даты).
    setHideCreateMonthPicker(true);
  };

  const onWheelHours = (e: any) => {
    if (!timePickerKind) return;
    e?.stopPropagation?.();

    const dir = e?.deltaY > 0 ? 1 : -1;
    const steps = Math.min(6, Math.max(1, Math.round(Math.abs(e?.deltaY ?? 0) / 80)));
    const nextHour = pickerHour + dir * steps;
    const minute5 = pickerMinuteIndex * 5;
    applyPickerTime(nextHour, minute5);
  };

  const onWheelMinutes = (e: any) => {
    if (!timePickerKind) return;
    e?.stopPropagation?.();

    const dir = e?.deltaY > 0 ? 1 : -1;
    const steps = Math.min(6, Math.max(1, Math.round(Math.abs(e?.deltaY ?? 0) / 80)));
    const nextMinuteIndex = (pickerMinuteIndex + dir * steps + 12) % 12;
    const minute5 = nextMinuteIndex * 5;
    applyPickerTime(pickerHour, minute5);
  };

  useEffect(() => {
    if (modal?.mode !== "create" || timePickerKind === null) return;
    if (timePickerKind === "start") {
      const root = hoursPickerScrollRef.current;
      const el = root?.querySelector(`[data-hour="${pickerHour}"]`) as HTMLElement | null;
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
      return;
    }
    const root = minutesPickerScrollRef.current;
    const selectedM5 = pickerMinuteIndex * 5;
    const el = root?.querySelector(`[data-minute="${selectedM5}"]`) as HTMLElement | null;
    el?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [modal?.mode, timePickerKind, pickerHour, pickerMinuteIndex]);

  return (
    <Stack gap="md" className="staff-cal-page">
      <ContextBar title="Календарь" />
      <Text size="sm" c="dimmed">
        Совещания и напоминания (Celery). Событие можно привязать к задаче Kanban — поле ниже или ссылка из задачи «В
        календарь». Несколько участников может добавить сотрудник с правом приглашения в календаре (обычно руководитель
        или старший администратор). Редактирование сохраняет изменения через PATCH.
      </Text>
      {lastCreatedEvent ? (
        <Text size="sm" c="dimmed" style={{ color: "var(--accent-teal)" }}>
          Создано событие: {lastCreatedEvent.title} ({dayjs(lastCreatedEvent.dayIso).format("DD.MM.YYYY")}).
        </Text>
      ) : null}
      <Box className="staff-cal-toolbar">
        <Group gap="xs">
          <Button variant="default" radius="md" onClick={() => setMonthAnchor((m) => m.subtract(1, "month"))}>
            {"<<"}
          </Button>
          <Button variant="default" radius="md" onClick={() => setMonthAnchor(dayjs().startOf("month"))}>
            Сегодня
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
            Новое событие
          </Button>
        </Group>
      </Box>

      {isLoading ? (
        <PageSkeleton variant="table" rows={10} />
      ) : isError ? (
        <QueryErrorAlert error={error} />
      ) : !monthGrid?.days?.length ? (
        <EmptyState title="Нет событий" description="Создайте совещание или напоминание." />
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
                  {["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"].map((d) => (
                    <Table.Th key={d} style={{ width: `${100 / 7}%` }}>
                      <Text size="xs" c="dimmed" fw={600} ta="center">
                        {d}
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
                                            Нов
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
                                          {ev.all_day ? "Весь день" : dayjs(ev.starts_at).format("HH:mm")}{" "}
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
        opened={!!dayDrawerDate}
        onClose={() => setDayDrawerDate(null)}
        title={dayDrawerDate ? `События ${dayjs(dayDrawerDate).format("DD MMM YYYY")}` : "События"}
        centered
        size={dayDrawerSize}
        radius="lg"
        classNames={{ content: "staff-cal-modal-content" }}
      >
        <Stack>
          {dayForDrawer ? (
            <Group justify="space-between" align="center">
              <Text size="sm" c="dimmed">
                Быстрое действие
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
                + Добавить событие
              </Button>
            </Group>
          ) : null}
          {!dayForDrawer ? (
            <PageSkeleton variant="table" rows={5} />
          ) : dayForDrawer.events.length === 0 ? (
            <Stack>
              <EmptyState title="В этот день нет событий" description="Можно быстро выбрать время ниже." />
              <Text size="xs" c="dimmed" fw={700} mt={2}>
                Быстрый выбор часа
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
                                ? "Весь день"
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
                                  Напоминание
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
                                  Новое для меня
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
                              Подтвердить
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
        opened={modal !== null}
        onClose={closeModal}
        title={
          modal?.mode === "edit"
            ? "Редактировать событие"
            : modal?.mode === "create"
              ? "Новое событие"
              : "Событие"
        }
        centered
        size={modal?.mode === "details" ? "lg" : "xl"}
        radius="lg"
        classNames={{ content: "staff-cal-modal-content" }}
        styles={{
          content: { display: "flex", flexDirection: "column" },
          body: {
            // Scroll is handled by Mantine modal body (see global CSS),
            // footer is sticky to keep actions accessible.
            padding: 0,
          },
        }}
      >
        <Stack gap="sm" p="md" pb="xl">
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
                      {eventDetails.event.all_day ? <Badge size="sm">Весь день</Badge> : null}
                      {eventDetails.event.task_id ? <Badge size="sm" color="teal">Задача</Badge> : null}
                      {eventDetails.reminder.reminder_minutes_before != null &&
                      eventDetails.reminder.reminder_minutes_before > 0 ? (
                        <Badge size="sm" variant="light" color="blue">
                          Напоминание: за {eventDetails.reminder.reminder_minutes_before} мин
                        </Badge>
                      ) : (
                        <Badge size="sm" variant="light" color="gray">
                          Напоминание: выключено
                        </Badge>
                      )}
                    </Group>

                    {eventDetails.event.participants?.length ? (
                      <Text size="sm" c="dimmed">
                        Участники:{" "}
                        {eventDetails.event.participants.map((p) => p.full_name?.trim() || "—").join(", ")}
                      </Text>
                    ) : null}

                    {eventDetails.creator_ack_summary ? (
                      <Text size="sm" c="dimmed">
                        Подтвердили: {eventDetails.creator_ack_summary.acknowledged_participants}/
                        {eventDetails.creator_ack_summary.total_participants}
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
                      <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
                      <Textarea
                        label="Описание"
                        value={description}
                        onChange={(e) => setDescription(e.currentTarget.value)}
                        minRows={6}
                      />
                      {canInviteParticipants ? (
                        <MultiSelect
                          label="Участники совещания"
                          description={
                            modal?.mode === "edit"
                              ? "Полная замена списка; организатор будет добавлен автоматически, если его нет в списке"
                              : "Кого видеть в календаре и напоминаниях; вы всегда в списке как организатор"
                          }
                          placeholder="Выберите сотрудников"
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
                          Чтобы приглашать коллег или менять состав участников, нужно право «приглашение участников календаря».
                          Сейчас групповые права централизованы владельцем; детальная политика scope (owner-driven) будет включена
                          отдельным этапом (P6).
                        </Text>
                      )}
                      <Switch
                        label="Весь день"
                        checked={allDay}
                        onChange={(e) => {
                          const checked = e.currentTarget.checked;
                          setAllDay(checked);
                          if (modal?.mode === "create" && !checked) {
                            setCreateStartTime("");
                            setCreateEndTime("");
                          }
                        }}
                      />
                      <Select
                        label="Напоминание"
                        description="За сколько минут до начала отправить напоминание (0 — не напоминать)"
                        data={[
                          { value: "0", label: "Не напоминать" },
                          { value: "5", label: "За 5 минут" },
                          { value: "15", label: "За 15 минут" },
                          { value: "30", label: "За 30 минут" },
                          { value: "60", label: "За 1 час" },
                          { value: "120", label: "За 2 часа" },
                          { value: "1440", label: "За сутки" },
                        ]}
                        value={reminderMinutes}
                        onChange={(v) => setReminderMinutes(v ?? "15")}
                      />
                    </Stack>

                    <Stack gap="sm">
                      {modal?.mode === "edit" ? (
                        <>
                          <TextInput
                            label="Начало"
                            type="datetime-local"
                            value={startsLocal}
                            onChange={(e) => setStartsLocal(e.currentTarget.value)}
                          />
                          <TextInput
                            label="Окончание"
                            type="datetime-local"
                            value={endsLocal}
                            onChange={(e) => setEndsLocal(e.currentTarget.value)}
                          />
                        </>
                      ) : (
                        <>
                          {hideCreateMonthPicker ? (
                            <Group justify="space-between" align="center">
                              <Stack gap={0}>
                                <Text size="sm" fw={700}>
                                  Дата
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
                                Изменить
                              </Button>
                            </Group>
                          ) : (
                            <>
                              <Text size="sm" fw={700}>
                                Дата
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
                              Для события “Весь день” время не выбирается.
                            </Text>
                          ) : (
                            <SimpleGrid cols={{ base: 1, sm: 2 }} spacing="sm">
                              <Box>
                                <Text size="sm" fw={700}>
                                  Время начала
                                </Text>
                                <Group mt={6} grow align="flex-end" gap="xs" wrap="nowrap">
                                  <TextInput
                                    type="text"
                                    placeholder="HH:MM"
                                    value={createStartTime}
                                    onChange={(e) => {
                                      const next = formatTimeHHMMInput(e.currentTarget.value || "");
                                      if (!next) {
                                        setCreateStartTime("");
                                        setTimeConflictWarning(null);
                                        return;
                                      }
                                      setCreateStartTime(next);
                                      updateTimeConflictWarning(next, createEndTime);
                                    }}
                                    styles={{
                                      root: { flex: 1, minWidth: 0 },
                                      input: {
                                        background: "var(--bg-card)",
                                        borderRadius: "var(--radius-md)",
                                        boxShadow: "var(--shadow-soft-sm)",
                                      },
                                    }}
                                  />
                                  <ActionIcon
                                    variant="light"
                                    size="lg"
                                    radius="md"
                                    aria-label="Выбрать время начала"
                                    onClick={() => setTimePickerKind("start")}
                                    style={{ boxShadow: "var(--shadow-soft-sm)" }}
                                  >
                                    <IconClock size={18} />
                                  </ActionIcon>
                                </Group>
                              </Box>

                              <Box>
                                <Text size="sm" fw={700}>
                                  Время окончания
                                </Text>
                                <Group mt={6} grow align="flex-end" gap="xs" wrap="nowrap">
                                  <TextInput
                                    type="text"
                                    placeholder="HH:MM"
                                    value={createEndTime}
                                    onChange={(e) => {
                                      const next = formatTimeHHMMInput(e.currentTarget.value || "");
                                      if (!next) {
                                        setCreateEndTime("");
                                        setTimeConflictWarning(null);
                                        return;
                                      }
                                      setCreateEndTime(next);
                                      updateTimeConflictWarning(createStartTime, next);
                                    }}
                                    styles={{
                                      root: { flex: 1, minWidth: 0 },
                                      input: {
                                        background: "var(--bg-card)",
                                        borderRadius: "var(--radius-md)",
                                        boxShadow: "var(--shadow-soft-sm)",
                                      },
                                    }}
                                  />
                                  <ActionIcon
                                    variant="light"
                                    size="lg"
                                    radius="md"
                                    aria-label="Выбрать время окончания"
                                    onClick={() => setTimePickerKind("end")}
                                    style={{ boxShadow: "var(--shadow-soft-sm)" }}
                                  >
                                    <IconClock size={18} />
                                  </ActionIcon>
                                </Group>
                              </Box>
                            </SimpleGrid>
                          )}

                          {timeConflictWarning ? (
                            <Text size="xs" c="orange" mt={6}>
                              {timeConflictWarning} Можно продолжать ввод — проверка применится при сохранении.
                            </Text>
                          ) : null}
                        </>
                      )}

                      <TextInput
                        label="ID задачи (необязательно)"
                        description="UUID задачи из раздела «Задачи» — для связи с календарём; оставьте пустым, чтобы снять привязку"
                        value={linkedTaskId}
                        onChange={(e) => setLinkedTaskId(e.currentTarget.value)}
                        placeholder="например из ссылки «В календарь»"
                      />
                    </Stack>
                  </SimpleGrid>
                </>
              )}
        </Stack>

        <Box
          p="md"
          pt="sm"
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
                    Вы подтвердили что увидели
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
                    Подтвердить что увидел
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
                    Изменить
                  </Button>
                ) : null}
                <Button variant="default" onClick={closeModal}>
                  Закрыть
                </Button>
              </Group>
            </Group>
          ) : (
            <Group justify="flex-end">
              <Button variant="default" onClick={closeModal}>
                Отмена
              </Button>
              <Button
                onClick={submitModal}
                loading={pending}
                disabled={
                  !title.trim() || (modal?.mode === "create" && !allDay && (!createStartTime || !createEndTime))
                }
              >
                {modal?.mode === "edit" ? "Сохранить" : "Создать"}
              </Button>
            </Group>
          )}
        </Box>
      </Modal>

      <Modal
        opened={modal?.mode === "create" && timePickerKind !== null}
        onClose={() => setTimePickerKind(null)}
        title={timePickerKind === "end" ? "Время окончания" : "Время начала"}
        centered
        size="xs"
        radius="lg"
        classNames={{ content: "staff-cal-modal-content" }}
      >
        <Stack gap="sm">
          <Group justify="space-between" gap="xs">
            <Text size="xs" c="dimmed">
              Колесико: быстрый выбор (часы +1, минуты +5)
            </Text>
            <Button
              variant="light"
              size="xs"
              onClick={() => {
                if (timePickerKind === "start") setCreateStartTime("");
                if (timePickerKind === "end") setCreateEndTime("");
                setTimePickerKind(null);
              }}
            >
              Очистить
            </Button>
          </Group>

          <Group grow gap="xs" align="stretch">
            <ScrollArea
              ref={hoursPickerScrollRef}
              className="staff-cal-time-scroll"
              style={{
                height: 240,
                borderRadius: "var(--radius-md)",
                background: "var(--bg-card-soft)",
                border: "1px solid var(--input-border)",
              }}
              onWheel={onWheelHours}
            >
              <Stack gap={6} p={10}>
                {hourOptions.map((h) => {
                  const isSel = h === pickerHour;
                  const minute5 = pickerMinuteIndex * 5;
                  const isDisabled = isPickerSlotDisabled(h, minute5);
                  return (
                    <Box
                      key={h}
                        data-hour={h}
                      onClick={() => {
                          if (isDisabled) return;
                          applyPickerTime(h, minute5);
                      }}
                      style={{
                        padding: "var(--space-10) var(--space-md)",
                        borderRadius: "var(--radius-md)",
                        background: isDisabled
                          ? "var(--mantine-color-gray-1)"
                          : isSel
                            ? "var(--staff-cal-time-selected-bg)"
                            : "var(--bg-card)",
                        border: isDisabled
                          ? "1px solid var(--mantine-color-gray-2)"
                          : isSel
                            ? "1px solid var(--staff-cal-time-selected-border)"
                            : "1px solid transparent",
                        cursor: isDisabled ? "not-allowed" : "pointer",
                        boxShadow: isDisabled ? "none" : isSel ? "var(--shadow-soft-sm)" : "none",
                        transition:
                          "transform 0.14s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.2s ease",
                        transform: isDisabled ? undefined : isSel ? "translateY(-1px)" : undefined,
                      }}
                    >
                      <Text
                        size="sm"
                        fw={900}
                        c={isDisabled ? "dimmed" : isSel ? undefined : "dark"}
                        style={{
                          textAlign: "center",
                          ...(!isDisabled && isSel ? { color: "var(--staff-cal-time-selected-text)" } : {}),
                        }}
                      >
                        {String(h).padStart(2, "0")}
                      </Text>
                    </Box>
                  );
                })}
              </Stack>
            </ScrollArea>

            <ScrollArea
              ref={minutesPickerScrollRef}
              className="staff-cal-time-scroll"
              style={{
                height: 240,
                borderRadius: "var(--radius-md)",
                background: "var(--bg-card-soft)",
                border: "1px solid var(--input-border)",
              }}
              onWheel={onWheelMinutes}
            >
              <Stack gap={6} p={10}>
                {minuteOptions.map((m5) => {
                  const isSel = m5 === pickerMinuteIndex * 5;
                  const isDisabled = isPickerSlotDisabled(pickerHour, m5);
                  return (
                    <Box
                      key={m5}
                      data-minute={m5}
                      onClick={() => {
                        if (isDisabled) return;
                        applyPickerTime(pickerHour, m5);
                      }}
                      style={{
                        padding: "var(--space-10) var(--space-md)",
                        borderRadius: "var(--radius-md)",
                        background: isDisabled
                          ? "var(--mantine-color-gray-1)"
                          : isSel
                            ? "var(--staff-cal-time-selected-bg)"
                            : "var(--bg-card)",
                        border: isDisabled
                          ? "1px solid var(--mantine-color-gray-2)"
                          : isSel
                            ? "1px solid var(--staff-cal-time-selected-border)"
                            : "1px solid transparent",
                        cursor: isDisabled ? "not-allowed" : "pointer",
                        boxShadow: isDisabled ? "none" : isSel ? "var(--shadow-soft-sm)" : "none",
                        transition:
                          "transform 0.14s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.2s ease",
                        transform: isDisabled ? undefined : isSel ? "translateY(-1px)" : undefined,
                      }}
                    >
                      <Text
                        size="sm"
                        fw={900}
                        c={isDisabled ? "dimmed" : isSel ? undefined : "dark"}
                        style={{
                          textAlign: "center",
                          ...(isDisabled || !isSel ? {} : { color: "var(--staff-cal-time-selected-text)" }),
                        }}
                      >
                        {String(m5).padStart(2, "0")}
                      </Text>
                    </Box>
                  );
                })}
              </Stack>
            </ScrollArea>
          </Group>

          <Group justify="flex-end">
            <Button variant="default" onClick={() => setTimePickerKind(null)}>
              Закрыть
            </Button>
            <Button onClick={() => setTimePickerKind(null)}>Готово</Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}
