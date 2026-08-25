import { useState, useMemo, useEffect, useRef, useCallback, type ReactNode } from "react";
import {
  ActionIcon,
  Avatar,
  Badge,
  Button,
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
  Divider,
  UnstyledButton,
} from "@mantine/core";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { TaskDetailsView } from "@/admin/components/TaskDetailsView";
import {
  IconGripVertical,
  IconRobot,
  IconDotsVertical,
  IconExternalLink,
  IconAlertTriangle,
  IconChevronUp,
  IconChevronDown,
  IconLayoutKanban,
  IconPlus,
  IconPalette,
  IconSettings,
  IconFilter,
  IconSearch,
  IconTrash,
} from "@tabler/icons-react";
import { Link, useSearchParams } from "react-router-dom";
import {
  GlassModal,
  AdminDataTableToolbar,
  AdminDataTableSurface,
  AppleEmojiOverlayTextarea,
  EmojiMartPopoverPicker,
  CompactMonthPicker,
} from "@/shared/ui";
import { ContextBar } from "@/shared/ui/ContextBar";
import { useTranslation } from "react-i18next";
import { SEMANTIC } from "@/shared/semanticUi";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { EmptyState } from "@/shared/ui/EmptyState";
import { taskKanbanQuietSurface } from "@/shared/taskStatusSemantic";
import { leadOutcomeLabel, taskStatusLabel } from "@/shared/taskStatusI18n";
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
  useReorderAdminTasksMutation,
  useTaskWipPolicies,
  useTaskComments,
  usePostTaskComment,
  useAdminSession,
  useTaskBoardsQuery,
  useReplaceTaskBoardColumnsMutation,
  useTaskStreamsQuery,
  useTaskTagsQuery,
  useCreateTaskStreamMutation,
  usePatchTaskStreamMutation,
  useCreateTaskTagMutation,
  usePatchAdminTaskStreamTagsMutation,
  useAdminLeadLogDetail,
  useAdminLeadLogRoutingRules,
  useSimulateAdminLeadLogRoutingMutation,
  useReplaceAdminLeadLogRoutingRulesMutation,
} from "@/hooks";
import type { AdminTaskRow, AdminUserRow, TaskStreamRow, TaskStreamMantineColor, TaskStreamPageTint } from "@/hooks";
import { ApiErrorWithCode, getAdminId } from "@/api/client";
import { displayPersonName } from "@/shared/ui/personNameFallback";
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

const STATUS_ORDER = ["open", "in_progress", "on_hold", "review", "done", "cancelled"] as const;

const LEAD_OUTCOME_COLOR: Record<"BOOKED" | "NOT_BOOKED" | "UNKNOWN", string> = {
  BOOKED: "teal",
  NOT_BOOKED: "orange",
  UNKNOWN: "gray",
};

function leadOutcomeKey(v: unknown): "BOOKED" | "NOT_BOOKED" | "UNKNOWN" {
  const s = String(v || "").toUpperCase();
  if (s === "BOOKED" || s === "NOT_BOOKED" || s === "UNKNOWN") return s;
  return "UNKNOWN";
}

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

type TaskKanbanCardProps = {
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
};

function TaskKanbanCard(props: TaskKanbanCardProps) {
  if (props.draggable) return <DraggableTaskKanbanCard {...props} />;
  return <TaskKanbanCardSurface {...props} />;
}

function DraggableTaskKanbanCard(props: TaskKanbanCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: props.task.id,
  });
  return (
    <TaskKanbanCardSurface
      {...props}
      drag={{ attributes, listeners, setNodeRef, transform, isDragging }}
    />
  );
}

