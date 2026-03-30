import { useState, useMemo, useEffect, useRef, type ReactNode } from "react";
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
} from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import {
  GlassModal,
  AdminDataTableToolbar,
  AdminDataTableSurface,
  AppleEmojiOverlayTextarea,
  EmojiMartPopoverPicker,
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
  useBulkUpdateAdminTaskStatusMutation,
  useTaskWipPolicies,
  useTaskTransitions,
  useTaskCalendarContext,
  useInviteTaskCalendarParticipants,
  useTaskComments,
  usePostTaskComment,
} from "@/hooks";
import type { AdminTaskRow, AdminUserRow } from "@/hooks";
import { getAdminId } from "@/api/client";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
  type DragEndEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";

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

/** Имена личных исполнителей: assignee_ids или legacy assignee_id. */
function taskAssigneeIdList(task: AdminTaskRow): string[] {
  if (task.assignee_ids && task.assignee_ids.length > 0) return task.assignee_ids;
  if (task.assignee_id) return [task.assignee_id];
  return [];
}

function formatTaskAssigneeLine(task: AdminTaskRow, admins: AdminUserRow[]): string {
  const ids = taskAssigneeIdList(task);
  if (ids.length === 0) return "";
  return ids
    .map((id) => {
      const a = admins.find((x) => x.id === id);
      return a?.full_name || a?.email || id.slice(0, 8);
    })
    .join(", ");
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
  const [dueDate, setDueDate] = useState("");
  const [selectedTaskIds, setSelectedTaskIds] = useState<string[]>([]);
  const [filterAssignee, setFilterAssignee] = useState<string | null>(null);
  const [filterPriority, setFilterPriority] = useState<string | null>(null);
  const [filterDue, setFilterDue] = useState<string>("all");
  const [onlyNeedsMyApproval, setOnlyNeedsMyApproval] = useState(false);
  const [bulkStatus, setBulkStatus] = useState<string | null>(null);
  const [blockedReasonDraft, setBlockedReasonDraft] = useState("");
  const [auditTrail, setAuditTrail] = useState<
    Array<{ id: string; taskId: string; taskTitle: string; from: string; to: string; at: string }>
  >([]);
  const [dragError, setDragError] = useState<string | null>(null);
  const [bulkResultMessage, setBulkResultMessage] = useState<string | null>(null);

  const currentAdminId = getAdminId();
  const { data: tasks = [], isLoading } = useAdminTasksList();
  const taskChatTitle = useMemo(() => {
    if (!taskChatId) return "";
    return tasks.find((t) => t.id === taskChatId)?.title ?? "";
  }, [taskChatId, tasks]);
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
    () => (detailTaskId ? tasks.find((t) => t.id === detailTaskId) : undefined),
    [detailTaskId, tasks]
  );

  const createTaskMutation = useCreateAdminTaskMutation();
  const claimMutation = useClaimAdminTaskMutation();
  const updateStatusMutation = useUpdateAdminTaskStatusMutation();
  const updateTaskMetaMutation = useUpdateAdminTaskMetaMutation();
  const reorderTasksMutation = useReorderAdminTasksMutation();
  const bulkUpdateMutation = useBulkUpdateAdminTaskStatusMutation();
  const { data: wipPolicies = KANBAN_WIP_LIMITS } = useTaskWipPolicies();
  const { data: detailTransitions = [] } = useTaskTransitions(detailTaskId);
  const { data: taskCalendarContext = [] } = useTaskCalendarContext(detailTaskId);
  const [inviteEventId, setInviteEventId] = useState<string | null>(null);
  const [inviteAdminIds, setInviteAdminIds] = useState<string[]>([]);
  const inviteParticipantsMutation = useInviteTaskCalendarParticipants(detailTaskId, inviteEventId);

  useEffect(() => {
    setSelectedTaskIds((prev) => prev.filter((id) => tasks.some((t) => t.id === id)));
  }, [tasks]);

  useEffect(() => {
    if (!detailTask) {
      setBlockedReasonDraft("");
      return;
    }
    setBlockedReasonDraft(detailTask.blocked_reason ?? "");
  }, [detailTask?.id, detailTask?.blocked_reason]);

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

  const handleCreate = () => {
    if (!title.trim()) return;
    if (assigneeIds.length === 0 || !dueDate) return;
    createTaskMutation.mutate(
      {
        title: title.trim(),
        description: description.trim() || null,
        priority: priority ?? "medium",
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
          setDueDate("");
        },
      }
    );
  };

  const adminOptions = admins.map((a) => ({
    value: a.id,
    label: a.full_name || a.email || a.id.slice(0, 8),
  }));

  const statusColumns = useMemo(() => {
    const discovered = Array.from(new Set(tasks.map((t) => t.status).filter(Boolean)));
    const ordered = STATUS_ORDER.filter((s) => discovered.includes(s));
    const extras = discovered.filter((s) => !STATUS_ORDER.includes(s as (typeof STATUS_ORDER)[number])).sort();
    return [...ordered, ...extras].map((id) => ({
      id,
      label: STATUS_META[id] ?? id.replace(/_/g, " "),
    }));
  }, [tasks]);

  const needsApprovalTaskIds = useMemo(() => {
    return new Set(
      tasks
        .filter((t) => t.status === "review" || (t.source?.startsWith("ai") && t.status !== "done" && t.status !== "cancelled"))
        .filter((t) => {
          if (!currentAdminId) return true;
          const assignees = taskAssigneeIdList(t);
          return assignees.length === 0 || assignees.includes(currentAdminId);
        })
        .map((t) => t.id)
    );
  }, [tasks, currentAdminId]);

  const approvalQueueTasks = useMemo(() => {
    return tasks
      .filter((t) => needsApprovalTaskIds.has(t.id))
      .slice()
      .sort((a, b) => {
        const ra = a.rank ?? Number.MAX_SAFE_INTEGER;
        const rb = b.rank ?? Number.MAX_SAFE_INTEGER;
        if (ra !== rb) return ra - rb;
        return (a.due_at ? new Date(a.due_at).getTime() : Number.MAX_SAFE_INTEGER) - (b.due_at ? new Date(b.due_at).getTime() : Number.MAX_SAFE_INTEGER);
      });
  }, [tasks, needsApprovalTaskIds]);

  const filteredTasks = useMemo(() => {
    return tasks.filter((t) => {
      if (onlyNeedsMyApproval && !needsApprovalTaskIds.has(t.id)) return false;
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
  }, [tasks, onlyNeedsMyApproval, needsApprovalTaskIds, filterAssignee, filterPriority, filterDue]);

  const tasksByStatus = (list: AdminTaskRow[]) => {
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
        return (a.due_at ? new Date(a.due_at).getTime() : Number.MAX_SAFE_INTEGER) - (b.due_at ? new Date(b.due_at).getTime() : Number.MAX_SAFE_INTEGER);
      });
    });
    return m;
  };

  const columnMap = tasksByStatus(filteredTasks);

  const canMoveToStatus = (task: AdminTaskRow, toStatus: string): { ok: boolean; reason?: string } => {
    if (toStatus === task.status) return { ok: true };
    const wipLimit = wipPolicies[toStatus];
    if (typeof wipLimit === "number") {
      const currentCount = (columnMap[toStatus] ?? []).length;
      if (currentCount >= wipLimit) return { ok: false, reason: `WIP-лимит колонки "${STATUS_META[toStatus] ?? toStatus}" исчерпан` };
    }
    if (toStatus === "done") {
      if (!task.checklist_done) return { ok: false, reason: "Перед завершением отметьте checklist в карточке задачи" };
      if (task.blocked) return { ok: false, reason: "Нельзя завершить заблокированную задачу" };
    }
    return { ok: true };
  };

  const moveTask = (task: AdminTaskRow, toStatus: string) => {
    const decision = canMoveToStatus(task, toStatus);
    if (!decision.ok) {
      setDragError(decision.reason ?? "Переход запрещен");
      return;
    }
    setDragError(null);
    updateStatusMutation.mutate({ taskId: task.id, status: toStatus });
    setAuditTrail((prev) => [
      {
        id: `${Date.now()}-${task.id}`,
        taskId: task.id,
        taskTitle: task.title,
        from: task.status,
        to: toStatus,
        at: new Date().toISOString(),
      },
      ...prev,
    ].slice(0, 40));
  };

  const handleKanbanDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || typeof over.id !== "string") return;
    const overId = String(over.id);
    const status = overId.startsWith("droppable-")
      ? overId.replace("droppable-", "")
      : overId.startsWith("task-slot-")
        ? overId.split("--")[0].replace("task-slot-", "")
        : "";
    if (!statusColumns.some((c) => c.id === status)) return;
    const taskId = String(active.id);
    const task = tasks.find((t) => t.id === taskId);
    if (!task) return;
    const hasActiveFilters =
      onlyNeedsMyApproval || Boolean(filterAssignee) || Boolean(filterPriority) || filterDue !== "all";
    if (overId.startsWith("task-slot-")) {
      if (hasActiveFilters) {
        setDragError("Перестановка внутри колонки доступна только без активных фильтров.");
        return;
      }
      const targetTaskId = overId.split("--")[1];
      const current = columnMap[status] ?? [];
      const without = current.filter((x) => x.id !== task.id);
      const targetIdx = without.findIndex((x) => x.id === targetTaskId);
      const insertAt = targetIdx >= 0 ? targetIdx : without.length;
      const next = [...without.slice(0, insertAt), { ...task, status }, ...without.slice(insertAt)];
      reorderTasksMutation.mutate({
        status,
        ordered_task_ids: next.map((item) => item.id),
      });
    }
    if (task.status !== status) moveTask(task, status);
  };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  const handleKeyboardColumnMove = (taskId: string, direction: -1 | 1) => {
    const task = tasks.find((t) => t.id === taskId);
    if (!task) return;
    const idx = statusColumns.findIndex((s) => s.id === task.status);
    if (idx < 0) return;
    const target = statusColumns[idx + direction];
    if (!target) return;
    moveTask(task, target.id);
  };

  const applyBulkStatus = () => {
    if (!bulkStatus) return;
    setBulkResultMessage(null);
    bulkUpdateMutation.mutate(
      {
        task_ids: selectedTaskIds,
        to_status: bulkStatus,
      },
      {
        onSuccess: (result) => {
          const appliedCount = result.applied.length;
          const rejectedCount = result.rejected.length;
          if (rejectedCount > 0) {
            const firstReason = result.rejected[0]?.detail;
            setBulkResultMessage(
              `Массовая операция завершена частично: успешно ${appliedCount}, отклонено ${rejectedCount}${
                firstReason ? ` (пример: ${firstReason})` : ""
              }`
            );
          } else {
            setBulkResultMessage(`Массовая операция выполнена: обновлено ${appliedCount}.`);
          }
          if (appliedCount > 0) {
            setSelectedTaskIds([]);
            setBulkStatus(null);
          }
        },
      }
    );
  };

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Задачи" />
        <PageSkeleton variant="cards" rows={6} />
      </Stack>
    );
  }

  return (
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
        <Group gap="xs" wrap="wrap" justify="space-between">
          <Group gap="xs" wrap="wrap">
            <Button
              size="xs"
              variant={onlyNeedsMyApproval ? "filled" : "light"}
              onClick={() => setOnlyNeedsMyApproval((v) => !v)}
            >
              Ждут моего подтверждения ({needsApprovalTaskIds.size})
            </Button>
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
          </Group>
          <Group gap="xs" wrap="wrap">
            <Select
              size="xs"
              placeholder="Массово: статус"
              data={statusColumns.map((c) => ({ value: c.id, label: c.label }))}
              value={bulkStatus}
              onChange={setBulkStatus}
              w={180}
            />
            <Button
              size="xs"
              variant="light"
              onClick={applyBulkStatus}
              disabled={!bulkStatus || selectedTaskIds.length === 0}
            >
              Применить ({selectedTaskIds.length})
            </Button>
          </Group>
        </Group>
      </AdminDataTableToolbar>

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
                  />
                </Box>
              ))}
            </Group>
          </Box>
        )}
      </AdminDataTableSurface>

      <DndContext sensors={sensors} onDragEnd={handleKanbanDragEnd}>
          <Box style={{ flex: 1, minWidth: 0 }}>
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
                  title="Нет задач"
                  description="Создайте первую задачу или примите задачу от AI в работу."
                  action={{ label: "Создать задачу", onClick: () => setCreateOpened(true) }}
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
                  const columnTasks = columnMap[col.id] ?? [];
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
        }}
        title={detailTask ? detailTask.title : "Задача"}
      >
        {detailTask ? (
          <Stack gap="md">
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
                Срок: {detailTask.due_at ? dayjs(detailTask.due_at).format("DD.MM.YYYY HH:mm") : "—"} · Исполнители:{" "}
                {formatTaskAssigneeLine(detailTask, admins) || detailTask.role_assignee || "—"}
              </Text>
            </Box>
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
        size="md"
        centered
        opened={createOpened}
        onClose={() => setCreateOpened(false)}
        title="Новая задача"
      >
        <Stack>
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
            minRows={3}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
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
          <MultiSelect
            label="Исполнители"
            placeholder="Выберите одного или нескольких"
            data={adminOptions}
            value={assigneeIds}
            onChange={setAssigneeIds}
            required
            searchable
            hidePickedOptions
          />
          <TextInput
            label="Срок"
            type="datetime-local"
            value={dueDate}
            onChange={(e) => setDueDate(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button
              onClick={handleCreate}
              loading={createTaskMutation.isPending}
              disabled={!title.trim() || assigneeIds.length === 0 || !dueDate}
            >
              Создать
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