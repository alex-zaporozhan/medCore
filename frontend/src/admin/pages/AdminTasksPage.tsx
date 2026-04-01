import { useState, useMemo, useEffect, useRef, useCallback, type ReactNode } from "react";
import {
  ActionIcon,
  Avatar,
  Badge,
  Button,
  Card,
  Checkbox,
  Group,
  Input,
  Loader,
  Menu,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  TextInput,
  Select,
  MultiSelect,
  Box,
  SimpleGrid,
  Paper,
  Alert,
  Tooltip,
} from "@mantine/core";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import {
  IconGripVertical,
  IconRobot,
  IconMessageCircle,
  IconMessages,
  IconCalendarEvent,
  IconPhone,
  IconBrandWhatsapp,
  IconAlertTriangle,
  IconLock,
  IconLockOpen,
  IconChevronUp,
  IconChevronDown,
  IconLayoutKanban,
  IconPlus,
  IconPalette,
  IconSettings,
  IconFilter,
  IconSearch,
} from "@tabler/icons-react";
import { Link, useSearchParams } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import {
  GlassModal,
  AdminDataTableToolbar,
  AdminDataTableSurface,
  AppleEmojiOverlayTextarea,
  EmojiMartPopoverPicker,
  CompactMonthPicker,
  PersonNameLink,
} from "@/shared/ui";
import { ContextBar } from "@/shared/ui/ContextBar";
import { SEMANTIC } from "@/shared/semanticUi";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { EmptyState } from "@/shared/ui/EmptyState";
import {
  priorityBadgeColor,
  taskStatusBadgeStyles,
  taskStatusCardSurface,
  taskStatusTextColors,
} from "@/shared/taskStatusSemantic";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { usePatients } from "@/hooks/usePatients";
import {
  useAdminAdmins,
  useAdminTasksList,
  useAdminTasksMyFocus,
  useCreateAdminTaskMutation,
  useClaimAdminTaskMutation,
  useUpdateAdminTaskStatusMutation,
  useUpdateAdminTaskMetaMutation,
  useReorderAdminTasksMutation,
  useTaskWipPolicies,
  useTaskTransitions,
  useTaskCalendarContext,
  useInviteTaskCalendarParticipants,
  useTaskComments,
  usePostTaskComment,
  usePatchAdminTaskAssigneesMutation,
  usePatchAdminTaskDueMutation,
  useAdminSession,
  useTaskBoardsQuery,
  useReplaceTaskBoardColumnsMutation,
  useTaskStreamsQuery,
  useTaskTagsQuery,
  useCreateTaskStreamMutation,
  usePatchTaskStreamMutation,
  useCreateTaskTagMutation,
  usePatchAdminTaskStreamTagsMutation,
} from "@/hooks";
import type { AdminTaskRow, AdminUserRow, TaskStreamRow, TaskStreamMantineColor, TaskStreamPageTint } from "@/hooks";
import { ApiErrorWithCode, getAdminId } from "@/api/client";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
  type DragEndEvent,
  type DragOverEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { useDebouncedValue } from "@mantine/hooks";

const STATUS_META: Record<string, string> = {
  open: "Открыто",
  in_progress: "В работе",
  on_hold: "На паузе",
  review: "На проверке",
  done: "Выполнено",
  cancelled: "Отменено",
};
const STATUS_ORDER = ["open", "in_progress", "on_hold", "review", "done", "cancelled"] as const;

const TIME_BOMB_HOURS = 2;
const AGING_ALERT_HOURS = 48;
const KANBAN_WIP_LIMITS: Record<string, number> = {
  open: 8,
  in_progress: 6,
  on_hold: 6,
  review: 6,
};

function streamPageTintKey(theme: Record<string, unknown> | undefined): string {
  const v = theme?.page_tint;
  return typeof v === "string" && v !== "none" ? v : "none";
}

function streamMantineColorKey(theme: Record<string, unknown> | undefined): TaskStreamMantineColor {
  const v = theme?.mantine_color;
  const allowed: TaskStreamMantineColor[] = [
    "gray",
    "red",
    "pink",
    "grape",
    "violet",
    "indigo",
    "blue",
    "cyan",
    "teal",
    "green",
    "lime",
    "yellow",
    "orange",
  ];
  return typeof v === "string" && allowed.includes(v as TaskStreamMantineColor)
    ? (v as TaskStreamMantineColor)
    : "blue";
}

/** Имена личных исполнителей: assignee_ids или legacy assignee_id. */
function taskAssigneeIdList(task: AdminTaskRow): string[] {
  if (task.assignee_ids && task.assignee_ids.length > 0) return task.assignee_ids;
  if (task.assignee_id) return [task.assignee_id];
  return [];
}

function isTimeBomb(dueAt: string | null): boolean {
  if (!dueAt) return false;
  const due = dayjs(dueAt);
  const now = dayjs();
  return due.isBefore(now) || due.diff(now, "hour", true) <= TIME_BOMB_HOURS;
}

function isDueOverdue(dueAt: string | null): boolean {
  if (!dueAt) return false;
  return dayjs(dueAt).isBefore(dayjs());
}

function firstAssigneeForAvatar(task: AdminTaskRow, admins: AdminUserRow[]): AdminUserRow | null {
  const ids = taskAssigneeIdList(task);
  if (ids.length === 0) return null;
  return admins.find((a) => a.id === ids[0]) ?? null;
}

function TaskKanbanCard({
  task,
  admins,
  patientName,
  onOpenDetail,
  onClaim,
  onTaskChat,
  isAi,
  draggable,
  blocked,
  selected,
  onSelect,
  onMoveByKeyboard,
  canMoveStream,
  streamOptions,
  onMoveToStream,
}: {
  task: AdminTaskRow;
  admins: AdminUserRow[];
  patientName?: string | null;
  onOpenDetail: (taskId: string) => void;
  onClaim?: (taskId: string) => void;
  onTaskChat?: (taskId: string) => void;
  isAi?: boolean;
  draggable: boolean;
  blocked?: boolean;
  selected?: boolean;
  onSelect?: (taskId: string, checked: boolean) => void;
  onMoveByKeyboard?: (taskId: string, direction: -1 | 1) => void;
  canMoveStream?: boolean;
  streamOptions?: Array<{ value: string; label: string }>;
  onMoveToStream?: (taskId: string, streamId: string) => void;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
    disabled: !draggable,
  });
  const overdue = isDueOverdue(task.due_at);
  const timeBomb = isTimeBomb(task.due_at);
  const assignee = firstAssigneeForAvatar(task, admins);
  const displayName = assignee?.full_name || assignee?.email || null;
  const tc = taskStatusTextColors(task.status);

  const outerStyle = draggable
    ? {
        transform: transform ? CSS.Translate.toString(transform) : undefined,
        opacity: isDragging ? 0.88 : 1,
      }
    : undefined;

  return (
    <Box ref={setNodeRef} style={outerStyle}>
      <Paper
        radius="md"
        p="md"
        withBorder={false}
        style={{
          ...taskStatusCardSurface(task.status),
          cursor: "pointer",
          width: "100%",
          opacity: blocked ? 0.9 : 1,
          boxShadow: selected
            ? `0 0 0 2px var(--mantine-color-indigo-5), var(--calendar-card-shadow)`
            : "var(--calendar-card-shadow)",
        }}
        onClick={() => onOpenDetail(task.id)}
        tabIndex={0}
        onKeyDown={(e) => {
          if (!onMoveByKeyboard) return;
          if (e.altKey && e.key === "ArrowRight") {
            e.preventDefault();
            onMoveByKeyboard(task.id, 1);
          }
          if (e.altKey && e.key === "ArrowLeft") {
            e.preventDefault();
            onMoveByKeyboard(task.id, -1);
          }
        }}
      >
        <Group gap="xs" wrap="nowrap" align="flex-start">
          {onSelect ? (
            <Checkbox
              mt={2}
              checked={Boolean(selected)}
              onChange={(e) => onSelect(task.id, e.currentTarget.checked)}
              onClick={(e) => e.stopPropagation()}
              aria-label="Выбрать задачу"
            />
          ) : null}
          {draggable ? (
            <ActionIcon
              variant="subtle"
              color="gray"
              size="sm"
              style={{ cursor: "grab", flexShrink: 0, marginTop: 2 }}
              {...listeners}
              {...attributes}
              onClick={(e) => e.stopPropagation()}
              aria-label="Перетащить задачу"
            >
              <IconGripVertical size={16} />
            </ActionIcon>
          ) : null}
          <Stack gap={6} style={{ flex: 1, minWidth: 0 }}>
            <Group gap={6} wrap="wrap">
              <Badge size="xs" variant="transparent" tt="uppercase" styles={taskStatusBadgeStyles(task.status)}>
                {STATUS_META[task.status] ?? task.status}
              </Badge>
              <Badge size="xs" variant="light" color={priorityBadgeColor(task.priority)} tt="uppercase">
                {task.priority}
              </Badge>
            </Group>
            <Group gap={6} wrap="nowrap" align="flex-start">
              {isAi && <IconRobot size={16} color="var(--mantine-color-indigo-6)" style={{ flexShrink: 0 }} />}
              <Text size="sm" fw={600} lineClamp={2} style={{ flex: 1, color: tc.title }}>
                {task.title}
              </Text>
              {canMoveStream && streamOptions && streamOptions.length > 0 && onMoveToStream ? (
                <Menu shadow="md" width={260} withinPortal>
                  <Menu.Target>
                    <ActionIcon
                      variant="subtle"
                      color="gray"
                      size="sm"
                      onClick={(e) => e.stopPropagation()}
                      aria-label="Переместить в поток"
                      style={{ flexShrink: 0 }}
                    >
                      <IconLayoutKanban size={16} />
                    </ActionIcon>
                  </Menu.Target>
                  <Menu.Dropdown>
                    <Menu.Label>Переместить в поток</Menu.Label>
                    {streamOptions.map((opt) => (
                      <Menu.Item
                        key={opt.value}
                        onClick={(e) => {
                          e.stopPropagation();
                          onMoveToStream(task.id, opt.value);
                        }}
                      >
                        {opt.label}
                      </Menu.Item>
                    ))}
                  </Menu.Dropdown>
                </Menu>
              ) : null}
            </Group>
            {blocked ? (
              <Tooltip
                label={task.blocked_reason?.trim() ? `Причина: ${task.blocked_reason}` : "Причина блокировки не указана"}
                withArrow
                multiline
                maw={300}
              >
                <Badge size="xs" color="red" variant="light" leftSection={<IconLock size={12} />}>
                  Заблокировано
                </Badge>
              </Tooltip>
            ) : null}
            {patientName ? (
              <Text size="xs" lineClamp={1} style={{ color: tc.meta }}>
                Привязка: {patientName}
              </Text>
            ) : null}
            <Group justify="space-between" mt="md" wrap="nowrap" gap="xs">
              <Text size="xs" c={overdue || timeBomb ? "red" : "dimmed"} fw={overdue ? 500 : 400}>
                {task.due_at ? dayjs(task.due_at).format("DD.MM HH:mm") : "—"}
              </Text>
              <Avatar size="sm" radius="xl" color="indigo">
                {(displayName || "?").slice(0, 2).toUpperCase()}
              </Avatar>
            </Group>
            {isAi && onClaim && (task.status === "open" || task.source === "ai_suggested" || task.source === "ai_auto") ? (
              <Button
                size="xs"
                variant="light"
                color="indigo"
                onClick={(e) => {
                  e.stopPropagation();
                  onClaim(task.id);
                }}
              >
                Принять в работу
              </Button>
            ) : null}
            {onTaskChat ? (
              <Button
                size="xs"
                variant="outline"
                color="indigo"
                leftSection={<IconMessages size={12} />}
                onClick={(e) => {
                  e.stopPropagation();
                  onTaskChat(task.id);
                }}
              >
                Чат задачи
              </Button>
            ) : null}
          </Stack>
        </Group>
      </Paper>
    </Box>
  );
}