function TaskKanbanCardSurface({
  task,
  admins,
  patientName,
  onOpenDetail,
  onClaim: _onClaim,
  onTaskChat: _onTaskChat,
  isAi,
  blocked,
  selected,
  onSelect,
  onMoveByKeyboard,
  canMoveStream,
  streamOptions,
  onMoveToStream,
  drag,
}: TaskKanbanCardProps & {
  drag?: {
    attributes: ReturnType<typeof useDraggable>["attributes"];
    listeners: ReturnType<typeof useDraggable>["listeners"];
    setNodeRef: ReturnType<typeof useDraggable>["setNodeRef"];
    transform: ReturnType<typeof useDraggable>["transform"];
    isDragging: boolean;
  };
}) {
  const overdue = isDueOverdue(task.due_at);
  const timeBomb = isTimeBomb(task.due_at);
  const assignee = firstAssigneeForAvatar(task, admins);
  const displayName = assignee?.full_name || assignee?.email || null;
  const { t } = useTranslation("tasks");
  const priorityKey =
    task.priority === "low" ||
    task.priority === "medium" ||
    task.priority === "high" ||
    task.priority === "urgent"
      ? task.priority
      : null;

  const outerStyle = drag
    ? {
        transform: drag.transform ? CSS.Translate.toString(drag.transform) : undefined,
        opacity: drag.isDragging ? 0.88 : 1,
      }
    : undefined;

  return (
    <Box ref={drag?.setNodeRef} style={outerStyle}>
      <Paper
        radius="md"
        p={0}
        withBorder={false}
        style={{
          ...taskKanbanQuietSurface(),
          cursor: "pointer",
          width: "100%",
          opacity: blocked ? 0.9 : 1,
          outline: selected ? "2px solid var(--mantine-color-indigo-5)" : undefined,
        }}
        onClick={() => onOpenDetail(task.id)}
        data-testid={`kanban-task-card-${task.id}`}
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
        <Group gap={0} wrap="nowrap" align="stretch">
          {drag ? (
            <Tooltip label={t("card.drag")} withArrow>
              <Box
                {...drag.listeners}
                {...drag.attributes}
                onClick={(e) => e.stopPropagation()}
                onDoubleClick={(e) => e.stopPropagation()}
                aria-label={t("card.dragTask")}
                style={{
                  width: 28,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "grab",
                  userSelect: "none",
                  borderTopLeftRadius: "var(--radius-md)",
                  borderBottomLeftRadius: "var(--radius-md)",
                  background: "var(--mantine-color-gray-1)",
                }}
              >
                <IconGripVertical size={16} color="var(--mantine-color-gray-6)" />
              </Box>
            </Tooltip>
          ) : null}

          <Box p="md" style={{ flex: 1, minWidth: 0 }}>
            <Group gap="xs" wrap="nowrap" align="flex-start">
              {onSelect ? (
                <Checkbox
                  mt={2}
                  checked={Boolean(selected)}
                  onChange={(e) => onSelect(task.id, e.currentTarget.checked)}
                  onClick={(e) => e.stopPropagation()}
                  aria-label={t("card.selectTask")}
                />
              ) : null}

              <Stack gap={6} style={{ flex: 1, minWidth: 0 }}>
                <Group gap={6} wrap="wrap" align="center">
                  <Text
                    size="xs"
                    c="dimmed"
                    style={{ minWidth: "3.5rem" }}
                  >
                    {priorityKey ? t(`priority.${priorityKey}`) : task.priority}
                  </Text>
                  <Box style={{ marginLeft: "auto" }}>
                    <Menu shadow="md" width={260} withinPortal>
                      <Menu.Target>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          size="sm"
                          onClick={(e) => e.stopPropagation()}
                          aria-label={t("card.actions")}
                        >
                          <IconDotsVertical size={16} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        <Menu.Item onClick={(e) => { e.stopPropagation(); onOpenDetail(task.id); }}>
                          {t("open")}
                        </Menu.Item>
                        <Menu.Item
                          component={Link}
                          to={`/admin/tasks/${task.id}`}
                          target="_blank"
                          onClick={(e) => e.stopPropagation()}
                          leftSection={<IconExternalLink size={14} />}
                        >
                          {t("openNewTab")}
                        </Menu.Item>
                        {canMoveStream && streamOptions && streamOptions.length > 0 && onMoveToStream ? (
                          <>
                            <Menu.Divider />
                            <Menu.Label>{t("card.moveToStream")}</Menu.Label>
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
                          </>
                        ) : null}
                      </Menu.Dropdown>
                    </Menu>
                  </Box>
                </Group>

                <Group gap={6} wrap="nowrap" align="flex-start">
                  {isAi ? (
                    <Tooltip label={t("card.ai")} withArrow>
                      <Box style={{ flexShrink: 0, marginTop: 2 }}>
                        <IconRobot size={16} color="var(--mantine-color-indigo-6)" />
                      </Box>
                    </Tooltip>
                  ) : null}
                  <UnstyledButton
                    type="button"
                    aria-label={t("card.openTask", { title: task.title })}
                    onClick={(e) => {
                      e.stopPropagation();
                      onOpenDetail(task.id);
                    }}
                    style={{ flex: 1, minWidth: 0, textAlign: "left" }}
                  >
                    <Text size="sm" fw={600} lineClamp={2} component="span">
                      {task.title}
                    </Text>
                  </UnstyledButton>
                </Group>

                {blocked ? (
                  <Tooltip
                    label={
                      task.blocked_reason?.trim()
                        ? t("card.blockedReason", { reason: task.blocked_reason })
                        : t("card.blockedReasonMissing")
                    }
                    withArrow
                    multiline
                    maw={300}
                  >
                    <Badge size="xs" variant="light" color="gray">
                      {t("card.blocked")}
                    </Badge>
                  </Tooltip>
                ) : null}

                {patientName ? (
                  <Text size="xs" lineClamp={1} c="dimmed">
                    {t("card.linkedPatient", { name: patientName })}
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
              </Stack>
            </Group>
          </Box>
        </Group>
      </Paper>
    </Box>
  );
}

export type AdminTasksPageMode = "tasks" | "leads-log";

export default function AdminTasksPage({
  mode = "tasks",
  forcedStreamSlug,
  titleOverride,
}: {
  mode?: AdminTasksPageMode;
  /** Lock page to a single stream (by slug), disabling stream pager selection. */
  forcedStreamSlug?: string;
  /** Override ContextBar title. */
  titleOverride?: string;
}) {
  const { t } = useTranslation("tasks");
  const { currentClinicId } = useAdminClinic();
  const [detailTaskId, setDetailTaskId] = useState<string | null>(null);
  const [taskChatId, setTaskChatId] = useState<string | null>(null);
  const [taskChatDraft, setTaskChatDraft] = useState("");
  const taskChatTextareaRef = useRef<HTMLTextAreaElement>(null);
  const { data: taskComments = [], isLoading: taskCommentsLoading } = useTaskComments(taskChatId);
  const postTaskComment = usePostTaskComment(taskChatId);
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
  const [completedDayIso, setCompletedDayIso] = useState(() => dayjs().format("YYYY-MM-DD"));
  const [auditTrail] = useState<
    Array<{ id: string; taskId: string; taskTitle: string; from: string; to: string; at: string }>
  >([]);
  const [dragError, setDragError] = useState<string | null>(null);
  const [bulkResultMessage, setBulkResultMessage] = useState<string | null>(null);
  const [selectedBoardId, setSelectedBoardId] = useState<string | null>(null);
  const [boardColumnModalOpened, setBoardColumnModalOpened] = useState(false);
  const [columnDraft, setColumnDraft] = useState<{ mapped_status: string; label: string | null; visible: boolean }[]>([]);
  const boardInitRef = useRef(false);
  const [hiddenStatuses, setHiddenStatuses] = useState<string[]>([]);
  const [boardPickerOpened, setBoardPickerOpened] = useState(false);
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


  const currentAdminId = getAdminId();
  const { data: adminSession } = useAdminSession();
  const canManageBoards = Boolean(adminSession?.permissions?.includes("manage_tasks"));
  const canLeadsLogManage = Boolean(adminSession?.permissions?.includes("leads.log.manage"));
  const { data: taskStreams = [], isLoading: streamsLoading } = useTaskStreamsQuery();
  const { data: taskTags = [], isLoading: tagsLoading } = useTaskTagsQuery();
  const {
    data: allTasks = [],
    isLoading: tasksLoading,
  } = useAdminTasksList(
    mode === "leads-log"
      ? {
          streamId: null,
          tagIds: filterTagIds,
          completedFrom: `${completedDayIso}T00:00:00Z`,
          completedTo: `${completedDayIso}T23:59:59Z`,
        }
      : { streamId: null, tagIds: filterTagIds },
    { enabled: streamFilterInitialized }
  );
  const taskChatTitle = useMemo(() => {
    if (!taskChatId) return "";
    return allTasks.find((t) => t.id === taskChatId)?.title ?? "";
  }, [taskChatId, allTasks]);
  const { data: myFocusTasks = [] } = useAdminTasksMyFocus(currentAdminId);
  const { data: admins = [] } = useAdminAdmins();
  const { data: patientsList = [] } = usePatients({ clinic_id: currentClinicId ?? undefined, limit: 500 });
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
  const leadLogIdFromTrace = useMemo(() => {
    if (mode !== "leads-log") return null;
    const raw = String(detailTask?.trace_id ?? "");
    const m = raw.match(/^omni_lead_log:([0-9a-fA-F-]{32,36})$/);
    return m?.[1] ?? null;
  }, [detailTask?.trace_id, mode]);
  const leadLogDetailQ = useAdminLeadLogDetail(mode === "leads-log" ? leadLogIdFromTrace : null);

  const routingRulesQ = useAdminLeadLogRoutingRules();
  const simulateRoutingMut = useSimulateAdminLeadLogRoutingMutation();
  const replaceRoutingRulesMut = useReplaceAdminLeadLogRoutingRulesMutation();
  const [routingModalOpened, setRoutingModalOpened] = useState(false);
  const [routingDraft, setRoutingDraft] = useState<
    Array<{
      key: string;
      channel_type: string;
      source_key: string;
      target_stream_id: string;
      is_active: boolean;
      sort_order: number;
    }>
  >([]);
  const [simulateChannelType, setSimulateChannelType] = useState("");
  const [simulateSourceKey, setSimulateSourceKey] = useState("");

  useEffect(() => {
    if (!routingModalOpened) return;
    const rows = (routingRulesQ.data ?? []).map((r) => ({
      key: r.id,
      channel_type: r.channel_type ?? "",
      source_key: r.source_key ?? "",
      target_stream_id: r.target_stream_id,
      is_active: Boolean(r.is_active),
      sort_order: Number(r.sort_order ?? 0),
    }));
    setRoutingDraft(rows);
  }, [routingModalOpened, routingRulesQ.data]);

  const createTaskMutation = useCreateAdminTaskMutation();
  const claimMutation = useClaimAdminTaskMutation();
  const claimTask = useCallback(
    (id: string) => {
      claimMutation.mutate(id, {
        onError: (e: unknown) => {
          setDragError(e instanceof ApiErrorWithCode ? e.message : t("errors.claimFailed"));
        },
      });
    },
    [claimMutation, t],
  );
  const updateStatusMutation = useUpdateAdminTaskStatusMutation();
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

  useEffect(() => {
    setSelectedTaskIds((prev) => prev.filter((id) => allTasks.some((t) => t.id === id)));
  }, [allTasks]);

  useEffect(() => {
    if (streamsLoading || streamFilterInitialized) return;
    if (forcedStreamSlug) {
      const forced = taskStreams.find((s) => s.slug === forcedStreamSlug && !s.is_archived);
      setSelectedStreamId(forced?.id ?? null);
      setStreamFilterInitialized(true);
      return;
    }
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
  }, [streamsLoading, taskStreams, searchParams, streamFilterInitialized, forcedStreamSlug]);

  useEffect(() => {
    if (!streamFilterInitialized) return;
    if (forcedStreamSlug) return;
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
  }, [selectedStreamId, streamFilterInitialized, searchParams, setSearchParams, forcedStreamSlug]);

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
    }> = [{ key: "all", label: t("streams.all"), streamId: null }];
    taskStreams.forEach((s) => {
      pages.push({ key: s.id, label: s.name, streamId: s.id, stream: s });
    });
    if (forcedStreamSlug) {
      const forced = taskStreams.find((s) => s.slug === forcedStreamSlug && !s.is_archived);
      if (!forced) return [];
      return [{ key: forced.id, label: forced.name, streamId: forced.id, stream: forced }];
    }
    return pages;
  }, [taskStreams, forcedStreamSlug, t]);

  const activePageIndex = useMemo(() => {
    if (!selectedStreamId) return 0;
    const i = streamPages.findIndex((p) => p.streamId === selectedStreamId);
    return i >= 0 ? i : 0;
  }, [selectedStreamId, streamPages]);
  const activePage = streamPages[activePageIndex];

  const navHoverTimerRef = useRef<number | null>(null);
  const navIntentRef = useRef<"prev" | "next" | null>(null);
  const streamPagesRef = useRef(streamPages);
  streamPagesRef.current = streamPages;
  const applyNavIntent = useCallback((intent: "prev" | "next") => {
    setSelectedStreamId((current) => {
      const pages = streamPagesRef.current;
      const idx = current == null ? 0 : pages.findIndex((p) => p.streamId === current);
      const base = idx >= 0 ? idx : 0;
      const nextIdx = intent === "prev" ? base - 1 : base + 1;
      if (nextIdx < 0 || nextIdx >= pages.length) return current;
      return pages[nextIdx]?.streamId ?? null;
    });
  }, []);
  const scheduleNavIntent = useCallback(
    (intent: "prev" | "next" | null) => {
      navIntentRef.current = intent;
      if (navHoverTimerRef.current) {
        window.clearTimeout(navHoverTimerRef.current);
        navHoverTimerRef.current = null;
      }
      if (!intent) return;
      navHoverTimerRef.current = window.setTimeout(() => {
        applyNavIntent(intent);
      }, 420);
    },
    [applyNavIntent]
  );

  useEffect(() => {
    return () => {
      if (navHoverTimerRef.current) window.clearTimeout(navHoverTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!createOpened) return;
    const def =
      selectedStreamId ??
      taskStreams.find((s) => s.slug === "general")?.id ??
      taskStreams[0]?.id ??
      null;
    if (def) setCreateStreamId(def);
  }, [createOpened, selectedStreamId, taskStreams]);

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

  useEffect(() => {
    if (!selectedBoardId || typeof localStorage === "undefined") {
      setHiddenStatuses([]);
      return;
    }
    try {
      const raw = localStorage.getItem(`adminKanbanHiddenColumns:${selectedBoardId}`);
      const parsed = raw ? (JSON.parse(raw) as unknown) : [];
      const list = Array.isArray(parsed) ? parsed.filter((x): x is string => typeof x === "string") : [];
      setHiddenStatuses(list);
    } catch {
      setHiddenStatuses([]);
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
        onError: (e: unknown) => {
          setDragError(e instanceof ApiErrorWithCode ? e.message : t("errors.createFailed"));
        },
      }
    );
  };

  const adminOptions = admins.map((a) => ({
    value: a.id,
    label: displayPersonName(a.full_name?.trim() || a.email, a.id),
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
        <ContextBar title={titleOverride ?? (mode === "leads-log" ? t("leadsTitle") : t("title"))} />
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
        title={titleOverride ?? (mode === "leads-log" ? t("leadsTitle") : t("title"))}
        actions={
          mode === "leads-log" ? null : (
            <Button size="sm" onClick={() => setCreateOpened(true)}>
              {t("newTask")}
            </Button>
          )
        }
      />

      <Box style={{ position: "sticky", top: 0, zIndex: "var(--z-sticky)", background: "var(--bg-main)" }}>
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
                }}
                disabled={forcedStreamSlug ? true : activePageIndex <= 0}
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
                }}
                disabled={forcedStreamSlug ? true : activePageIndex >= streamPages.length - 1}
              >
                {">"}
              </Button>
            </Button.Group>

            <PagerDots count={streamPages.length} activeIndex={activePageIndex} />

            {forcedStreamSlug ? null : (
              <Menu shadow="md" width={280} withinPortal>
                <Menu.Target>
                  <Button size="xs" variant="light" data-testid="stream-switcher">
                    {activeStream?.name ?? t("streams.all")}
                  </Button>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>{t("streams.label")}</Menu.Label>
                  {streamPages.map((p) => (
                    <Menu.Item
                      key={p.key}
                      onClick={() => {
                        setSelectedStreamId(p.streamId);
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
                        {t("streams.new")}
                      </Menu.Item>
                    </>
                  ) : null}
                </Menu.Dropdown>
              </Menu>
            )}

            {activeStream && canManageBoards ? (
              <ActionIcon
                variant="light"
                color="indigo"
                aria-label={t("streams.color")}
                onClick={() => setStreamThemeModalOpened(true)}
              >
                <IconPalette size={16} />
              </ActionIcon>
            ) : null}

            {mode === "leads-log" && canLeadsLogManage ? (
              <Tooltip label={t("routing.tooltip")} withArrow>
                <ActionIcon
                  variant="light"
                  color="indigo"
                  aria-label={t("routing.tooltip")}
                  onClick={() => setRoutingModalOpened(true)}
                >
                  <IconSettings size={16} />
                </ActionIcon>
              </Tooltip>
            ) : null}

            <TextInput
              size="xs"
              placeholder={t("search")}
              leftSection={<IconSearch size={14} />}
              value={filterQuery}
              onChange={(e) => setFilterQuery(e.currentTarget.value)}
              w={220}
            />

            {mode === "leads-log" ? (
              <TextInput
                size="xs"
                type="date"
                label={t("filtersBar.day")}
                value={completedDayIso}
                onChange={(e) => setCompletedDayIso(e.currentTarget.value)}
              />
            ) : null}

            <Select
              size="xs"
              placeholder={t("filtersBar.assignee")}
              data={adminOptions}
              value={filterAssignee}
              onChange={setFilterAssignee}
              clearable
              w={190}
            />

            <Select
              size="xs"
              placeholder={t("filtersBar.due")}
              data={[
                { value: "all", label: t("filtersBar.dueAll") },
                { value: "today", label: t("filtersBar.dueToday") },
                { value: "overdue", label: t("filtersBar.dueOverdue") },
              ]}
              value={filterDue}
              onChange={(v) => setFilterDue(v ?? "all")}
              w={150}
            />

            <Menu shadow="md" width={320} withinPortal>
              <Menu.Target>
                <Button size="xs" variant="default" leftSection={<IconFilter size={14} />}>
                  {t("filters")}
                </Button>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Label>{t("filters")}</Menu.Label>
                {mode !== "leads-log" ? (
                  <>
                    <Menu.Item onClick={() => setOnlyNeedsMyApproval((v) => !v)}>
                      {onlyNeedsMyApproval ? t("filtersBar.showAll") : t("filtersBar.needsApproval", { count: activeNeedsApprovalCount })}
                    </Menu.Item>
                    <Menu.Divider />
                  </>
                ) : null}
                <Box p="xs">
                  <Group gap="xs" wrap="wrap">
                    <Select
                      size="xs"
                      placeholder={t("priority.label")}
                      data={[
                        { value: "low", label: t("priority.low") },
                        { value: "medium", label: t("priority.medium") },
                        { value: "high", label: t("priority.high") },
                        { value: "urgent", label: t("priority.urgent") },
                      ]}
                      value={filterPriority}
                      onChange={setFilterPriority}
                      clearable
                      w={160}
                    />
                    <MultiSelect
                      size="xs"
                      placeholder={t("filtersBar.tags")}
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
            {canManageBoards ? (
              <Menu shadow="md" width={320} withinPortal>
                <Menu.Target>
                  <ActionIcon variant="light" color="gray" aria-label={t("settings")}>
                    <IconSettings size={16} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  <Menu.Label>{t("settings")}</Menu.Label>
                  <Menu.Item
                    leftSection={<IconLayoutKanban size={14} />}
                    onClick={() => {
                      if (!selectedBoard) return;
                      const sorted = [...selectedBoard.columns].sort((a, b) => a.sort_order - b.sort_order);
                      setColumnDraft(
                        sorted.map((c) => ({
                          mapped_status: c.mapped_status,
                          label: c.label,
                          visible: !hiddenStatuses.includes(c.mapped_status),
                        }))
                      );
                      setBoardColumnModalOpened(true);
                    }}
                    disabled={!canEditSelectedBoardColumns}
                  >
                    {t("board.columns")}
                  </Menu.Item>
                  <Menu.Item
                    leftSection={<IconLayoutKanban size={14} />}
                    onClick={() => setBoardPickerOpened(true)}
                  >
                    {t("board.kanbanBoards")}
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            ) : null}
          </Group>
        </Group>
      </AdminDataTableToolbar>
      </Box>

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
              {t("filtersBar.approvalFilterHint")}
            </Text>
            <Button size="xs" variant="light" onClick={() => setOnlyNeedsMyApproval(false)}>
              {t("filtersBar.showAll")}
            </Button>
          </Group>
        </Alert>
      ) : null}

      {activePage ? (
      <Box data-testid="stream-pager" style={{ width: "100%", paddingBottom: "var(--space-sm)" }}>
        <div
          key={activePage.key}
          data-stream-page-index={activePageIndex}
          data-stream-id={activePage.streamId ?? "all"}
        >
          <StreamPageShell
            pageTint={streamPageTintKey(activePage.stream?.theme)}
            accentColor={streamMantineColorKey(activePage.stream?.theme)}
          >
            <TasksKanbanPage
              streamId={activePage.streamId}
              streamName={activePage.streamId ? activePage.label : t("streams.all")}
              streamTheme={activePage.stream?.theme}
              allTasks={allTasks}
              taskStreams={taskStreams}
              admins={admins}
              patientIdToName={patientIdToName}
              currentAdminId={currentAdminId}
              myFocusTasks={myFocusTasks}
              selectedBoard={selectedBoard}
              wipPolicies={wipPolicies}
              hiddenStatuses={hiddenStatuses}
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
              setCreateOpened={setCreateOpened}
              setDetailTaskId={setDetailTaskId}
              setTaskChatId={setTaskChatId}
              claimMutation={{ mutate: claimTask }}
              patchStreamTagsMutation={patchStreamTagsMutation}
              updateStatusMutation={updateStatusMutation}
              reorderTasksMutation={reorderTasksMutation}
              setDragError={setDragError}
              scheduleNavIntent={scheduleNavIntent}
              applyNavIntent={applyNavIntent}
              handleKeyboardColumnMove={handleKeyboardColumnMove}
              activePageIndex={activePageIndex}
              streamPagesLength={streamPages.length}
            />
          </StreamPageShell>
        </div>
      </Box>
      ) : null}

      <AdminDataTableSurface>
        <Text size="sm" fw={700} mb={6}>
          {t("audit.title")}
        </Text>
        {auditTrail.length === 0 ? (
          <Text size="xs" c="dimmed">
            {t("audit.empty")}
          </Text>
        ) : (
          <Stack gap={4}>
            {auditTrail.slice(0, 8).map((a) => (
              <Text key={a.id} size="xs" c="dimmed">
                {dayjs(a.at).format("DD.MM HH:mm")} · {a.taskTitle} · {taskStatusLabel(a.from)} →{" "}
                {taskStatusLabel(a.to)}
              </Text>
            ))}
          </Stack>
        )}
      </AdminDataTableSurface>

      <GlassModal
        size="calc(100vw - 48px)"
        centered
        styles={{
          content: {
            height: "calc(100vh - 48px)",
            maxHeight: "calc(100vh - 48px)",
            borderRadius: "var(--radius-lg)",
          },
          body: { maxHeight: "calc(100vh - 140px)", overflowY: "auto" },
        }}
        opened={!!detailTaskId}
        onClose={() => {
          setDetailTaskId(null);
        }}
        title={
          mode === "leads-log"
            ? (leadLogDetailQ.data?.title ?? detailTask?.title ?? t("detail.leadLog"))
            : (detailTask ? detailTask.title : t("detail.task"))
        }
      >
        {detailTaskId ? (
          mode === "leads-log" ? (
            <Stack gap="sm">
              {leadLogIdFromTrace ? (
                <>
                  <Text size="sm" fw={600}>
                    {t("detail.dialogLog")}
                  </Text>
                  {leadLogDetailQ.isLoading ? (
                    <Group gap="xs">
                      <Loader size="sm" />
                      <Text size="sm" c="dimmed">
                        {t("loading")}
                      </Text>
                    </Group>
                  ) : leadLogDetailQ.data ? (
                    <Stack gap="sm">
                      <Group justify="space-between" align="flex-start" wrap="wrap" gap="xs">
                        <Stack gap={2} style={{ minWidth: 0 }}>
                          <Text fw={700} size="sm" truncate="end">
                            {leadLogDetailQ.data.contact_name ?? t("unknownName")}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {leadLogDetailQ.data.contact_primary_phone ?? ""}
                            {leadLogDetailQ.data.opened_by_admin_name ? t("detail.operator", { name: leadLogDetailQ.data.opened_by_admin_name }) : ""}
                          </Text>
                          <Text size="xs" c="dimmed">
                            {t("detail.closed", { date: dayjs(leadLogDetailQ.data.closed_at).format("DD.MM.YYYY HH:mm") })}
                          </Text>
                        </Stack>
                        <Group gap="xs" wrap="wrap">
                          <Badge
                            variant="light"
                            color={LEAD_OUTCOME_COLOR[leadOutcomeKey(leadLogDetailQ.data.outcome)]}
                          >
                            {leadOutcomeLabel(leadOutcomeKey(leadLogDetailQ.data.outcome))}
                          </Badge>
                          {leadLogDetailQ.data.omni_chat_id ? (
                            <Button
                              component={Link}
                              to={`/admin/omni-chat?chat_id=${encodeURIComponent(String(leadLogDetailQ.data.omni_chat_id))}`}
                              size="xs"
                              variant="default"
                              target="_blank"
                            >
                              {t("detail.openSourceChat")}
                            </Button>
                          ) : null}
                        </Group>
                      </Group>

                      <Divider />

                      {Array.isArray((leadLogDetailQ.data.transcript_json as any)?.messages) ? (
                        <Stack gap="xs">
                          {(leadLogDetailQ.data.transcript_json as any).messages.slice(-200).map((m: any) => {
                            const actor = String(m?.actor_type ?? "UNKNOWN").toUpperCase();
                            const dir = String(m?.direction ?? "").toUpperCase();
                            const ts = m?.created_at ? dayjs(String(m.created_at)) : null;
                            const body = String(m?.content ?? "").trim();
                            const tone =
                              actor === "ADMIN" || dir === "OUTBOUND"
                                ? { bg: "var(--mantine-color-indigo-0)", border: "var(--mantine-color-indigo-2)" }
                                : { bg: "white", border: "var(--mantine-color-gray-2)" };
                            return (
                              <Paper
                                key={String(m?.id ?? `${actor}-${m?.created_at ?? ""}-${Math.random()}`)}
                                withBorder
                                radius="md"
                                p="sm"
                                style={{ background: tone.bg, borderColor: tone.border }}
                              >
                                <Group justify="space-between" wrap="nowrap" gap="xs">
                                  <Text size="xs" fw={600} c="dimmed">
                                    {actor}
                                  </Text>
                                  <Text size="xs" c="dimmed">
                                    {ts?.isValid() ? ts.format("HH:mm") : ""}
                                  </Text>
                                </Group>
                                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                                  {body || "—"}
                                </Text>
                              </Paper>
                            );
                          })}
                        </Stack>
                      ) : (
                        <Paper withBorder p="md" radius="md" style={{ whiteSpace: "pre-wrap" }}>
                          <Text size="sm">
                            {leadLogDetailQ.data.transcript_text?.trim()
                              ? leadLogDetailQ.data.transcript_text
                              : t("detail.noText")}
                          </Text>
                        </Paper>
                      )}
                    </Stack>
                  ) : (
                    <Alert color="red" variant="light">
                      {t("detail.loadFailed")}
                    </Alert>
                  )}
                </>
              ) : (
                <Alert color="orange" variant="light">
                  {t("detail.noTrace")}
                </Alert>
              )}
            </Stack>
          ) : (
            <TaskDetailsView taskId={detailTaskId} mode="modal" onClose={() => setDetailTaskId(null)} />
          )
        ) : null}
      </GlassModal>

      <GlassModal
        size="xl"
        centered
        opened={createOpened}
        onClose={() => setCreateOpened(false)}
        title={t("newTask")}
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
            <Alert color="orange" title={t("createForm.dueInPastTitle")}>
              {t("createForm.dueInPastBody")}
            </Alert>
          ) : null}

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="lg">
            <Stack gap="sm">
              <TextInput
                label={t("createForm.taskTitle")}
                placeholder={t("createForm.taskTitlePlaceholder")}
                value={title}
                onChange={(e) => setTitle(e.currentTarget.value)}
                required
              />
              <Textarea
                label={t("createForm.description")}
                placeholder={t("createForm.descriptionPlaceholder")}
                minRows={8}
                value={description}
                onChange={(e) => setDescription(e.currentTarget.value)}
              />
              <MultiSelect
                label={t("createForm.assignees")}
                placeholder={t("createForm.assigneesPlaceholder")}
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
                label={t("priority.label")}
                data={[
                  { value: "low", label: t("priority.low") },
                  { value: "medium", label: t("priority.medium") },
                  { value: "high", label: t("priority.high") },
                  { value: "urgent", label: t("priority.urgent") },
                ]}
                value={priority}
                onChange={setPriority}
              />
              <Select
                label={t("streams.one")}
                placeholder={t("view.pickStream")}
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
                  label={t("filtersBar.tags")}
                  placeholder={t("createForm.optional")}
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
                    {t("createForm.tag")}
                  </Button>
                ) : null}
              </Group>

              <Stack gap={6}>
                <Text size="sm" fw={700}>
                  {t("createForm.due")}
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
                    label={t("view.time")}
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
              {t("cancel")}
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
              {t("create")}
            </Button>
          </Group>
        </Box>
      </GlassModal>

      <GlassModal
        size="sm"
        centered
        opened={newStreamModalOpened}
        onClose={() => setNewStreamModalOpened(false)}
        title={t("streams.new")}
      >
        <Stack gap="sm">
          <TextInput
            label={t("streams.name")}
            placeholder={t("streams.namePlaceholder")}
            value={newStreamName}
            onChange={(e) => setNewStreamName(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setNewStreamModalOpened(false)}>
              {t("cancel")}
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
              {t("create")}
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="sm"
        centered
        opened={streamThemeModalOpened}
        onClose={() => setStreamThemeModalOpened(false)}
        title={activeStream ? t("streams.colorNamed", { name: activeStream.name }) : t("streams.color")}
      >
        <Stack gap="sm">
          <Select
            label={t("streams.tint")}
            description={t("streams.tintHint")}
            data={[
              { value: "none", label: t("streams.tintNone") },
              { value: "subtle_gray", label: t("streams.tintGray") },
              { value: "subtle_violet", label: t("streams.tintViolet") },
              { value: "subtle_blue", label: t("streams.tintBlue") },
              { value: "subtle_green", label: t("streams.tintGreen") },
              { value: "subtle_amber", label: t("streams.tintAmber") },
            ]}
            value={themeDraftTint}
            onChange={(v) => setThemeDraftTint((v as TaskStreamPageTint) ?? "none")}
          />
          <Select
            label={t("streams.accent")}
            description={t("streams.accentHint")}
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
              {t("cancel")}
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
              {t("save")}
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="lg"
        centered
        opened={routingModalOpened}
        onClose={() => setRoutingModalOpened(false)}
        title={t("routing.title")}
      >
        <Stack gap="sm">
          <Alert icon={<IconFilter size={16} />} color="blue" variant="light">
            {t("routing.intro")}
          </Alert>

          <Paper withBorder radius="md" p="sm">
            <Stack gap="xs">
              <Group justify="space-between" align="flex-end" wrap="wrap">
                <Group gap="xs" wrap="wrap" align="flex-end">
                  <TextInput
                    label={t("routing.testChannel")}
                    placeholder="TELEGRAM_BOT / WHATSAPP / EMAIL"
                    value={simulateChannelType}
                    onChange={(e) => setSimulateChannelType(e.currentTarget.value)}
                    w={240}
                  />
                  <TextInput
                    label={t("routing.testSource")}
                    placeholder={t("routing.optional")}
                    value={simulateSourceKey}
                    onChange={(e) => setSimulateSourceKey(e.currentTarget.value)}
                    w={200}
                  />
                </Group>
                <Button
                  size="xs"
                  variant="default"
                  loading={simulateRoutingMut.isPending}
                  onClick={() => {
                    simulateRoutingMut.mutate({
                      channel_type: simulateChannelType.trim() ? simulateChannelType.trim() : null,
                      source_key: simulateSourceKey.trim() ? simulateSourceKey.trim() : null,
                    });
                  }}
                >
                  {t("routing.check")}
                </Button>
              </Group>

              {simulateRoutingMut.data ? (
                <Alert color="gray" variant="light">
                  {(() => {
                    const sid = simulateRoutingMut.data.target_stream_id;
                    if (!sid) return t("routing.noMatch");
                    const label =
                      streamPages.find((p) => p.streamId === sid)?.label ??
                      taskStreams.find((s) => s.id === sid)?.name ??
                      sid;
                    return t("routing.targetHit", { name: label });
                  })()}
                </Alert>
              ) : null}
            </Stack>
          </Paper>

          <Group justify="space-between">
            <Button
              size="xs"
              variant="light"
              leftSection={<IconPlus size={14} />}
              onClick={() => {
                const fallbackStreamId = activeStream?.id ?? streamPages[0]?.streamId ?? "";
                setRoutingDraft((prev) => [
                  ...prev,
                  {
                    key: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
                    channel_type: "",
                    source_key: "",
                    target_stream_id: fallbackStreamId,
                    is_active: true,
                    sort_order: prev.length,
                  },
                ]);
              }}
            >
              {t("routing.addRule")}
            </Button>

            <Button
              size="xs"
              loading={replaceRoutingRulesMut.isPending}
              disabled={!canLeadsLogManage}
              onClick={() => {
                const payload = routingDraft.map((r) => ({
                  channel_type: r.channel_type.trim() ? r.channel_type.trim() : null,
                  source_key: r.source_key.trim() ? r.source_key.trim() : null,
                  target_stream_id: r.target_stream_id,
                  is_active: Boolean(r.is_active),
                  sort_order: Number(r.sort_order ?? 0),
                }));
                replaceRoutingRulesMut.mutate(payload, {
                  onSuccess: () => setRoutingModalOpened(false),
                });
              }}
            >
              {t("save")}
            </Button>
          </Group>

          <Divider />

          <ScrollArea h={360} type="auto">
            <Stack gap="xs" pr="xs">
              {routingDraft.length === 0 ? (
                <EmptyState
                  title={t("routing.emptyTitle")}
                  description={t("routing.emptyHint")}
                />
              ) : null}

              {routingDraft.map((r, idx) => (
                <Paper key={r.key} withBorder radius="md" p="sm">
                  <Group gap="xs" align="flex-end" wrap="wrap">
                    <TextInput
                      label={t("routing.fieldChannel")}
                      placeholder="TELEGRAM_BOT / WHATSAPP / EMAIL"
                      value={r.channel_type}
                      onChange={(e) => {
                        const v = e.currentTarget.value;
                        setRoutingDraft((prev) =>
                          prev.map((x) => (x.key === r.key ? { ...x, channel_type: v } : x))
                        );
                      }}
                      w={220}
                    />
                    <TextInput
                      label={t("routing.fieldSource")}
                      placeholder={t("routing.optional")}
                      value={r.source_key}
                      onChange={(e) => {
                        const v = e.currentTarget.value;
                        setRoutingDraft((prev) =>
                          prev.map((x) => (x.key === r.key ? { ...x, source_key: v } : x))
                        );
                      }}
                      w={180}
                    />
                    <Select
                      label={t("routing.fieldTarget")}
                      data={streamPages
                        .filter((p) => typeof p.streamId === "string" && p.streamId)
                        .map((p) => ({ value: p.streamId as string, label: p.label }))}
                      value={r.target_stream_id}
                      onChange={(v) => {
                        const next = v ?? "";
                        setRoutingDraft((prev) =>
                          prev.map((x) => (x.key === r.key ? { ...x, target_stream_id: next } : x))
                        );
                      }}
                      w={260}
                      searchable
                    />
                    <TextInput
                      label={t("routing.fieldSort")}
                      value={String(r.sort_order)}
                      onChange={(e) => {
                        const n = Number(e.currentTarget.value);
                        setRoutingDraft((prev) =>
                          prev.map((x) =>
                            x.key === r.key ? { ...x, sort_order: Number.isFinite(n) ? n : 0 } : x
                          )
                        );
                      }}
                      w={80}
                    />
                    <Checkbox
                      label={t("routing.fieldActive")}
                      checked={r.is_active}
                      onChange={(e) => {
                        const checked = e.currentTarget.checked;
                        setRoutingDraft((prev) =>
                          prev.map((x) => (x.key === r.key ? { ...x, is_active: checked } : x))
                        );
                      }}
                      mt={22}
                    />
                    <ActionIcon
                      variant="subtle"
                      color="red"
                      aria-label={t("routing.deleteRule")}
                      onClick={() => setRoutingDraft((prev) => prev.filter((x) => x.key !== r.key))}
                      mt={22}
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
                    <Text size="xs" c="dimmed" mt={24}>
                      #{idx + 1}
                    </Text>
                  </Group>
                </Paper>
              ))}
            </Stack>
          </ScrollArea>
        </Stack>
      </GlassModal>

      <GlassModal
        size="sm"
        centered
        opened={newTagModalOpened}
        onClose={() => setNewTagModalOpened(false)}
        title={t("tagModal.title")}
      >
        <Stack gap="sm">
          <TextInput
            label={t("tagModal.name")}
            placeholder={t("tagModal.placeholder")}
            value={newTagName}
            onChange={(e) => setNewTagName(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setNewTagModalOpened(false)}>
              {t("cancel")}
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
              {t("create")}
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="md"
        centered
        opened={boardColumnModalOpened}
        onClose={() => setBoardColumnModalOpened(false)}
        title={t("board.columnOrderTitle")}
      >
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            {t("board.columnOrderHint")}
          </Text>
          {columnDraft.map((col, i) => (
            <Group key={`${col.mapped_status}-${i}`} justify="space-between" wrap="nowrap" align="flex-start">
              <Text size="xs" w={130} ff="monospace">
                {col.mapped_status}
              </Text>
              <Checkbox
                size="xs"
                mt={6}
                checked={col.visible}
                onChange={(e) => {
                  const checked = e.currentTarget.checked;
                  setColumnDraft((prev) =>
                    prev.map((c, idx) => (idx === i ? { ...c, visible: checked } : c))
                  );
                }}
                aria-label={t("board.showColumn")}
              />
              <TextInput
                size="xs"
                placeholder={taskStatusLabel(col.mapped_status)}
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
                aria-label={t("board.moveUp")}
                onClick={() => moveColumnDraft(i, -1)}
                disabled={i === 0}
              >
                <IconChevronUp size={16} />
              </ActionIcon>
              <ActionIcon
                size="sm"
                variant="light"
                aria-label={t("board.moveDown")}
                onClick={() => moveColumnDraft(i, 1)}
                disabled={i === columnDraft.length - 1}
              >
                <IconChevronDown size={16} />
              </ActionIcon>
            </Group>
          ))}
          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={() => setBoardColumnModalOpened(false)}>
              {t("cancel")}
            </Button>
            <Button
              loading={replaceBoardColumnsMutation.isPending}
              onClick={() => {
                if (!selectedBoardId) return;
                const hidden = columnDraft.filter((c) => !c.visible).map((c) => c.mapped_status);
                if (typeof localStorage !== "undefined") {
                  localStorage.setItem(`adminKanbanHiddenColumns:${selectedBoardId}`, JSON.stringify(hidden));
                }
                setHiddenStatuses(hidden);
                replaceBoardColumnsMutation.mutate(
                  {
                    boardId: selectedBoardId,
                    columns: columnDraft.map((c) => ({ mapped_status: c.mapped_status, label: c.label })),
                  },
                  { onSuccess: () => setBoardColumnModalOpened(false) }
                );
              }}
            >
              {t("save")}
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        size="md"
        centered
        opened={boardPickerOpened}
        onClose={() => setBoardPickerOpened(false)}
        title={t("board.kanbanBoards")}
      >
        <Stack gap="sm">
          <Text size="xs" c="dimmed">
            {t("board.pickBoardHint")}
          </Text>
          <Select
            label={t("board.pickBoard")}
            placeholder={t("board.pickBoardPlaceholder")}
            data={taskBoards.map((b) => ({
              value: b.id,
              label: `${b.name}${b.kind === "clinic_wide" ? t("board.kindClinic") : b.kind === "personal" ? t("board.kindPersonal") : ""}`,
            }))}
            value={selectedBoardId}
            onChange={(v) => setSelectedBoardId(v ?? null)}
            searchable
          />
          <Group justify="flex-end" mt="sm">
            <Button variant="default" onClick={() => setBoardPickerOpened(false)}>
              {t("close")}
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
        title={taskChatTitle ? t("chat.titleNamed", { name: taskChatTitle }) : t("chat.title")}
      >
        <Stack gap="sm" style={{ minHeight: 280 }}>
          {taskCommentsLoading ? (
            <Loader size="sm" />
          ) : (
            <ScrollArea h={320} offsetScrollbars>
              <Stack gap="xs">
                {taskComments.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    {t("chat.empty")}
                  </Text>
                ) : (
                  taskComments.map((c) => (
                    <Paper key={c.id} p="xs" withBorder>
                      <Text size="xs" c="dimmed" mb={4}>
                        {c.author_full_name || t("employee")} ·{" "}
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
              {t("chat.openStaffThread")}
            </Button>
          ) : null}
          <Input.Wrapper label={t("chat.message")}>
            <AppleEmojiOverlayTextarea
              ref={taskChatTextareaRef}
              placeholder={t("chat.placeholder")}
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
              {t("send")}
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
  canMoveStream,
  streamMoveOptions,
  onMoveToStream,
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
  canMoveStream?: boolean;
  streamMoveOptions?: Array<{ value: string; label: string }>;
  onMoveToStream?: (taskId: string, streamId: string) => void;
}) {
  const { t } = useTranslation("tasks");
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
          <Group gap={4} wrap="wrap">
            {typeof wipLimit === "number" ? (
              <Badge size="xs" variant="light" color={tasks.length > wipLimit ? "red" : "gray"}>
                {t("wip.limit", { current: tasks.length, max: wipLimit })}
              </Badge>
            ) : null}
            {overdueCount > 0 ? (
              <Badge size="xs" variant="light" color="red">
                {t("wip.slaOverdue", { count: overdueCount })}
              </Badge>
            ) : null}
            {agingCount > 0 ? (
              <Badge size="xs" variant="light" color="orange">
                {t("wip.aging", { count: agingCount })}
              </Badge>
            ) : null}
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
              canMoveStream={canMoveStream}
              streamOptions={streamMoveOptions?.filter((x) => x.value !== t.stream_id)}
              onMoveToStream={onMoveToStream}
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
  accentColor: _accentColor,
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
          height: 1,
          background: "var(--calendar-card-border)",
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
  const { t } = useTranslation("tasks");
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
            {t("streams.one")}
          </Badge>
        </Group>
        <Text size="xs" c="dimmed" mt={4}>
          {t("streams.dropHint")}
        </Text>
      </Paper>
    </Box>
  );
}

function NavDropZone({
  id,
  disabled,
  armed,
}: {
  id: string;
  disabled?: boolean;
  armed?: boolean;
}) {
  const blocked = Boolean(disabled) || !armed;
  const { setNodeRef } = useDroppable({ id, disabled: blocked });
  return (
    <div
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
        pointerEvents: blocked ? "none" : "auto",
        zIndex: "var(--z-page-overlay)",
      }}
    />
  );
}