export default function AdminTasksPage() {
  const { currentClinicId } = useAdminClinic();
  const [detailTaskId, setDetailTaskId] = useState<string | null>(null);
  const [detailCommentDraft, setDetailCommentDraft] = useState("");
  const detailCommentTextareaRef = useRef<HTMLTextAreaElement>(null);
  const [taskChatId, setTaskChatId] = useState<string | null>(null);
  const [taskChatDraft, setTaskChatDraft] = useState("");
  const taskChatTextareaRef = useRef<HTMLTextAreaElement>(null);
  const { data: taskComments = [], isLoading: taskCommentsLoading } = useTaskComments(taskChatId);
  const postTaskComment = usePostTaskComment(taskChatId);
  const { data: detailComments = [], isLoading: detailCommentsLoading } = useTaskComments(detailTaskId);
  const postDetailComment = usePostTaskComment(detailTaskId);
  const [createOpened, setCreateOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<string | null>("medium");
  const [assigneeIds, setAssigneeIds] = useState<string[]>([]);
  const [dueDayIso, setDueDayIso] = useState(() => dayjs().format("YYYY-MM-DD"));
  const [dueTimeStr, setDueTimeStr] = useState(() => dayjs().format("HH:mm"));
  const [taskDueMonth, setTaskDueMonth] = useState(() => dayjs().startOf("month"));
  const dueDate = useMemo(
    () => (dueDayIso && dueTimeStr ? `${dueDayIso}T${dueTimeStr}` : ""),
    [dueDayIso, dueTimeStr]
  );
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([]);
  const [filterAssignee, setFilterAssignee] = useState<string | null>(null);
  const [filterPriority, setFilterPriority] = useState<string | null>(null);
  const [filterDue, setFilterDue] = useState<string>("all");
  const [filterQuery, setFilterQuery] = useState("");
  const [debouncedFilterQuery] = useDebouncedValue(filterQuery, 180);
  const [onlyNeedsMyApproval, setOnlyNeedsMyApproval] = useState(false);
  const [blockedReasonDraft, setBlockedReasonDraft] = useState("");
  const [auditTrail, setAuditTrail] = useState<
    Array<{ id: string; taskId: string; taskTitle: string; from: string; to: string; at: string }>
  >([]);
  const [dragError, setDragError] = useState<string | null>(null);
  const [bulkResultMessage, setBulkResultMessage] = useState<string | null>(null);
  const [detailAssigneeDraft, setDetailAssigneeDraft] = useState<string[]>([]);
  const [detailDueDayIso, setDetailDueDayIso] = useState("");
  const [detailDueTimeStr, setDetailDueTimeStr] = useState("");
  const [detailModalApiError, setDetailModalApiError] = useState<string | null>(null);
  const [assigneeAuditComment, setAssigneeAuditComment] = useState(true);
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);
  const [boardColumnModalOpened, setBoardColumnModalOpened] = useState(false);
  const [columnDraft, setColumnDraft] = useState<{ mapped_status: string; label: string | null }[]>([]);
  const boardInitRef = useRef(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedStreamId, setSelectedStreamId] = useState<string | null>(null);
  const [streamFilterInitialized, setStreamFilterInitialized] = useState(false);
  const [filterTagIds, setFilterTagIds] = useState<string[]>([]);
  const [createStreamId, setCreateStreamId] = useState<string | null>(null);
  const [createTagIds, setCreateTagIds] = useState<string[]>([]);
  const [newStreamModalOpened, setNewStreamModalOpened] = useState(false);
  const [newStreamName, setNewStreamName] = useState("");
  const [streamThemeModalOpened, setStreamThemeModalOpened] = useState(false);
  const [themeDraftTint, setThemeDraftTint] = useState<TaskStreamPageTint>("none");
  const [themeDraftColor, setThemeDraftColor] = useState<TaskStreamMantineColor>("blue");
  const [newTagModalOpened, setNewTagModalOpened] = useState(false);
  const [newTagName, setNewTagName] = useState("");
  const [detailStreamDraft, setDetailStreamDraft] = useState<string | null>(null);
  const [detailTagDraft, setDetailTagDraft] = useState<string[]>([]);

  const currentAdminId = getAdminId();
  const { data: adminSession } = useAdminSession();
  const canManageBoards = Boolean(adminSession?.permissions?.includes("manage_tasks"));
  const { data: taskStreams = [], isLoading: streamsLoading } = useTaskStreamsQuery();
  const { data: taskTags = [], isLoading: tagsLoading } = useTaskTagsQuery();
  const {
    data: allTasks = [],
    isLoading: tasksLoading,
  } = useAdminTasksList(
    { streamId: null, tagIds: filterTagIds },
    { enabled: streamFilterInitialized }
  );
  const taskChatTitle = useMemo(() => {
    if (!taskChatId) return "";
    return allTasks.find((t) => t.id === taskChatId)?.title ?? "";
  }, [taskChatId, allTasks]);
  const { data: myFocusTasks = [] } = useAdminTasksMyFocus(currentAdminId);
  const { data: admins = [] } = useAdminAdmins();
  const { data: patientsList = [] } = usePatients({ clinic_id: currentClinicId ?? undefined, limit: 500 });
  const patientIdToPhone = useMemo(() => {
    const m = new Map<string, string>();
    patientsList.forEach((p) => {
      if (p.phone) m.set(p.id, p.phone);
    });
    return m;
  }, [patientsList]);
  const patientIdToName = useMemo(() => {
    const m = new Map<string, string>();
    patientsList.forEach((p) => {
      if (p.full_name) m.set(p.id, p.full_name);
    });
    return m;
  }, [patientsList]);

  const detailTask = useMemo(
    () => (detailTaskId ? allTasks.find((t) => t.id === detailTaskId) : undefined),
    [detailTaskId, allTasks]
  );

  useEffect(() => {
    if (!detailTask) {
      setDetailStreamDraft(null);
      setDetailTagDraft([]);
      return;
    }
    setDetailStreamDraft(detailTask.stream_id);
    setDetailTagDraft([...(detailTask.tag_ids ?? [])]);
  }, [detailTask?.id, detailTask?.stream_id, detailTask?.tag_ids]);

  const createTaskMutation = useCreateAdminTaskMutation();
  const claimMutation = useClaimAdminTaskMutation();
  const updateStatusMutation = useUpdateAdminTaskStatusMutation();
  const moveTask = useCallback(
    (task: AdminTaskRow, toStatus: string) => {
      if (!task || task.status === toStatus) return;
      const id =
        typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
      setAuditTrail((prev) => [
        { id, taskId: task.id, taskTitle: task.title, from: task.status, to: toStatus, at: new Date().toISOString() },
        ...prev,
      ]);
      updateStatusMutation.mutate({ taskId: task.id, status: toStatus });
    },
    [updateStatusMutation]
  );
  const updateTaskMetaMutation = useUpdateAdminTaskMetaMutation();
  const patchAssigneesMutation = usePatchAdminTaskAssigneesMutation();
  const patchDueMutation = usePatchAdminTaskDueMutation();
  const { data: taskBoards = [], isLoading: boardsLoading } = useTaskBoardsQuery();
  const replaceBoardColumnsMutation = useReplaceTaskBoardColumnsMutation();
  // Personal boards creation is intentionally hidden in the new UX; keep API hook unused for now.
  const createStreamMutation = useCreateTaskStreamMutation();
  const patchStreamMutation = usePatchTaskStreamMutation();
  const createTagMutation = useCreateTaskTagMutation();
  const patchStreamTagsMutation = usePatchAdminTaskStreamTagsMutation();
  const canMoveTasksAcrossStreams = canManageBoards;
  const streamMoveOptions = useMemo(
    () => taskStreams.filter((s) => !s.is_archived).map((s) => ({ value: s.id, label: s.name })),
    [taskStreams]
  );

  const reorderTasksMutation = useReorderAdminTasksMutation();
  // Bulk update action is hidden in the new UX; keep hook out until reintroduced.
  const { data: wipPolicies = KANBAN_WIP_LIMITS } = useTaskWipPolicies();
  const { data: detailTransitions = [] } = useTaskTransitions(detailTaskId);
  const { data: taskCalendarContext = [] } = useTaskCalendarContext(detailTaskId);
  const [inviteEventId, setInviteEventId] = useState<string | null>(null);
  const [inviteAdminIds, setInviteAdminIds] = useState<string[]>([]);
  const inviteParticipantsMutation = useInviteTaskCalendarParticipants(detailTaskId, inviteEventId);

  useEffect(() => {
    setSelectedTaskIds((prev) => prev.filter((id) => allTasks.some((t) => t.id === id)));
  }, [allTasks]);

  useEffect(() => {
    if (streamsLoading || streamFilterInitialized) return;
    const q = searchParams.get("stream");
    if (q === "all") {
      setSelectedStreamId(null);
    } else if (q && taskStreams.some((s) => s.id === q)) {
      setSelectedStreamId(q);
    } else if (taskStreams.length > 0) {
      try {
        const saved = localStorage.getItem("adminTasksStreamId");
        if (saved === "all") setSelectedStreamId(null);
        else if (saved && taskStreams.some((s) => s.id === saved)) setSelectedStreamId(saved);
        else {
          const g = taskStreams.find((s) => s.slug === "general");
          setSelectedStreamId(g?.id ?? taskStreams[0]?.id ?? null);
        }
      } catch {
        const g = taskStreams.find((s) => s.slug === "general");
        setSelectedStreamId(g?.id ?? taskStreams[0]?.id ?? null);
      }
    } else {
      setSelectedStreamId(null);
    }
    setStreamFilterInitialized(true);
  }, [streamsLoading, taskStreams, searchParams, streamFilterInitialized]);

  useEffect(() => {
    if (!streamFilterInitialized) return;
    const sp = new URLSearchParams(searchParams);
    if (selectedStreamId) sp.set("stream", selectedStreamId);
    else sp.set("stream", "all");
    const next = sp.toString();
    if (next !== searchParams.toString()) {
      setSearchParams(sp, { replace: true });
    }
    try {
      localStorage.setItem("adminTasksStreamId", selectedStreamId ?? "all");
    } catch {
      /* ignore */
    }
  }, [selectedStreamId, streamFilterInitialized, searchParams, setSearchParams]);

  const activeStream = useMemo(
    () => taskStreams.find((s) => s.id === selectedStreamId),
    [taskStreams, selectedStreamId]
  );

  useEffect(() => {
    if (!streamThemeModalOpened) return;
    const rawTint = activeStream?.theme?.page_tint;
    const rawColor = activeStream?.theme?.mantine_color;
    setThemeDraftTint((typeof rawTint === "string" ? (rawTint as TaskStreamPageTint) : "none") ?? "none");
    setThemeDraftColor((typeof rawColor === "string" ? (rawColor as TaskStreamMantineColor) : "blue") ?? "blue");
  }, [streamThemeModalOpened, activeStream?.id, activeStream?.theme]);

  const streamPages = useMemo(() => {
    const pages: Array<{
      key: string;
      label: string;
      streamId: string | null;
      stream?: TaskStreamRow;
    }> = [{ key: "all", label: "Все потоки", streamId: null }];
    taskStreams.forEach((s) => {
      pages.push({ key: s.id, label: s.name, streamId: s.id, stream: s });
    });
    return pages;
  }, [taskStreams]);

  const activePageIndex = useMemo(() => {
    if (!selectedStreamId) return 0;
    const i = streamPages.findIndex((p) => p.streamId === selectedStreamId);
    return i >= 0 ? i : 0;
  }, [selectedStreamId, streamPages]);

  const pagerRef = useRef<HTMLDivElement>(null);
  const skipAutoScrollRef = useRef(false);
  const pagerScrollTimerRef = useRef<number | null>(null);
  const pagerLastIdxRef = useRef<number>(-1);
  const scrollToPage = useCallback((idx: number, behavior: ScrollBehavior = "smooth") => {
    const el = pagerRef.current;
    if (!el) return;
    const clamped = Math.max(0, Math.min(idx, streamPages.length - 1));
    const target = el.querySelector<HTMLElement>(`[data-stream-page-index="${clamped}"]`);
    if (!target) return;
    if (typeof (target as any).scrollIntoView === "function") {
      target.scrollIntoView({ behavior, inline: "start", block: "nearest" });
      return;
    }
    // JSDOM / embedded: fallback to scrollLeft.
    const pageWidth = el.clientWidth || 1;
    const nextLeft = clamped * pageWidth;
    if (typeof (el as any).scrollTo === "function") {
      el.scrollTo({ left: nextLeft, behavior });
      return;
    }
    el.scrollLeft = nextLeft;
  }, [streamPages.length]);

  const handlePagerScroll = useCallback(() => {
    const el = pagerRef.current;
    if (!el) return;
    if (pagerScrollTimerRef.current) window.clearTimeout(pagerScrollTimerRef.current);
    pagerScrollTimerRef.current = window.setTimeout(() => {
      const w = el.clientWidth || 1;
      const idx = Math.max(0, Math.min(streamPages.length - 1, Math.round(el.scrollLeft / w)));
      if (idx === pagerLastIdxRef.current) return;
      pagerLastIdxRef.current = idx;
      skipAutoScrollRef.current = true;
      setSelectedStreamId(streamPages[idx]?.streamId ?? null);
      // UX: snap to exact page after swipe settles.
      window.setTimeout(() => scrollToPage(idx, "smooth"), 140);
    }, 80);
  }, [streamPages, streamPages.length, scrollToPage]);

  const navHoverTimerRef = useRef<number | null>(null);
  const navIntentRef = useRef<"prev" | "next" | null>(null);
  const scheduleNavIntent = useCallback(
    (intent: "prev" | "next" | null) => {
      navIntentRef.current = intent;
      if (navHoverTimerRef.current) {
        window.clearTimeout(navHoverTimerRef.current);
        navHoverTimerRef.current = null;
      }
      if (!intent) return;
      navHoverTimerRef.current = window.setTimeout(() => {
        const idx = activePageIndex;
        const nextIdx = intent === "prev" ? idx - 1 : idx + 1;
        if (nextIdx < 0 || nextIdx >= streamPages.length) return;
        setSelectedStreamId(streamPages[nextIdx]?.streamId ?? null);
        scrollToPage(nextIdx);
      }, 420);
    },
    [activePageIndex, scrollToPage, streamPages]
  );

  useEffect(() => {
    return () => {
      if (navHoverTimerRef.current) window.clearTimeout(navHoverTimerRef.current);
      if (pagerScrollTimerRef.current) window.clearTimeout(pagerScrollTimerRef.current);
    };
  }, []);

  useEffect(() => {
    // Sync visual position with URL/state changes, unless it was a user scroll.
    if (skipAutoScrollRef.current) {
      skipAutoScrollRef.current = false;
      return;
    }
    scrollToPage(activePageIndex, "auto");
  }, [activePageIndex, scrollToPage]);

  useEffect(() => {
    if (!createOpened) return;
    const def =
      selectedStreamId ??
      taskStreams.find((s) => s.slug === "general")?.id ??
      taskStreams[0]?.id ??
      null;
    if (def) setCreateStreamId(def);
  }, [createOpened, selectedStreamId, taskStreams]);

  useEffect(() => {
    if (!detailTask) {
      setBlockedReasonDraft("");
      return;
    }
    setBlockedReasonDraft(detailTask.blocked_reason ?? "");
  }, [detailTask?.id, detailTask?.blocked_reason]);

  const detailAssigneeServerSig = detailTask
    ? JSON.stringify([...taskAssigneeIdList(detailTask)].sort())
    : "";
  useEffect(() => {
    if (!detailTask) {
      setDetailAssigneeDraft([]);
      return;
    }
    setDetailAssigneeDraft(taskAssigneeIdList(detailTask));
  }, [detailTask?.id, detailAssigneeServerSig]);

  useEffect(() => {
    if (!detailTask) {
      setDetailDueDayIso("");
      setDetailDueTimeStr("");
      return;
    }
    if (!detailTask.due_at) {
      setDetailDueDayIso("");
      setDetailDueTimeStr("");
      return;
    }
    const d = dayjs(detailTask.due_at);
    setDetailDueDayIso(d.format("YYYY-MM-DD"));
    setDetailDueTimeStr(d.format("HH:mm"));
  }, [detailTask?.id, detailTask?.due_at]);

  const canEditAssignees =
    adminSession?.permissions?.includes("manage_tasks") ||
    adminSession?.permissions?.includes("assign_tasks");

  const canPatchTaskFields =
    Boolean(adminSession?.permissions?.includes("manage_tasks")) ||
    Boolean(adminSession?.permissions?.includes("assign_tasks")) ||
    Boolean(adminSession?.permissions?.includes("tasks.change_status"));

  // moved above (used earlier for stream movement)
  const canEditClinicBoardLayout = Boolean(
    adminSession?.permissions?.includes("tasks.manage_clinic_board")
  );

  useEffect(() => {
    if (!taskBoards.length || boardInitRef.current) return;
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem("adminKanbanBoardId") : null;
    if (saved && taskBoards.some((b) => b.id === saved)) {
      setSelectedBoardId(saved);
    } else {
      const clinicWide = taskBoards.find((b) => b.kind === "clinic_wide");
      setSelectedBoardId((clinicWide ?? taskBoards[0]).id);
    }
    boardInitRef.current = true;
  }, [taskBoards]);

  useEffect(() => {
    if (selectedBoardId && typeof localStorage !== "undefined") {
      localStorage.setItem("adminKanbanBoardId", selectedBoardId);
    }
  }, [selectedBoardId]);

  const selectedBoard = useMemo(
    () => taskBoards.find((b) => b.id === selectedBoardId),
    [taskBoards, selectedBoardId]
  );

  const canEditSelectedBoardColumns = useMemo(() => {
    if (!selectedBoard || !canManageBoards) return false;
    if (selectedBoard.kind === "personal") {
      return selectedBoard.owner_admin_id === currentAdminId;
    }
    return canEditClinicBoardLayout;
  }, [selectedBoard, canManageBoards, canEditClinicBoardLayout, currentAdminId]);

  const detailDueComposite = useMemo(
    () => (detailDueDayIso && detailDueTimeStr ? `${detailDueDayIso}T${detailDueTimeStr}` : ""),
    [detailDueDayIso, detailDueTimeStr]
  );

  const detailDueInPast = useMemo(() => {
    if (!detailDueDayIso || !detailDueTimeStr) return false;
    const wall = dayjs(`${detailDueDayIso}T${detailDueTimeStr}`);
    return wall.isValid() && wall.isBefore(dayjs().startOf("day"));
  }, [detailDueDayIso, detailDueTimeStr]);

  const detailDueUnchanged = useMemo(() => {
    if (!detailTask) return true;
    if (!detailTask.due_at) {
      return !detailDueComposite;
    }
    if (!detailDueComposite) return false;
    const cur = dayjs(detailTask.due_at);
    return cur.format("YYYY-MM-DD") === detailDueDayIso && cur.format("HH:mm") === detailDueTimeStr;
  }, [detailTask, detailDueComposite, detailDueDayIso, detailDueTimeStr]);

  const assigneeListUnchanged = useMemo(() => {
    if (!detailTask) return true;
    const cur = [...taskAssigneeIdList(detailTask)].sort().join(",");
    const next = [...detailAssigneeDraft].sort().join(",");
    return cur === next;
  }, [detailTask, detailAssigneeDraft]);

  const detailContextUnchanged = useMemo(() => {
    if (!detailTask || detailStreamDraft === null) return true;
    const tagsEq =
      JSON.stringify([...(detailTask.tag_ids ?? [])].sort()) ===
      JSON.stringify([...detailTagDraft].sort());
    return detailTask.stream_id === detailStreamDraft && tagsEq;
  }, [detailTask, detailStreamDraft, detailTagDraft]);

  useEffect(() => {
    if (!dragError) return;
    const t = window.setTimeout(() => setDragError(null), 3500);
    return () => window.clearTimeout(t);
  }, [dragError]);

  useEffect(() => {
    if (!bulkResultMessage) return;
    const t = window.setTimeout(() => setBulkResultMessage(null), 5500);
    return () => window.clearTimeout(t);
  }, [bulkResultMessage]);

  useEffect(() => {
    if (!inviteEventId && taskCalendarContext.length > 0) {
      setInviteEventId(taskCalendarContext[0].event_id);
    }
  }, [inviteEventId, taskCalendarContext]);

  useEffect(() => {
    if (!createOpened) return;
    const now = dayjs();
    setDueDayIso(now.format("YYYY-MM-DD"));
    setDueTimeStr(now.format("HH:mm"));
    setTaskDueMonth(now.startOf("month"));
  }, [createOpened]);

  const createDueInPast = useMemo(() => {
    if (!dueDayIso || !dueTimeStr) return false;
    const wall = dayjs(`${dueDayIso}T${dueTimeStr}`);
    return wall.isValid() && wall.isBefore(dayjs().startOf("day"));
  }, [dueDayIso, dueTimeStr]);

  const handleCreate = () => {
    if (!title.trim()) return;
    if (!createStreamId) return;
    if (assigneeIds.length === 0 || !dueDate) return;
    if (createDueInPast) return;
    createTaskMutation.mutate(
      {
        title: title.trim(),
        description: description.trim() || null,
        priority: priority ?? "medium",
        stream_id: createStreamId ?? undefined,
        tag_ids: createTagIds.length ? createTagIds : undefined,
        assignee_ids: assigneeIds,
        due_at: dueDate ? new Date(dueDate).toISOString() : null,
      },
      {
        onSuccess: () => {
          setCreateOpened(false);
          setTitle("");
          setDescription("");
          setPriority("medium");
          setAssigneeIds([]);
          setCreateTagIds([]);
          const n = dayjs();
          setDueDayIso(n.format("YYYY-MM-DD"));
          setDueTimeStr(n.format("HH:mm"));
          setTaskDueMonth(n.startOf("month"));
        },
      }
    );
  };

  const adminOptions = admins.map((a) => ({
    value: a.id,
    label: a.full_name || a.email || a.id.slice(0, 8),
  }));

  const activeNeedsApprovalCount = useMemo(() => {
    const list = selectedStreamId ? allTasks.filter((t) => t.stream_id === selectedStreamId) : allTasks;
    const ids = list
      .filter(
        (t) =>
          t.status === "review" ||
          (t.source?.startsWith("ai") && t.status !== "done" && t.status !== "cancelled")
      )
      .filter((t) => {
        if (!currentAdminId) return true;
        const assignees = taskAssigneeIdList(t);
        return assignees.length === 0 || assignees.includes(currentAdminId);
      });
    return ids.length;
  }, [allTasks, selectedStreamId, currentAdminId]);


  const moveColumnDraft = useCallback((i: number, dir: -1 | 1) => {
    setColumnDraft((prev) => {
      const j = i + dir;
      if (j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[i], next[j]] = [next[j], next[i]];
      return next;
    });
  }, []);

  const handleKeyboardColumnMove = (taskId: string, direction: -1 | 1) => {
    const task = allTasks.find((t) => t.id === taskId);
    if (!task) return;
    // Default fallback ordering for keyboard moves uses global STATUS_ORDER.
    const idx = STATUS_ORDER.findIndex((s) => s === task.status);
    if (idx < 0) return;
    const target = STATUS_ORDER[idx + direction];
    if (!target) return;
    updateStatusMutation.mutate({ taskId: task.id, status: target });
  };

  // Bulk status actions were intentionally removed from the main toolbar UX (can be re-added later in Settings).

  if (streamsLoading || tagsLoading || !streamFilterInitialized || boardsLoading || tasksLoading) {
    return (
      <Stack>
        <ContextBar title="Задачи" />
        <PageSkeleton variant="cards" rows={6} />
      </Stack>
    );
  }

  return (
    <Box
      className="admin-tasks-context"
      data-page-tint={streamPageTintKey(activeStream?.theme)}
      style={{ borderRadius: "var(--radius-md)", minHeight: "100%" }}
    >
      <Stack>
      <ContextBar
        title="Задачи"
        actions={
          <Button size="sm" onClick={() => setCreateOpened(true)}>
            Новая задача
          </Button>
        }
      />

      <AdminDataTableToolbar>
        <Group gap="xs" wrap="wrap" justify="space-between" align="flex-end">
          <Group gap="xs" wrap="wrap">
            <Button.Group>
              <Button
                size="xs"
                variant="default"
                onClick={() => {
                  if (activePageIndex <= 0) return;
                  const next = Math.max(0, activePageIndex - 1);
                  setSelectedStreamId(streamPages[next]?.streamId ?? null);
                  scrollToPage(next);
                }}
                disabled={activePageIndex <= 0}
              >
                {"<"}
              </Button>
              <Button
                size="xs"
                variant="default"
                onClick={() => {
                  if (activePageIndex >= streamPages.length - 1) return;
                  const next = Math.min(streamPages.length - 1, activePageIndex + 1);
                  setSelectedStreamId(streamPages[next]?.streamId ?? null);
                  scrollToPage(next);
                }}
                disabled={activePageIndex >= streamPages.length - 1}
              >
                {">"}
              </Button>
            </Button.Group>

            <PagerDots count={streamPages.length} activeIndex={activePageIndex} />

            <Menu shadow="md" width={280} withinPortal>
              <Menu.Target>
                <Button size="xs" variant="light">
                  {activeStream?.name ?? "Все потоки"}
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>Потоки</Menu.Label>
                {streamPages.map((p) => (
                  <Menu.Item
                    key={p.key}
                    onClick={() => {
                      setSelectedStreamId(p.streamId);
                      const idx = streamPages.findIndex((x) => x.key === p.key);
                      if (idx >= 0) scrollToPage(idx);
                    }}
                  >
                    {p.label}
                  </Menu.Item>
                ))}
                {canManageBoards ? (
                  <>
                    <Menu.Divider />
                    <Menu.Item
                      leftSection={<IconPlus size={14} />}
                      onClick={() => {
                        setNewStreamName("");
                        setNewStreamModalOpened(true);
                      }}
                    >
                      Новый поток
                    </Menu.Item>
                  </>
                ) : null}
              </Menu.Dropdown>
            </Menu>

            {activeStream && canManageBoards ? (
              <ActionIcon
                variant="light"
                color="indigo"
                aria-label="Цвет потока"
                onClick={() => setStreamThemeModalOpened(true)}
              >
                <IconPalette size={16} />
              </ActionIcon>
            ) : null}

            <TextInput
              size="xs"
              placeholder="Поиск…"
              leftSection={<IconSearch size={14} />}
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.currentTarget.value)}
              w={220}
            />

            <Select
              size="xs"
              placeholder="Исполнитель"
              data={adminOptions}
              value={filterAssignee}
              onChange={setFilterAssignee}
              clearable
              w={190}
            />

            <Select
              size="xs"
              placeholder="Срок"
              data={[
                { value: "all", label: "Все сроки" },
                { value: "today", label: "Сегодня" },
                { value: "overdue", label: "Просрочено" },
              ]}
              value={filterDue}
              onChange={(v) => setFilterDue(v ?? "all")}
              w={150}
            />

            <Menu shadow="md" width={320} withinPortal>
              <Menu.Target>
                <Button size="xs" variant="default" leftSection={<IconFilter size={14} />}>
                  Фильтры
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>Фильтры</Menu.Label>
                <Menu.Item
                  onClick={() => setOnlyNeedsMyApproval((v) => !v)}
                >
                  {onlyNeedsMyApproval ? "Показывать все задачи" : `Ждут подтверждения (${activeNeedsApprovalCount})`}
                </Menu.Item>
                <Menu.Divider />
                <Box p="xs">
                  <Group gap="xs" wrap="wrap">
                    <Select
                      size="xs"
                      placeholder="Приоритет"
                      data={[
                        { value: "low", label: "Низкий" },
                        { value: "medium", label: "Средний" },
                        { value: "high", label: "Высокий" },
                        { value: "urgent", label: "Срочно" },
                      ]}
                      value={filterPriority}
                      onChange={setFilterPriority}
                      clearable
                      w={160}
                    />
                    <MultiSelect
                      size="xs"
                      placeholder="Теги"
                      data={taskTags.map((t) => ({ value: t.id, label: t.name }))}
                      value={filterTagIds}
                      onChange={setFilterTagIds}
                      clearable
                      searchable
                      w={220}
                    />
                  </Group>
                </Box>
              </Menu.Dropdown>
            </Menu>
          </Group>

          <Group gap="xs" wrap="wrap">
            <Button size="xs" onClick={() => setCreateOpened(true)}>
              Новая задача
            </Button>
            {canManageBoards ? (
              <Menu shadow="md" width={320} withinPortal>
                <Menu.Target>
                  <ActionIcon variant="light" color="gray" aria-label="Настройки">
                    <IconSettings size={16} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>Настройки</Menu.Label>
                  <Menu.Item
                    leftSection={<IconLayoutKanban size={14} />}
                    onClick={() => {
                      if (!selectedBoard) return;
                      const sorted = [...selectedBoard.columns].sort((a, b) => a.sort_order - b.sort_order);
                      setColumnDraft(
                        sorted.map((c) => ({
                          mapped_status: c.mapped_status,
                          label: c.label,
                        }))
                      );
                      setBoardColumnModalOpened(true);
                    }}
                    disabled={!canEditSelectedBoardColumns}
                  >
                    Колонки (порядок/названия)
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconLayoutKanban size={14} />}
                    onClick={() => {}}
                    disabled
                  >
                    Доски колонок (скоро)
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            ) : null}
          </Group>
        </Group>
      </AdminDataTableToolbar>

      {/* bulk actions moved to Settings menu (later) */}

      {dragError ? (
        <Alert color={SEMANTIC.opsSeverity.warning} icon={<IconAlertTriangle size={16} />} variant="light">
          {dragError}
        </Alert>
      ) : null}
      {bulkResultMessage ? (
        <Alert color={SEMANTIC.opsSeverity.info} icon={<IconAlertTriangle size={16} />} variant="light">
          {bulkResultMessage}
        </Alert>
      ) : null}
      {onlyNeedsMyApproval ? (
        <Alert color="blue" icon={<IconAlertTriangle size={16} />} variant="light">
          <Group justify="space-between" wrap="wrap" gap="xs">
            <Text size="sm">
              Показаны только задачи, ожидающие вашего подтверждения. Остальные скрыты фильтром.
            </Text>
            <Button size="xs" variant="light" onClick={() => setOnlyNeedsMyApproval(false)}>
              Показать все задачи
            </Button>
          </Group>
        </Alert>
      ) : null}

      <Box
        ref={pagerRef}
        data-testid="stream-pager"
        onScroll={handlePagerScroll}
        className="admin-stream-pager"
        style={{
          display: "flex",
          overflowX: "auto",
          scrollSnapType: "x mandatory",
          scrollBehavior: "smooth",
          gap: "var(--space-md)",
          paddingBottom: "var(--space-sm)",
        }}
      >
        {streamPages.map((p, i) => {
          const shouldRender = Math.abs(i - activePageIndex) <= 1;
          const pageTint = streamPageTintKey(p.stream?.theme);
          const accent = streamMantineColorKey(p.stream?.theme);
          const streamName = p.streamId ? p.label : "Все потоки";
          return (
            <Box
              key={p.key}
              data-stream-page-index={i}
              style={{
                flex: "0 0 100%",
                scrollSnapAlign: "start",
                minWidth: 0,
              }}
            >
              <StreamPageShell pageTint={pageTint} accentColor={accent}>
                {shouldRender ? (
                  <TasksKanbanPage
                    streamId={p.streamId}
                    streamName={streamName}
                    streamTheme={p.stream?.theme}
                    allTasks={allTasks}
                    taskStreams={taskStreams}
                    admins={admins}
                    patientIdToName={patientIdToName}
                    currentAdminId={currentAdminId}
                    myFocusTasks={myFocusTasks}
                    selectedBoard={selectedBoard}
                    wipPolicies={wipPolicies}
                    canMoveTasksAcrossStreams={canMoveTasksAcrossStreams}
                    streamMoveOptions={streamMoveOptions}
                    selectedTaskIds={selectedTaskIds}
                    setSelectedTaskIds={setSelectedTaskIds}
                    onlyNeedsMyApproval={onlyNeedsMyApproval}
                    filterAssignee={filterAssignee}
                    filterPriority={filterPriority}
                    filterDue={filterDue}
                    filterQuery={debouncedFilterQuery}
                    setOnlyNeedsMyApproval={setOnlyNeedsMyApproval}
                    setDetailTaskId={setDetailTaskId}
                    setTaskChatId={setTaskChatId}
                    claimMutation={claimMutation}
                    patchStreamTagsMutation={patchStreamTagsMutation}
                    updateStatusMutation={updateStatusMutation}
                    reorderTasksMutation={reorderTasksMutation}
                    setDragError={setDragError}
                    scheduleNavIntent={scheduleNavIntent}
                    handleKeyboardColumnMove={handleKeyboardColumnMove}
                    activePageIndex={activePageIndex}
                    streamPagesLength={streamPages.length}
                  />
                ) : (
                  <PageSkeleton variant="cards" rows={4} />
                )}
              </StreamPageShell>
            </Box>
          );
        })}
      </Box>

      <AdminDataTableSurface>
        <Text size="sm" fw={700} mb={6}>
          Аудит перемещений
        </Text>
        {auditTrail.length === 0 ? (
          <Text size="xs" c="dimmed">
            Пока нет перемещений в этой сессии.
          </Text>
        ) : (
          <Stack gap={4}>
            {auditTrail.slice(0, 8).map((a) => (
              <Text key={a.id} size="xs" c="dimmed">
                {dayjs(a.at).format("DD.MM HH:mm")} · {a.taskTitle} · {STATUS_META[a.from] ?? a.from} →{" "}
                {STATUS_META[a.to] ?? a.to}
              </Text>
            ))}
          </Stack>
        )}
      </AdminDataTableSurface>

      <GlassModal
        size="lg"
        centered
        styles={{ body: { maxHeight: "calc(100vh - 180px)", overflowY: "auto" } }}
        opened={!!detailTaskId && !!detailTask}
        onClose={() => {
          setDetailTaskId(null);
          setDetailCommentDraft("");
          setDetailModalApiError(null);
        }}
        title={detailTask ? detailTask.title : "Задача"}
      >
        {detailTask ? (
          <Stack gap="md">
            {detailModalApiError ? (
              <Alert color="red" variant="light" icon={<IconAlertTriangle size={16} />}>
                {detailModalApiError}
              </Alert>
            ) : null}
            <Box
              p="md"
              style={{
                ...taskStatusCardSurface(detailTask.status),
                borderRadius: "var(--calendar-slot-radius)",
              }}
            >
              <Group gap="xs" wrap="wrap">
                <Badge size="sm" variant="light" color={priorityBadgeColor(detailTask.priority)} tt="uppercase">
                  {detailTask.priority}
                </Badge>
                <Badge size="sm" variant="transparent" tt="uppercase" styles={taskStatusBadgeStyles(detailTask.status)}>
                  {STATUS_META[detailTask.status] ?? detailTask.status}
                </Badge>
              </Group>
              {detailTask.description ? (
                <Text size="sm" mt="sm" style={{ whiteSpace: "pre-wrap", color: taskStatusTextColors(detailTask.status).title }}>
                  {detailTask.description}
                </Text>
              ) : (
                <Text size="sm" mt="sm" c="dimmed">
                  Без описания
                </Text>
              )}
              <Text size="xs" mt="xs" style={{ color: taskStatusTextColors(detailTask.status).meta }}>
                Срок: {detailTask.due_at ? dayjs(detailTask.due_at).format("DD.MM.YYYY HH:mm") : "—"}
                {!canEditAssignees ? (
                  <>
                    {" "}
                    · Исполнители:{" "}
                    {(() => {
                      const ids = taskAssigneeIdList(detailTask);
                      if (!ids.length) return detailTask.role_assignee || "—";
                      return ids.map((id, idx) => {
                        const a = admins.find((x) => x.id === id);
                        return (
                          <span key={id}>
                            <PersonNameLink kind="staff" id={id} label={a?.full_name || a?.email || null} size="xs" />
                            {idx < ids.length - 1 ? ", " : ""}
                          </span>
                        );
                      });
                    })()}
                  </>
                ) : null}
              </Text>
            </Box>
            {canEditAssignees ? (
              <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
                <Stack gap="xs">
                  <Text size="sm" fw={600}>
                    Исполнители
                  </Text>
                  <MultiSelect
                    label="Назначение и делегирование"
                    description="Первый в списке — основной исполнитель. Можно добавить или убрать любого сотрудника клиники."
                    placeholder="Выберите одного или нескольких"
                    data={adminOptions}
                    value={detailAssigneeDraft}
                    onChange={setDetailAssigneeDraft}
                    searchable
                    hidePickedOptions
                    clearable
                  />
                  <Checkbox
                    label="Добавить служебную запись в комментарии об изменении состава"
                    checked={assigneeAuditComment}
                    onChange={(e) => setAssigneeAuditComment(e.currentTarget.checked)}
                  />
                  <Group justify="flex-end">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => detailTask && setDetailAssigneeDraft(taskAssigneeIdList(detailTask))}
                      disabled={assigneeListUnchanged}
                    >
                      Сбросить
                    </Button>
                    <Button
                      size="xs"
                      onClick={() => {
                        if (!detailTask || assigneeListUnchanged) return;
                        setDetailModalApiError(null);
                        patchAssigneesMutation.mutate(
                          { taskId: detailTask.id, assignee_ids: detailAssigneeDraft },
                          {
                            onSuccess: () => {
                              setDetailModalApiError(null);
                              if (assigneeAuditComment) {
                                postDetailComment.mutate("Системное событие: обновлён состав исполнителей.");
                              }
                            },
                            onError: (e) => {
                              setDetailModalApiError(
                                e instanceof ApiErrorWithCode
                                  ? e.message
                                  : "Не удалось сохранить исполнителей"
                              );
                            },
                          }
                        );
                      }}
                      loading={patchAssigneesMutation.isPending}
                      disabled={assigneeListUnchanged}
                    >
                      Сохранить исполнителей
                    </Button>
                  </Group>
                </Stack>
              </Card>
            ) : null}
            {canManageBoards ? (
              <Card
                withBorder
                p="sm"
                style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}
              >
                <Stack gap="xs">
                  <Text size="sm" fw={600}>
                    Поток и теги
                  </Text>
                  <Select
                    label="Поток"
                    placeholder="Выберите поток"
                    data={taskStreams
                      .filter((s) => !s.is_archived)
                      .map((s) => ({ value: s.id, label: s.name }))}
                    value={detailStreamDraft}
                    onChange={(v) => setDetailStreamDraft(v)}
                    searchable
                  />
                  <MultiSelect
                    label="Теги"
                    placeholder="Необязательно"
                    data={taskTags.map((t) => ({ value: t.id, label: t.name }))}
                    value={detailTagDraft}
                    onChange={setDetailTagDraft}
                    searchable
                    clearable
                  />
                  <Group justify="flex-end">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        if (!detailTask) return;
                        setDetailStreamDraft(detailTask.stream_id);
                        setDetailTagDraft([...(detailTask.tag_ids ?? [])]);
                      }}
                      disabled={detailContextUnchanged}
                    >
                      Сбросить
                    </Button>
                    <Button
                      size="xs"
                      onClick={() => {
                        if (!detailTask || detailStreamDraft === null || detailContextUnchanged) return;
                        setDetailModalApiError(null);
                        patchStreamTagsMutation.mutate(
                          {
                            taskId: detailTask.id,
                            stream_id: detailStreamDraft,
                            tag_ids: detailTagDraft,
                          },
                          {
                            onSuccess: () => setDetailModalApiError(null),
                            onError: (e) => {
                              setDetailModalApiError(
                                e instanceof ApiErrorWithCode
                                  ? e.message
                                  : "Не удалось сохранить поток и теги"
                              );
                            },
                          }
                        );
                      }}
                      loading={patchStreamTagsMutation.isPending}
                      disabled={detailContextUnchanged || detailStreamDraft === null}
                    >
                      Сохранить поток и теги
                    </Button>
                  </Group>
                </Stack>
              </Card>
            ) : null}
            {canPatchTaskFields ? (
              <Card
                withBorder
                p="sm"
                style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}
              >
                <Stack gap="xs">
                  <Text size="sm" fw={600}>
                    Срок выполнения
                  </Text>
                  <Text size="xs" c="dimmed">
                    Дата и время по локальному времени браузера; на сервере действует политика «не раньше сегодняшнего
                    календарного дня (UTC)».
                  </Text>
                  <Group align="flex-end" gap="md" wrap="wrap">
                    <TextInput
                      label="Дата"
                      type="date"
                      value={detailDueDayIso}
                      onChange={(e) => setDetailDueDayIso(e.currentTarget.value)}
                      styles={{ root: { minWidth: 160 } }}
                    />
                    <TextInput
                      label="Время"
                      type="time"
                      value={detailDueTimeStr}
                      onChange={(e) => setDetailDueTimeStr(e.currentTarget.value)}
                      styles={{ root: { minWidth: 120 } }}
                    />
                  </Group>
                  {detailDueInPast ? (
                    <Alert color="orange" variant="light" icon={<IconAlertTriangle size={16} />}>
                      Выбранный срок в прошлом — сервер отклонит сохранение.
                    </Alert>
                  ) : null}
                  <Group justify="flex-end" wrap="wrap">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        if (!detailTask) return;
                        setDetailModalApiError(null);
                        patchDueMutation.mutate(
                          { taskId: detailTask.id, due_at: null },
                          {
                            onSuccess: () => setDetailModalApiError(null),
                            onError: (e) => {
                              setDetailModalApiError(
                                e instanceof ApiErrorWithCode ? e.message : "Не удалось сбросить срок"
                              );
                            },
                          }
                        );
                      }}
                      loading={patchDueMutation.isPending}
                      disabled={!detailTask.due_at}
                    >
                      Без срока
                    </Button>
                    <Button
                      size="xs"
                      onClick={() => {
                        if (!detailTask || !detailDueComposite || detailDueUnchanged || detailDueInPast) return;
                        setDetailModalApiError(null);
                        patchDueMutation.mutate(
                          {
                            taskId: detailTask.id,
                            due_at: new Date(detailDueComposite).toISOString(),
                          },
                          {
                            onSuccess: () => setDetailModalApiError(null),
                            onError: (e) => {
                              setDetailModalApiError(
                                e instanceof ApiErrorWithCode ? e.message : "Не удалось сохранить срок"
                              );
                            },
                          }
                        );
                      }}
                      loading={patchDueMutation.isPending}
                      disabled={!detailDueComposite || detailDueUnchanged || detailDueInPast}
                    >
                      Сохранить срок
                    </Button>
                  </Group>
                </Stack>
              </Card>
            ) : null}
            <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
              <Stack gap="xs">
                <Group justify="space-between" wrap="wrap">
                  <Text size="sm" fw={600}>
                    Критерии перехода
                  </Text>
                  <Button
                    size="xs"
                    variant="outline"
                    color={detailTask.blocked ? "red" : "indigo"}
                    leftSection={detailTask.blocked ? <IconLockOpen size={12} /> : <IconLock size={12} />}
                    onClick={() =>
                      updateTaskMetaMutation.mutate({
                        taskId: detailTask.id,
                        blocked: !detailTask.blocked,
                      })
                    }
                  >
                    {detailTask.blocked ? "Разблокировать" : "Заблокировать"}
                  </Button>
                </Group>
                {detailTask.blocked ? (
                  <Stack gap="xs">
                    <TextInput
                      label="Причина блокировки"
                      placeholder="Опишите, что мешает завершить задачу"
                      value={blockedReasonDraft}
                      onChange={(e) => setBlockedReasonDraft(e.currentTarget.value)}
                    />
                    <Group justify="flex-end">
                      <Button
                        size="xs"
                        variant="light"
                        onClick={() =>
                          updateTaskMetaMutation.mutate({
                            taskId: detailTask.id,
                            blocked: true,
                            blocked_reason: blockedReasonDraft.trim() || null,
                          })
                        }
                        loading={updateTaskMetaMutation.isPending}
                      >
                        Сохранить причину
                      </Button>
                    </Group>
                  </Stack>
                ) : null}
                <Checkbox
                  label="Checklist завершения подтвержден"
                  checked={Boolean(detailTask.checklist_done)}
                  onChange={(e) =>
                    updateTaskMetaMutation.mutate({
                      taskId: detailTask.id,
                      checklist_done: e.currentTarget.checked,
                    })
                  }
                />
              </Stack>
            </Card>
            <Group gap="xs" wrap="wrap">
              {detailTask.patient_id && (
                <Button
                  component={Link}
                  to={`/admin/omni-chat?patient_id=${detailTask.patient_id}`}
                  variant="light"
                  size="xs"
                  leftSection={<IconMessageCircle size={14} />}
                >
                  Чат с клиентом
                </Button>
              )}
              {detailTask.booking_id && (
                <Button
                  component={Link}
                  to={`/admin/schedule?booking_id=${detailTask.booking_id}`}
                  variant="light"
                  size="xs"
                  leftSection={<IconCalendarEvent size={14} />}
                >
                  Запись
                </Button>
              )}
              <Button
                component={Link}
                to={`${ROUTE_PATHS.admin.staffCalendar}?task_id=${detailTask.id}&open_create=1`}
                variant="outline"
                color="indigo"
                size="xs"
                leftSection={<IconCalendarEvent size={14} />}
              >
                В календарь
              </Button>
              <Button
                variant="outline"
                color="indigo"
                size="xs"
                leftSection={<IconMessages size={14} />}
                onClick={() => setTaskChatId(detailTask.id)}
              >
                Чат задачи
              </Button>
            </Group>
            {detailTask.patient_id && patientIdToPhone.get(detailTask.patient_id) && (
              <Group gap="xs">
                <Button
                  component="a"
                  href={`tel:${patientIdToPhone.get(detailTask.patient_id)!.replace(/\s/g, "")}`}
                  variant="subtle"
                  size="xs"
                  leftSection={<IconPhone size={14} />}
                >
                  Позвонить
                </Button>
                <Button
                  component="a"
                  href={`https://wa.me/${patientIdToPhone.get(detailTask.patient_id)!.replace(/\D/g, "").replace(/^8/, "7")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  variant="subtle"
                  size="xs"
                  leftSection={<IconBrandWhatsapp size={14} />}
                >
                  WhatsApp
                </Button>
              </Group>
            )}
            <Menu shadow="md" width={260}>
              <Menu.Target>
                <Button variant="filled" color="indigo">
                  Сменить статус
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item
                  onClick={() => {
                    moveTask(detailTask, "open");
                  }}
                >
                  Открыто
                </Menu.Item>
                <Menu.Item
                  onClick={() => {
                    moveTask(detailTask, "in_progress");
                  }}
                >
                  В работе
                </Menu.Item>
                <Menu.Item
                  onClick={() => {
                    moveTask(detailTask, "on_hold");
                  }}
                >
                  На паузе
                </Menu.Item>
                <Menu.Item
                  onClick={() => {
                    moveTask(detailTask, "review");
                  }}
                >
                  На проверке
                </Menu.Item>
                <Menu.Item
                  onClick={() => {
                    moveTask(detailTask, "done");
                  }}
                >
                  Выполнено
                </Menu.Item>
                <Menu.Item
                  color="red"
                  onClick={() => {
                    moveTask(detailTask, "cancelled");
                  }}
                >
                  Отменить
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
            <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
              <Text size="sm" fw={600} mb={6}>
                История переходов
              </Text>
              {detailTransitions.length === 0 ? (
                <Text size="xs" c="dimmed">
                  Пока нет переходов статусов.
                </Text>
              ) : (
                <Stack gap={4}>
                  {detailTransitions.slice(0, 6).map((tr) => (
                    <Text key={tr.id} size="xs" c="dimmed">
                      {dayjs(tr.created_at).format("DD.MM HH:mm")} · {STATUS_META[tr.from_status] ?? tr.from_status} →{" "}
                      {STATUS_META[tr.to_status] ?? tr.to_status}
                      {tr.reason ? ` · ${tr.reason}` : ""}
                      {tr.metadata && typeof tr.metadata === "object" && "event" in tr.metadata
                        ? ` · ${String((tr.metadata as Record<string, unknown>).event)}`
                        : ""}
                    </Text>
                  ))}
                </Stack>
              )}
            </Card>
            <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
              <Text size="sm" fw={600} mb={6}>
                Календарные слоты задачи
              </Text>
              {taskCalendarContext.length === 0 ? (
                <Text size="xs" c="dimmed">
                  Нет связанных слотов. Нажмите «В календарь», чтобы создать слот из этой задачи.
                </Text>
              ) : (
                <Stack gap="xs">
                  {taskCalendarContext.map((ev) => (
                    <Paper key={ev.event_id} p="xs" withBorder>
                      <Group justify="space-between" wrap="nowrap">
                        <Text size="sm" fw={500} lineClamp={1}>
                          {ev.title}
                        </Text>
                        <Badge size="xs" variant="light" color={ev.acknowledged_count < ev.participants_count ? "orange" : "teal"}>
                          ACK {ev.acknowledged_count}/{ev.participants_count}
                        </Badge>
                      </Group>
                      <Text size="xs" c="dimmed" mt={4}>
                        {dayjs(ev.starts_at).format("DD.MM HH:mm")} - {dayjs(ev.ends_at).format("HH:mm")}
                      </Text>
                      <Text size="xs" c="dimmed" mt={4}>
                        Участники:{" "}
                        {ev.participants
                          .map((p) => `${p.full_name || "Сотрудник"}${p.acknowledged_at ? " (ACK)" : ""}`)
                          .join(", ") || "—"}
                      </Text>
                    </Paper>
                  ))}
                  <Group align="end" wrap="wrap">
                    <Select
                      size="xs"
                      label="Слот"
                      data={taskCalendarContext.map((ev) => ({
                        value: ev.event_id,
                        label: `${dayjs(ev.starts_at).format("DD.MM HH:mm")} · ${ev.title}`,
                      }))}
                      value={inviteEventId}
                      onChange={setInviteEventId}
                      w={280}
                    />
                    <MultiSelect
                      size="xs"
                      label="Пригласить в слот"
                      data={adminOptions}
                      value={inviteAdminIds}
                      onChange={setInviteAdminIds}
                      searchable
                      w={340}
                    />
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        if (!inviteEventId || inviteAdminIds.length === 0) return;
                        inviteParticipantsMutation.mutate(inviteAdminIds, {
                          onSuccess: () => setInviteAdminIds([]),
                        });
                      }}
                      loading={inviteParticipantsMutation.isPending}
                      disabled={!inviteEventId || inviteAdminIds.length === 0}
                    >
                      Пригласить
                    </Button>
                  </Group>
                </Stack>
              )}
            </Card>
            <Text size="sm" fw={600}>
              Комментарии
            </Text>
            {detailCommentsLoading ? (
              <Loader size="sm" />
            ) : (
              <ScrollArea h={240} offsetScrollbars>
                <Stack gap="xs">
                  {detailComments.length === 0 ? (
                    <Text size="sm" c="dimmed">
                      Пока нет комментариев.
                    </Text>
                  ) : (
                    detailComments.map((c) => (
                      <Paper
                        key={c.id}
                        p="xs"
                        withBorder
                        style={{ borderColor: "var(--calendar-card-border)", background: "var(--mantine-color-body)" }}
                      >
                        <Text size="xs" c="dimmed" mb={4}>
                          {c.author_full_name || "Сотрудник"} · {dayjs(c.created_at).format("DD.MM.YYYY HH:mm")}
                        </Text>
                        <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                          <AppleEmojiRichText text={c.text} />
                        </Text>
                      </Paper>
                    ))
                  )}
                </Stack>
              </ScrollArea>
            )}
            <Input.Wrapper label="Новый комментарий">
              <AppleEmojiOverlayTextarea
                ref={detailCommentTextareaRef}
                placeholder="Текст для команды…"
                minRows={2}
                value={detailCommentDraft}
                onChange={(e) => setDetailCommentDraft(e.currentTarget.value)}
              />
            </Input.Wrapper>
            <Group justify="space-between" align="center" wrap="wrap">
              <EmojiMartPopoverPicker
                actionIconProps={{ variant: "light", color: "indigo", size: "md" }}
                onPick={(native) => setDetailCommentDraft((prev) => prev + native)}
                onInserted={() => detailCommentTextareaRef.current?.focus()}
              />
              <Button
                color="indigo"
                onClick={() => {
                  const text = detailCommentDraft.trim();
                  if (!text || !detailTaskId) return;
                  postDetailComment.mutate(text, {
                    onSuccess: () => setDetailCommentDraft(""),
                  });
                }}
                loading={postDetailComment.isPending}
                disabled={!detailCommentDraft.trim()}
              >
                Отправить
              </Button>
            </Group>
          </Stack>
        ) : null}
      </GlassModal>

      <GlassModal
        size="xl"
        centered
        opened={createOpened}
        onClose={() => setCreateOpened(false)}
        title="Новая задача"
        styles={{
          content: {
            maxHeight: "min(92vh, 900px)",
            display: "flex",
            flexDirection: "column",
            width: "min(980px, 96vw)",
          },
          // Scroll is handled by Mantine Modal body (global CSS),
          // footer below is sticky to keep actions accessible.
          body: { padding: 0 },
        }}
      >
        <Stack gap="sm" p="md" pb="xl">
          {createDueInPast ? (
            <Alert color="orange" title="Срок в прошлом">
              Выберите сегодняшнюю дату или позже — иначе создание на сервере будет отклонено.
            </Alert>
          ) : null}

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
            <Stack gap="sm">
              <TextInput
                label="Заголовок задачи"
                placeholder="Например: Перезвонить пациенту по отменённой записи"
                value={title}
                onChange={(e) => setTitle(e.currentTarget.value)}
                required
              />
              <Textarea
                label="Описание"
                placeholder="Добавьте детали, ссылки, ID брони/лида и т.д."
                minRows={8}
                value={description}
                onChange={(e) => setDescription(e.currentTarget.value)}
              />
              <MultiSelect
                label="Исполнители"
                placeholder="Выберите одного или нескольких"
                data={adminOptions}
                value={assigneeIds}
                onChange={setAssigneeIds}
                required
                searchable
                hidePickedOptions
                comboboxProps={{ withinPortal: true }}
              />
            </Stack>

            <Stack gap="sm">
              <Select
                label="Приоритет"
                data={[
                  { value: "low", label: "Низкий" },
                  { value: "medium", label: "Средний" },
                  { value: "high", label: "Высокий" },
                  { value: "urgent", label: "Срочно" },
                ]}
                value={priority}
                onChange={setPriority}
              />
              <Select
                label="Поток"
                placeholder="Обязательно"
                required
                data={taskStreams
                  .filter((s) => !s.is_archived)
                  .map((s) => ({ value: s.id, label: s.name }))}
                value={createStreamId}
                onChange={(v) => setCreateStreamId(v)}
                searchable
                comboboxProps={{ withinPortal: true }}
              />
              <Group gap="xs" wrap="nowrap" align="flex-end">
                <MultiSelect
                  style={{ flex: 1, minWidth: 0 }}
                  label="Теги"
                  placeholder="Необязательно"
                  data={taskTags.map((t) => ({ value: t.id, label: t.name }))}
                  value={createTagIds}
                  onChange={setCreateTagIds}
                  searchable
                  clearable
                  comboboxProps={{ withinPortal: true }}
                />
                {canManageBoards ? (
                  <Button
                    size="xs"
                    variant="light"
                    mb={4}
                    leftSection={<IconPlus size={14} />}
                    onClick={() => {
                      setNewTagName("");
                      setNewTagModalOpened(true);
                    }}
                  >
                    Тег
                  </Button>
                ) : null}
              </Group>

              <Stack gap={6}>
                <Text size="sm" fw={700}>
                  Срок
                </Text>
                <Group align="flex-start" gap="md" wrap="wrap">
                  <CompactMonthPicker
                    value={dueDayIso}
                    onChange={(iso) => {
                      setDueDayIso(iso);
                      setTaskDueMonth(dayjs(iso).startOf("month"));
                    }}
                    monthAnchor={taskDueMonth}
                    onMonthAnchorChange={setTaskDueMonth}
                    size="compact"
                  />
                  <TextInput
                    label="Время"
                    type="time"
                    value={dueTimeStr}
                    onChange={(e) => setDueTimeStr(e.currentTarget.value)}
                    required
                    styles={{ root: { minWidth: 120 } }}
                  />
                </Group>
              </Stack>
            </Stack>
          </SimpleGrid>
        </Stack>

        <Box
          p="md"
          pt="sm"
          style={{
            position: "sticky",
            bottom: 0,
            borderTop: "1px solid var(--mantine-color-gray-3)",
            background: "var(--overlay-glass-surface)",
            zIndex: 2,
          }}
        >
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCreateOpened(false)}>
              Отмена
            </Button>
            <Button
              onClick={handleCreate}
              loading={createTaskMutation.isPending}
              disabled={
                !title.trim() ||
                !createStreamId ||
                assigneeIds.length === 0 ||
                !dueDate ||
                createDueInPast
              }
            >
              Создать
            </Button>
          </Group>
        </Box>
      </GlassModal>

      <GlassModal
        size="sm"
        centered
        opened={newStreamModalOpened}
        onClose={() => setNewStreamModalOpened(false)}
        title="Новый поток"
      >
        <Stack gap="sm">
          <TextInput
            label="Название"
            placeholder="Например: Дизайн"
            value={newStreamName}
            onChange={(e) => setNewStreamName(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setNewStreamModalOpened(false)}>
              Отмена
            </Button>
            <Button
              loading={createStreamMutation.isPending}
              disabled={!newStreamName.trim()}
              onClick={() => {
                const name = newStreamName.trim();
                if (!name) return;
                createStreamMutation.mutate(
                  { name },
                  {
                    onSuccess: (row) => {
                      setNewStreamModalOpened(false);
                      setNewStreamName("");
                      setSelectedStreamId(row.id);
                    },
                  }
                );
              }}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="sm"
        centered
        opened={streamThemeModalOpened}
        onClose={() => setStreamThemeModalOpened(false)}
        title={activeStream ? `Цвет потока: ${activeStream.name}` : "Цвет потока"}
      >
        <Stack gap="sm">
          <Select
            label="Фоновый tint"
            description="Мягкий градиент страницы потока (пресеты UI)."
            data={[
              { value: "none", label: "Нет" },
              { value: "subtle_gray", label: "Серый" },
              { value: "subtle_violet", label: "Фиолетовый" },
              { value: "subtle_blue", label: "Синий" },
              { value: "subtle_green", label: "Зелёный" },
              { value: "subtle_amber", label: "Янтарный" },
            ]}
            value={themeDraftTint}
            onChange={(v) => setThemeDraftTint((v as TaskStreamPageTint) ?? "none")}
          />
          <Select
            label="Акцент"
            description="Цвет для акцентов UI (Mantine preset)."
            data={[
              { value: "gray", label: "Gray" },
              { value: "red", label: "Red" },
              { value: "pink", label: "Pink" },
              { value: "grape", label: "Grape" },
              { value: "violet", label: "Violet" },
              { value: "indigo", label: "Indigo" },
              { value: "blue", label: "Blue" },
              { value: "cyan", label: "Cyan" },
              { value: "teal", label: "Teal" },
              { value: "green", label: "Green" },
              { value: "lime", label: "Lime" },
              { value: "yellow", label: "Yellow" },
              { value: "orange", label: "Orange" },
            ]}
            value={themeDraftColor}
            onChange={(v) => setThemeDraftColor((v as TaskStreamMantineColor) ?? "blue")}
            searchable
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setStreamThemeModalOpened(false)}>
              Отмена
            </Button>
            <Button
              disabled={!activeStream}
              loading={patchStreamMutation.isPending}
              onClick={() => {
                if (!activeStream) return;
                patchStreamMutation.mutate(
                  {
                    streamId: activeStream.id,
                    theme: { page_tint: themeDraftTint, mantine_color: themeDraftColor },
                  },
                  { onSuccess: () => setStreamThemeModalOpened(false) }
                );
              }}
            >
              Сохранить
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="sm"
        centered
        opened={newTagModalOpened}
        onClose={() => setNewTagModalOpened(false)}
        title="Новый тег"
      >
        <Stack gap="sm">
          <TextInput
            label="Название"
            placeholder="Например: Филиал А"
            value={newTagName}
            onChange={(e) => setNewTagName(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setNewTagModalOpened(false)}>
              Отмена
            </Button>
            <Button
              loading={createTagMutation.isPending}
              disabled={!newTagName.trim()}
              onClick={() => {
                const name = newTagName.trim();
                if (!name) return;
                createTagMutation.mutate(
                  { name },
                  {
                    onSuccess: (row) => {
                      setNewTagModalOpened(false);
                      setNewTagName("");
                      if (createOpened) {
                        setCreateTagIds((prev) => [...prev, row.id]);
                      } else {
                        setFilterTagIds((prev) => Array.from(new Set([...prev, row.id])));
                      }
                    },
                  }
                );
              }}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="md"
        centered
        opened={boardColumnModalOpened}
        onClose={() => setBoardColumnModalOpened(false)}
        title="Порядок колонок Kanban"
      >
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            Подпись пустая — стандартное имя статуса. Должны присутствовать все статусы (как на сервере).
          </Text>
          {columnDraft.map((col, i) => (
            <Group key={`${col.mapped_status}-${i}`} justify="space-between" wrap="nowrap" align="flex-start">
              <Text size="xs" w={130} ff="monospace">
                {col.mapped_status}
              </Text>
              <TextInput
                size="xs"
                placeholder={STATUS_META[col.mapped_status] ?? col.mapped_status}
                value={col.label ?? ""}
                onChange={(e) => {
                  const v = e.currentTarget.value;
                  setColumnDraft((prev) =>
                    prev.map((c, idx) =>
                      idx === i ? { ...c, label: v.trim() ? v : null } : c
                    )
                  );
                }}
                style={{ flex: 1, minWidth: 0 }}
              />
              <ActionIcon
                size="sm"
                variant="light"
                aria-label="Выше"
                onClick={() => moveColumnDraft(i, -1)}
                disabled={i === 0}
              >
                <IconChevronUp size={16} />
              </ActionIcon>
              <ActionIcon
                size="sm"
                variant="light"
                aria-label="Ниже"
                onClick={() => moveColumnDraft(i, 1)}
                disabled={i === columnDraft.length - 1}
              >
                <IconChevronDown size={16} />
              </ActionIcon>
            </Group>
          ))}
          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={() => setBoardColumnModalOpened(false)}>
              Отмена
            </Button>
            <Button
              loading={replaceBoardColumnsMutation.isPending}
              onClick={() => {
                if (!selectedBoardId) return;
                replaceBoardColumnsMutation.mutate(
                  { boardId: selectedBoardId, columns: columnDraft },
                  { onSuccess: () => setBoardColumnModalOpened(false) }
                );
              }}
            >
              Сохранить
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="md"
        centered
        styles={{ body: { maxHeight: "calc(100vh - 180px)", overflowY: "auto" } }}
        opened={!!taskChatId}
        onClose={() => {
          setTaskChatId(null);
          setTaskChatDraft("");
        }}
        title={taskChatTitle ? `Чат задачи: ${taskChatTitle}` : "Чат задачи"}
      >
        <Stack gap="sm" style={{ minHeight: 280 }}>
          {taskCommentsLoading ? (
            <Loader size="sm" />
          ) : (
            <ScrollArea h={320} offsetScrollbars>
              <Stack gap="xs">
                {taskComments.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    Пока нет сообщений. Напишите коллегам в контексте этой задачи.
                  </Text>
                ) : (
                  taskComments.map((c) => (
                    <Paper key={c.id} p="xs" withBorder>
                      <Text size="xs" c="dimmed" mb={4}>
                        {c.author_full_name || "Сотрудник"} ·{" "}
                        {dayjs(c.created_at).format("DD.MM.YYYY HH:mm")}
                      </Text>
                      <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        <AppleEmojiRichText text={c.text} />
                      </Text>
                    </Paper>
                  ))
                )}
              </Stack>
            </ScrollArea>
          )}
          {taskChatId ? (
            <Button
              component={Link}
              to={`/admin/staff-chat?task=${taskChatId}`}
              variant="light"
              size="xs"
            >
              Открыть thread в мессенджере персонала
            </Button>
          ) : null}
          <Input.Wrapper label="Сообщение">
            <AppleEmojiOverlayTextarea
              ref={taskChatTextareaRef}
              placeholder="Текст для команды…"
              minRows={3}
              value={taskChatDraft}
              onChange={(e) => setTaskChatDraft(e.currentTarget.value)}
            />
          </Input.Wrapper>
          <Group justify="space-between" align="center" wrap="wrap">
            <EmojiMartPopoverPicker
              actionIconProps={{ variant: "light", color: "indigo", size: "md" }}
              onPick={(native) => setTaskChatDraft((prev) => prev + native)}
              onInserted={() => taskChatTextareaRef.current?.focus()}
            />
            <Button
              onClick={() => {
                const text = taskChatDraft.trim();
                if (!text || !taskChatId) return;
                postTaskComment.mutate(text, {
                  onSuccess: () => setTaskChatDraft(""),
                });
              }}
              loading={postTaskComment.isPending}
              disabled={!taskChatDraft.trim()}
            >
              Отправить
            </Button>
          </Group>
        </Stack>
      </GlassModal>
      </Stack>
    </Box>
  );
}

function KanbanColumn({
  id,
  title,
  tasks,
  admins,
  isLast,
  onOpenDetail,
  onClaim,
  onTaskChat,
  patientIdToName,
  selectedTaskIds,
  onSelectTask,
  onMoveByKeyboard,
  wipLimit,
  overdueCount,
  agingCount,
}: {
  id: string;
  title: string;
  tasks: AdminTaskRow[];
  admins: AdminUserRow[];
  isLast: boolean;
  onOpenDetail: (taskId: string) => void;
  onClaim: (taskId: string) => void;
  onTaskChat?: (taskId: string) => void;
  patientIdToName: Map<string, string>;
  selectedTaskIds: string[];
  onSelectTask: (taskId: string, checked: boolean) => void;
  onMoveByKeyboard: (taskId: string, direction: -1 | 1) => void;
  wipLimit?: number;
  overdueCount: number;
  agingCount: number;
}) {
  const { isOver, setNodeRef } = useDroppable({ id });
  const overWip = typeof wipLimit === "number" && tasks.length > wipLimit;
  return (
    <Stack
      ref={setNodeRef}
      gap="xs"
      w={300}
      p="sm"
      style={{
        minHeight: 200,
        flexShrink: 0,
        borderRadius: "var(--mantine-radius-md)",
        borderRight: isLast ? undefined : "1px solid var(--mantine-color-gray-3)",
        outline: isOver ? `2px dashed ${overWip ? "var(--mantine-color-red-4)" : "var(--mantine-color-indigo-4)"}` : undefined,
        background: isOver ? (overWip ? "var(--mantine-color-red-0)" : "var(--mantine-color-indigo-0)") : "var(--mantine-color-gray-0)",
      }}
    >
      <Group justify="space-between">
        <Stack gap={2}>
          <Text size="sm" fw={600}>
            {title}
          </Text>
          <Group gap={4}>
            {typeof wipLimit === "number" ? (
              <Badge size="xs" variant="light" color={tasks.length > wipLimit ? "red" : "gray"}>
                WIP {tasks.length}/{wipLimit}
              </Badge>
            ) : null}
            <Badge size="xs" variant="light" color={overdueCount > 0 ? "red" : "gray"}>
              SLA overdue: {overdueCount}
            </Badge>
            <Badge size="xs" variant="light" color={agingCount > 0 ? "orange" : "gray"}>
              Aging 48h+: {agingCount}
            </Badge>
          </Group>
        </Stack>
        <Badge size="sm" variant="light" color={tasks.length > (wipLimit ?? Number.MAX_SAFE_INTEGER) ? "red" : "gray"}>
          {tasks.length}
        </Badge>
      </Group>
      <Stack gap="xs">
        {tasks.map((t) => (
          <TaskDropSlot
            key={t.id}
            statusId={id.replace("droppable-", "")}
            taskId={t.id}
          >
            <TaskKanbanCard
              task={t}
              admins={admins}
              patientName={t.patient_id ? patientIdToName.get(t.patient_id) ?? null : null}
              onOpenDetail={onOpenDetail}
              onClaim={(t.source === "ai_suggested" || t.source === "ai_auto") ? onClaim : undefined}
              onTaskChat={onTaskChat}
              isAi={t.source === "ai_suggested" || t.source === "ai_auto"}
              draggable
              blocked={Boolean(t.blocked)}
              selected={selectedTaskIds.includes(t.id)}
              onSelect={onSelectTask}
              onMoveByKeyboard={onMoveByKeyboard}
            />
          </TaskDropSlot>
        ))}
      </Stack>
    </Stack>
  );
}

function TaskDropSlot({
  statusId,
  taskId,
  children,
}: {
  statusId: string;
  taskId: string;
  children: ReactNode;
}) {
  const slotId = `task-slot-${statusId}--${taskId}`;
  const { setNodeRef, isOver } = useDroppable({ id: slotId });
  return (
    <Box
      ref={setNodeRef}
      style={{
        outline: isOver ? "1px dashed var(--mantine-color-indigo-4)" : undefined,
        borderRadius: "var(--radius-sm)",
      }}
    >
      {children}
    </Box>
  );
}

function StreamPageShell({
  pageTint,
  accentColor,
  children,
}: {
  pageTint: string;
  accentColor: TaskStreamMantineColor;
  children: ReactNode;
}) {
  return (
    <Box
      className="admin-tasks-context"
      data-page-tint={pageTint}
      style={{ borderRadius: "var(--radius-md)", overflow: "hidden" }}
    >
      <Box
        style={{
          height: 4,
          background: `var(--mantine-color-${accentColor}-6)`,
          opacity: 0.8,
        }}
      />
      <Box p="md" style={{ paddingTop: "var(--space-md)" }}>
        {children}
      </Box>
    </Box>
  );
}

function StreamHeaderDropZone({
  id,
  label,
  disabled,
  accentColor,
}: {
  id: string;
  label: string;
  disabled?: boolean;
  accentColor: TaskStreamMantineColor;
}) {
  const { setNodeRef, isOver } = useDroppable({ id, disabled: Boolean(disabled) });
  return (
    <Box ref={setNodeRef}>
      <Paper
        withBorder
        radius="md"
        p="xs"
        style={{
          borderColor: isOver ? `var(--mantine-color-${accentColor}-4)` : "var(--calendar-card-border)",
          background: isOver ? `var(--mantine-color-${accentColor}-0)` : "var(--mantine-color-body)",
        }}
      >
        <Group justify="space-between" wrap="wrap" gap="xs">
          <Text size="sm" fw={700}>
            {label}
          </Text>
          <Badge size="sm" variant="light" color={accentColor}>
            Поток
          </Badge>
        </Group>
        <Text size="xs" c="dimmed" mt={4}>
          Можно перетащить карточку задачи сюда, чтобы переместить её в этот поток.
        </Text>
      </Paper>
    </Box>
  );
}

function NavDropZone({ id, disabled }: { id: string; disabled?: boolean }) {
  const { setNodeRef } = useDroppable({ id, disabled: Boolean(disabled) });
  return (
    <Box
      ref={setNodeRef}
      aria-hidden
      style={{
        position: "absolute",
        top: 0,
        bottom: 0,
        width: 44,
        left: id === "nav-prev" ? 0 : undefined,
        right: id === "nav-next" ? 0 : undefined,
        opacity: 0,
        pointerEvents: disabled ? "none" : "auto",
        zIndex: 4,
      }}
    />
  );
}

function PagerDots({ count, activeIndex }: { count: number; activeIndex: number }) {
  return (
    <Group gap={6} wrap="nowrap" aria-label="Индикатор страниц">
      {Array.from({ length: count }, (_, i) => (
        <Box
          key={i}
          style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: i === activeIndex ? "var(--mantine-color-indigo-6)" : "var(--mantine-color-gray-4)",
            opacity: i === activeIndex ? 0.95 : 0.55,
          }}
        />
      ))}
    </Group>
  );
}

function TasksKanbanPage({
  streamId,
  streamName,
  streamTheme,
  allTasks,
  taskStreams,
  admins,
  patientIdToName,
  currentAdminId,
  myFocusTasks,
  selectedBoard,
  wipPolicies,
  canMoveTasksAcrossStreams,
  streamMoveOptions,
  selectedTaskIds,
  setSelectedTaskIds,
  onlyNeedsMyApproval,
  filterAssignee,
  filterPriority,
  filterDue,
  filterQuery,
  setOnlyNeedsMyApproval,
  setDetailTaskId,
  setTaskChatId,
  claimMutation,
  patchStreamTagsMutation,
  updateStatusMutation,
  reorderTasksMutation,
  setDragError,
  scheduleNavIntent,
  handleKeyboardColumnMove,
  activePageIndex,
  streamPagesLength,
}: {
  streamId: string | null;
  streamName: string;
  streamTheme?: Record<string, unknown>;
  allTasks: AdminTaskRow[];
  taskStreams: TaskStreamRow[];
  admins: AdminUserRow[];
  patientIdToName: Map<string, string>;
  currentAdminId: string | null;
  myFocusTasks: AdminTaskRow[];
  selectedBoard: { columns?: Array<{ mapped_status: string; sort_order: number; label: string | null }> } | undefined;
  wipPolicies: Record<string, number>;
  canMoveTasksAcrossStreams: boolean;
  streamMoveOptions: Array<{ value: string; label: string }>;
  selectedTaskIds: string[];
  setSelectedTaskIds: React.Dispatch<React.SetStateAction<string[]>>;
  onlyNeedsMyApproval: boolean;
  filterAssignee: string | null;
  filterPriority: string | null;
  filterDue: string;
  filterQuery: string;
  setOnlyNeedsMyApproval: (v: boolean) => void;
  setDetailTaskId: (id: string) => void;
  setTaskChatId: (id: string) => void;
  claimMutation: { mutate: (id: string) => void };
  patchStreamTagsMutation: { mutate: (args: { taskId: string; stream_id?: string; tag_ids?: string[] }) => void };
  updateStatusMutation: { mutate: (args: { taskId: string; status: string }) => void };
  reorderTasksMutation: {
    mutate: (
      args: { status: string; ordered_task_ids: string[] },
      opts?: { onError?: () => void; onSuccess?: () => void }
    ) => void;
  };
  setDragError: (msg: string | null) => void;
  scheduleNavIntent: (intent: "prev" | "next" | null) => void;
  handleKeyboardColumnMove: (taskId: string, direction: -1 | 1) => void;
  activePageIndex: number;
  streamPagesLength: number;
}) {
  const [optimisticOrderByStatus, setOptimisticOrderByStatus] = useState<Record<string, string[]>>({});
  void taskStreams;
  const pageTasks = useMemo(() => {
    if (!streamId) return allTasks;
    return allTasks.filter((t) => t.stream_id === streamId);
  }, [allTasks, streamId]);

  const statusColumns = useMemo(() => {
    if (selectedBoard?.columns?.length) {
      return selectedBoard.columns
        .slice()
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((c) => ({
          id: c.mapped_status,
          label:
            (c.label && c.label.trim()) ||
            STATUS_META[c.mapped_status] ||
            c.mapped_status.replace(/_/g, " "),
        }));
    }
    const discovered = Array.from(new Set(pageTasks.map((t) => t.status).filter(Boolean)));
    const ordered = STATUS_ORDER.filter((s) => discovered.includes(s));
    const extras = discovered
      .filter((s) => !STATUS_ORDER.includes(s as (typeof STATUS_ORDER)[number]))
      .sort();
    return [...ordered, ...extras].map((id) => ({
      id,
      label: STATUS_META[id] ?? id.replace(/_/g, " "),
    }));
  }, [pageTasks, selectedBoard]);

  const tasksByStatus = useCallback(
    (list: AdminTaskRow[]) => {
      const m: Record<string, AdminTaskRow[]> = {};
      statusColumns.forEach((c) => {
        m[c.id] = [];
      });
      list.forEach((t) => {
        const key = t.status || "open";
        if (!m[key]) m[key] = [];
        m[key].push(t);
      });
      Object.keys(m).forEach((status) => {
        m[status] = m[status].slice().sort((a, b) => {
          const ra = a.rank ?? Number.MAX_SAFE_INTEGER;
          const rb = b.rank ?? Number.MAX_SAFE_INTEGER;
          if (ra !== rb) return ra - rb;
          return (
            (a.due_at ? new Date(a.due_at).getTime() : Number.MAX_SAFE_INTEGER) -
            (b.due_at ? new Date(b.due_at).getTime() : Number.MAX_SAFE_INTEGER)
          );
        });
      });
      return m;
    },
    [statusColumns]
  );

  const needsApprovalTaskIds = useMemo(() => {
    return new Set(
      pageTasks
        .filter(
          (t) =>
            t.status === "review" ||
            (t.source?.startsWith("ai") && t.status !== "done" && t.status !== "cancelled")
        )
        .filter((t) => {
          if (!currentAdminId) return true;
          const assignees = taskAssigneeIdList(t);
          return assignees.length === 0 || assignees.includes(currentAdminId);
        })
        .map((t) => t.id)
    );
  }, [pageTasks, currentAdminId]);

  const approvalQueueTasks = useMemo(() => {
    return pageTasks
      .filter((t) => needsApprovalTaskIds.has(t.id))
      .slice()
      .sort((a, b) => {
        const ra = a.rank ?? Number.MAX_SAFE_INTEGER;
        const rb = b.rank ?? Number.MAX_SAFE_INTEGER;
        if (ra !== rb) return ra - rb;
        return (
          (a.due_at ? new Date(a.due_at).getTime() : Number.MAX_SAFE_INTEGER) -
          (b.due_at ? new Date(b.due_at).getTime() : Number.MAX_SAFE_INTEGER)
        );
      });
  }, [pageTasks, needsApprovalTaskIds]);

  const filteredTasks = useMemo(() => {
    return pageTasks.filter((t) => {
      if (onlyNeedsMyApproval && !needsApprovalTaskIds.has(t.id)) return false;
      const fq = String(filterQuery ?? "");
      if (fq.trim()) {
        const q = fq.trim().toLowerCase();
        const hay = `${t.title ?? ""} ${t.description ?? ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      if (filterAssignee) {
        const assignees = taskAssigneeIdList(t);
        if (!assignees.includes(filterAssignee)) return false;
      }
      if (filterPriority && t.priority !== filterPriority) return false;
      if (filterDue === "today") {
        if (!t.due_at || !dayjs(t.due_at).isSame(dayjs(), "day")) return false;
      }
      if (filterDue === "overdue") {
        if (!isDueOverdue(t.due_at)) return false;
      }
      return true;
    });
  }, [pageTasks, onlyNeedsMyApproval, needsApprovalTaskIds, filterQuery, filterAssignee, filterPriority, filterDue]);

  const columnMap = useMemo(() => tasksByStatus(filteredTasks), [tasksByStatus, filteredTasks]);
  const columnMapWithOptimistic = useMemo(() => {
    const next: Record<string, AdminTaskRow[]> = { ...columnMap };
    Object.entries(optimisticOrderByStatus).forEach(([status, orderedIds]) => {
      const cur = next[status];
      if (!cur || cur.length === 0) return;
      const byId = new Map(cur.map((t) => [t.id, t]));
      const ordered: AdminTaskRow[] = [];
      orderedIds.forEach((id) => {
        const row = byId.get(id);
        if (row) ordered.push(row);
      });
      cur.forEach((t) => {
        if (!orderedIds.includes(t.id)) ordered.push(t);
      });
      next[status] = ordered;
    });
    return next;
  }, [columnMap, optimisticOrderByStatus]);

  const canMoveToStatus = useCallback(
    (task: AdminTaskRow, toStatus: string): { ok: boolean; reason?: string } => {
      if (toStatus === task.status) return { ok: true };
      const wipLimit = wipPolicies[toStatus];
      if (typeof wipLimit === "number") {
        const currentCount = (columnMapWithOptimistic[toStatus] ?? []).length;
        if (currentCount >= wipLimit)
          return {
            ok: false,
            reason: `WIP-лимит колонки "${STATUS_META[toStatus] ?? toStatus}" исчерпан`,
          };
      }
      if (toStatus === "done") {
        if (!task.checklist_done)
          return { ok: false, reason: "Перед завершением отметьте checklist в карточке задачи" };
        if (task.blocked) return { ok: false, reason: "Нельзя завершить заблокированную задачу" };
      }
      return { ok: true };
    },
    [columnMapWithOptimistic, wipPolicies]
  );

  const moveTask = useCallback(
    (task: AdminTaskRow, toStatus: string) => {
      const decision = canMoveToStatus(task, toStatus);
      if (!decision.ok) {
        setDragError(decision.reason ?? "Переход запрещен");
        return;
      }
      setDragError(null);
      updateStatusMutation.mutate({ taskId: task.id, status: toStatus });
    },
    [canMoveToStatus, setDragError, updateStatusMutation]
  );

  const handleKanbanDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || typeof over.id !== "string") return;
      const overId = String(over.id);

      if (overId.startsWith("stream-page-")) {
        const taskId = String(active.id);
        const task = allTasks.find((t) => t.id === taskId);
        if (!task) return;
        if (!canMoveTasksAcrossStreams) return;
        const target = overId.replace("stream-page-", "");
        if (target === "all") return;
        if (target === task.stream_id) return;
        patchStreamTagsMutation.mutate({ taskId: task.id, stream_id: target });
        return;
      }

      const status = overId.startsWith("droppable-")
        ? overId.replace("droppable-", "")
        : overId.startsWith("task-slot-")
          ? overId.split("--")[0].replace("task-slot-", "")
          : "";
      if (!statusColumns.some((c) => c.id === status)) return;
      const taskId = String(active.id);
      const task = allTasks.find((t) => t.id === taskId);
      if (!task) return;

      const hasActiveFilters =
        onlyNeedsMyApproval || Boolean(filterAssignee) || Boolean(filterPriority) || filterDue !== "all";

      if (overId.startsWith("task-slot-")) {
        if (hasActiveFilters) {
          setDragError("Перестановка внутри колонки доступна только без активных фильтров.");
          return;
        }
        const targetTaskId = overId.split("--")[1];
        const current = columnMapWithOptimistic[status] ?? [];
        const without = current.filter((x) => x.id !== task.id);
        const targetIdx = without.findIndex((x) => x.id === targetTaskId);
        const insertAt = targetIdx >= 0 ? targetIdx : without.length;
        const next = [...without.slice(0, insertAt), { ...task, status }, ...without.slice(insertAt)];
        setOptimisticOrderByStatus((prev) => ({ ...prev, [status]: next.map((x) => x.id) }));
        reorderTasksMutation.mutate(
          {
            status,
            ordered_task_ids: next.map((item) => item.id),
          },
          {
            onError: () => {
              setOptimisticOrderByStatus((prev) => {
                const rest = { ...prev };
                delete rest[status];
                return rest;
              });
            },
            onSuccess: () => {
              setOptimisticOrderByStatus((prev) => {
                const rest = { ...prev };
                delete rest[status];
                return rest;
              });
            },
          }
        );
      }
      if (task.status !== status) moveTask(task, status);
    },
    [
      allTasks,
      canMoveTasksAcrossStreams,
      patchStreamTagsMutation,
      statusColumns,
      onlyNeedsMyApproval,
      filterAssignee,
      filterPriority,
      filterDue,
      columnMap,
      reorderTasksMutation,
      setDragError,
      moveTask,
    ]
  );

  const handleKanbanDragOver = useCallback(
    (event: DragOverEvent) => {
      if (!event.over || typeof event.over.id !== "string") {
        scheduleNavIntent(null);
        return;
      }
      const overId = String(event.over.id);
      if (overId === "nav-prev") scheduleNavIntent("prev");
      else if (overId === "nav-next") scheduleNavIntent("next");
      else scheduleNavIntent(null);
    },
    [scheduleNavIntent]
  );

  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 6 } }));

  const accentColor = streamMantineColorKey(streamTheme);
  const pageDroppableId = streamId ? `stream-page-${streamId}` : "stream-page-all";

  return (
    <Stack>
      {canMoveTasksAcrossStreams ? (
        <StreamHeaderDropZone
          id={pageDroppableId}
          label={streamName}
          accentColor={accentColor}
          disabled={streamId === null}
        />
      ) : (
        <Group justify="space-between" wrap="wrap">
          <Text size="sm" fw={700}>
            {streamName}
          </Text>
          {streamId ? (
            <Badge size="sm" variant="light" color={accentColor}>
              Поток
            </Badge>
          ) : null}
        </Group>
      )}

      <AdminDataTableSurface>
        <Group justify="space-between" mb="xs">
          <Text size="sm" fw={700}>
            Требуют подтверждения
          </Text>
          <Badge
            size="sm"
            variant="light"
            color={approvalQueueTasks.length > 0 ? SEMANTIC.opsSeverity.warning : "gray"}
          >
            {approvalQueueTasks.length}
          </Badge>
        </Group>
        {approvalQueueTasks.length === 0 ? (
          <Text size="xs" c="dimmed">
            Очередь подтверждений пуста.
          </Text>
        ) : (
          <Box style={{ overflowX: "auto" }}>
            <Group gap="xs" wrap="nowrap" align="stretch">
              {approvalQueueTasks.slice(0, 24).map((t) => (
                <Box key={t.id} w={300} style={{ flexShrink: 0 }}>
                  <TaskKanbanCard
                    task={t}
                    admins={admins}
                    patientName={t.patient_id ? patientIdToName.get(t.patient_id) ?? null : null}
                    onOpenDetail={setDetailTaskId}
                    onClaim={(t.source === "ai_suggested" || t.source === "ai_auto") ? (id) => claimMutation.mutate(id) : undefined}
                    onTaskChat={setTaskChatId}
                    isAi={t.source === "ai_suggested" || t.source === "ai_auto"}
                    draggable={false}
                    blocked={Boolean(t.blocked)}
                    selected={selectedTaskIds.includes(t.id)}
                    onSelect={(taskId, checked) =>
                      setSelectedTaskIds((prev) =>
                        checked ? Array.from(new Set([...prev, taskId])) : prev.filter((id) => id !== taskId)
                      )
                    }
                    onMoveByKeyboard={handleKeyboardColumnMove}
                    canMoveStream={canMoveTasksAcrossStreams}
                    streamOptions={streamMoveOptions.filter((x) => x.value !== t.stream_id)}
                    onMoveToStream={(taskId, nextStreamId) =>
                      patchStreamTagsMutation.mutate({ taskId, stream_id: nextStreamId })
                    }
                  />
                </Box>
              ))}
            </Group>
          </Box>
        )}
      </AdminDataTableSurface>

      <DndContext sensors={sensors} onDragEnd={handleKanbanDragEnd} onDragOver={handleKanbanDragOver}>
        <Box style={{ flex: 1, minWidth: 0, position: "relative" }}>
          {canMoveTasksAcrossStreams ? (
            <>
              <NavDropZone id="nav-prev" disabled={activePageIndex <= 0} />
              <NavDropZone id="nav-next" disabled={activePageIndex >= streamPagesLength - 1} />
              <Box
                aria-hidden
                style={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  bottom: 0,
                  width: 44,
                  background:
                    "linear-gradient(90deg, rgba(15,20,25,0.05) 0%, transparent 100%)",
                  opacity: 0.7,
                  pointerEvents: "none",
                }}
              />
              <Box
                aria-hidden
                style={{
                  position: "absolute",
                  right: 0,
                  top: 0,
                  bottom: 0,
                  width: 44,
                  background:
                    "linear-gradient(270deg, rgba(15,20,25,0.05) 0%, transparent 100%)",
                  opacity: 0.7,
                  pointerEvents: "none",
                }}
              />
            </>
          ) : null}

          <Box mb="md">
            <AdminDataTableSurface>
              <Group justify="space-between" align="center">
                <Text size="sm" fw={700}>
                  Список задач
                </Text>
                {currentAdminId ? (
                  <Text size="xs" c="dimmed">
                    Назначено мне: {myFocusTasks.filter((t) => t.status !== "done" && t.status !== "cancelled").length}
                  </Text>
                ) : null}
              </Group>
            </AdminDataTableSurface>
          </Box>

          {filteredTasks.length === 0 ? (
            <AdminDataTableSurface>
              <EmptyState
                title={onlyNeedsMyApproval ? "Нет задач в очереди подтверждений" : "Нет задач"}
                description={
                  onlyNeedsMyApproval
                    ? "В этом режиме список пуст. Переключитесь на «Все задачи» или ослабьте фильтры исполнителя, приоритета и срока."
                    : "Создайте первую задачу или примите задачу от AI в работу."
                }
                action={
                  onlyNeedsMyApproval
                    ? { label: "Показать все задачи", onClick: () => setOnlyNeedsMyApproval(false) }
                    : { label: "Создать задачу", onClick: () => {} }
                }
              />
            </AdminDataTableSurface>
          ) : (
            <Box style={{ overflowX: "auto" }}>
              <Box
                style={{
                  display: "grid",
                  gridAutoFlow: "column",
                  gridAutoColumns: "minmax(290px, 1fr)",
                  gap: "var(--space-md)",
                  alignItems: "start",
                  minWidth: "max-content",
                }}
              >
                {statusColumns.map((col, colIndex) => {
                  const droppableId = `droppable-${col.id}`;
                  const columnTasks = columnMapWithOptimistic[col.id] ?? [];
                  const wipLimit = wipPolicies[col.id] ?? KANBAN_WIP_LIMITS[col.id];
                  const overdueCount = columnTasks.filter((t) => isDueOverdue(t.due_at)).length;
                  const agingCount = columnTasks.filter((t) => {
                    if (!t.stage_entered_at) return false;
                    return dayjs().diff(dayjs(t.stage_entered_at), "hour") >= AGING_ALERT_HOURS;
                  }).length;
                  return (
                    <KanbanColumn
                      key={col.id}
                      id={droppableId}
                      title={col.label}
                      tasks={columnTasks}
                      admins={admins}
                      isLast={colIndex === statusColumns.length - 1}
                      onOpenDetail={setDetailTaskId}
                      onClaim={(id) => claimMutation.mutate(id)}
                      onTaskChat={setTaskChatId}
                      patientIdToName={patientIdToName}
                      selectedTaskIds={selectedTaskIds}
                      onSelectTask={(taskId, checked) =>
                        setSelectedTaskIds((prev) =>
                          checked ? Array.from(new Set([...prev, taskId])) : prev.filter((id) => id !== taskId)
                        )
                      }
                      onMoveByKeyboard={handleKeyboardColumnMove}
                      wipLimit={wipLimit}
                      overdueCount={overdueCount}
                      agingCount={agingCount}
                    />
                  );
                })}
              </Box>
            </Box>
          )}
        </Box>
      </DndContext>
    </Stack>
  );
}