function PagerDots({ count, activeIndex }: { count: number; activeIndex: number }) {
  const { t } = useTranslation("tasks");
  return (
    <Group gap={6} wrap="nowrap" aria-label={t("board.pageDots")}>
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
  hiddenStatuses,
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
  setCreateOpened,
  setDetailTaskId,
  setTaskChatId,
  claimMutation,
  patchStreamTagsMutation,
  updateStatusMutation,
  reorderTasksMutation,
  setDragError,
  scheduleNavIntent,
  applyNavIntent,
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
  hiddenStatuses: string[];
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
  setCreateOpened: (v: boolean) => void;
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
  applyNavIntent: (intent: "prev" | "next") => void;
  handleKeyboardColumnMove: (taskId: string, direction: -1 | 1) => void;
  activePageIndex: number;
  streamPagesLength: number;
}) {
  const { t, i18n } = useTranslation("tasks");
  const [optimisticOrderByStatus, setOptimisticOrderByStatus] = useState<Record<string, string[]>>({});
  void taskStreams;
  const pageTasks = useMemo(() => {
    if (!streamId) return allTasks;
    return allTasks.filter((t) => t.stream_id === streamId);
  }, [allTasks, streamId]);

  const statusColumns = useMemo(() => {
    const hidden = new Set(hiddenStatuses);
    if (selectedBoard?.columns?.length) {
      return selectedBoard.columns
        .slice()
        .sort((a, b) => a.sort_order - b.sort_order)
        .map((c) => ({
          id: c.mapped_status,
          label:
            (c.label && c.label.trim()) ||
            taskStatusLabel(c.mapped_status) ||
            c.mapped_status.replace(/_/g, " "),
        }))
        .filter((c) => !hidden.has(c.id));
    }
    const discovered = Array.from(new Set(pageTasks.map((t) => t.status).filter(Boolean)));
    const ordered = STATUS_ORDER.filter((s) => discovered.includes(s));
    const extras = discovered
      .filter((s) => !STATUS_ORDER.includes(s as (typeof STATUS_ORDER)[number]))
      .sort();
    return [...ordered, ...extras]
      .map((id) => ({
        id,
        label: taskStatusLabel(id) || id.replace(/_/g, " "),
      }))
      .filter((c) => !hidden.has(c.id));
  }, [pageTasks, selectedBoard, hiddenStatuses, i18n.language]);

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
            reason: i18n.t("errors.wipExhausted", { ns: "tasks", column: taskStatusLabel(toStatus) }),
          };
      }
      if (toStatus === "done") {
        if (!task.checklist_done)
          return { ok: false, reason: i18n.t("errors.needChecklist", { ns: "tasks" }) };
        if (task.blocked) return { ok: false, reason: i18n.t("errors.blockedDone", { ns: "tasks" }) };
      }
      return { ok: true };
    },
    [columnMapWithOptimistic, wipPolicies]
  );

  const moveTask = useCallback(
    (task: AdminTaskRow, toStatus: string) => {
      const decision = canMoveToStatus(task, toStatus);
      if (!decision.ok) {
        setDragError(decision.reason ?? i18n.t("errors.transitionDenied", { ns: "tasks" }));
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

      if (overId === "nav-prev" || overId === "nav-next") {
        applyNavIntent(overId === "nav-prev" ? "prev" : "next");
        return;
      }

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
          setDragError(t("errors.reorderNeedsClearFilters"));
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
      applyNavIntent,
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
  const [navDropArmed, setNavDropArmed] = useState(false);

  const accentColor = streamMantineColorKey(streamTheme);
  const pageDroppableId = streamId ? `stream-page-${streamId}` : "stream-page-all";

  return (
    <DndContext
      sensors={sensors}
      onDragStart={() => setNavDropArmed(true)}
      onDragEnd={(event) => {
        setNavDropArmed(false);
        const overId = event.over ? String(event.over.id) : "";
        scheduleNavIntent(null);
        if (overId === "nav-prev") applyNavIntent("prev");
        else if (overId === "nav-next") applyNavIntent("next");
        handleKanbanDragEnd(event);
      }}
      onDragCancel={() => {
        setNavDropArmed(false);
        scheduleNavIntent(null);
      }}
      onDragOver={handleKanbanDragOver}
    >
    <Stack>
      {canMoveTasksAcrossStreams && streamId !== null ? (
        <StreamHeaderDropZone
          id={pageDroppableId}
          label={streamName}
          accentColor={accentColor}
          disabled={false}
        />
      ) : (
        <Group justify="space-between" wrap="wrap">
          <Text size="sm" fw={700}>
            {streamName}
          </Text>
          {streamId ? (
            <Badge size="sm" variant="light" color={accentColor}>
              {t("streams.one")}
            </Badge>
          ) : null}
        </Group>
      )}

      {approvalQueueTasks.length > 0 ? (
      <AdminDataTableSurface>
        <Group justify="space-between" mb="xs">
          <Text size="sm" fw={700}>
            {t("queue.title")}
          </Text>
          <Badge
            size="sm"
            variant="light"
            color={SEMANTIC.opsSeverity.warning}
          >
            {approvalQueueTasks.length}
          </Badge>
        </Group>
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
      </AdminDataTableSurface>
      ) : null}

        <Box style={{ flex: 1, minWidth: 0, position: "relative" }}>
          {canMoveTasksAcrossStreams ? (
            <>
              <NavDropZone id="nav-prev" disabled={activePageIndex <= 0} armed={navDropArmed} />
              <NavDropZone id="nav-next" disabled={activePageIndex >= streamPagesLength - 1} armed={navDropArmed} />
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
                  {t("list.boardTitle")}
                </Text>
                {currentAdminId ? (
                  <Text size="xs" c="dimmed">
                    {t("list.assignedToMe", {
                      count: myFocusTasks.filter((row) => row.status !== "done" && row.status !== "cancelled").length,
                    })}
                  </Text>
                ) : null}
              </Group>
            </AdminDataTableSurface>
          </Box>

          {filteredTasks.length === 0 ? (
            <AdminDataTableSurface>
              <EmptyState
                title={onlyNeedsMyApproval ? t("empty.approvalNone") : t("empty.none")}
                description={
                  onlyNeedsMyApproval
                    ? t("empty.approvalHint")
                    : t("empty.noneHint")
                }
                action={
                  onlyNeedsMyApproval
                    ? { label: t("empty.showAll"), onClick: () => setOnlyNeedsMyApproval(false) }
                    : { label: t("empty.create"), onClick: () => setCreateOpened(true) }
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
                      canMoveStream={canMoveTasksAcrossStreams}
                      streamMoveOptions={streamMoveOptions}
                      onMoveToStream={(taskId, nextStreamId) =>
                        patchStreamTagsMutation.mutate({ taskId, stream_id: nextStreamId })
                      }
                    />
                  );
                })}
              </Box>
            </Box>
          )}
        </Box>
    </Stack>
    </DndContext>
  );
}