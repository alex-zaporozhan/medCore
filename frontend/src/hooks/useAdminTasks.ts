import type { QueryKey } from "@tanstack/react-query";
import {
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

/** Задача админки (GET /v1/admin/tasks). */
export interface AdminTaskRow {
  id: string;
  clinic_id: string;
  stream_id: string;
  tag_ids?: string[];
  title: string;
  description: string | null;
  status: string;
  priority: string;
  creator_id?: string | null;
  assignee_id: string | null;
  /** Личные исполнители (junction); если пусто — смотрите assignee_id / role_assignee. */
  assignee_ids?: string[];
  role_assignee: string | null;
  due_at: string | null;
  source?: string;
  created_at?: string;
  booking_id?: string | null;
  patient_id?: string | null;
  lead_id?: string | null;
  attention_kind?: "follow_up" | "retention_gap" | "conflict" | null;
  attention_ref_id?: string | null;
  trace_id?: string | null;
  rank?: number;
  blocked?: boolean;
  blocked_reason?: string | null;
  checklist_done?: boolean;
  stage_entered_at?: string;
}

export interface TaskTransitionRow {
  id: string;
  task_id: string;
  from_status: string;
  to_status: string;
  reason: string | null;
  actor_admin_id: string | null;
  created_at: string;
  metadata?: Record<string, unknown>;
}

export interface TaskCalendarParticipantAckRow {
  admin_id: string;
  full_name: string | null;
  acknowledged_at: string | null;
}

export interface TaskCalendarEventContextRow {
  event_id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  participants: TaskCalendarParticipantAckRow[];
  acknowledged_count: number;
  participants_count: number;
}

/** Укороченная проекция для виджета (Omni Chat). */
export type AdminTaskOpenRow = Pick<
  AdminTaskRow,
  "id" | "title" | "status" | "priority" | "due_at"
>;

function fetchAdminTasks(params?: {
  source?: string;
  assignee_id?: string;
  status?: string;
  stream_id?: string;
  tag_ids?: string[];
  completed_from?: string;
  completed_to?: string;
}) {
  const search = new URLSearchParams();
  if (params?.source) search.set("source", params.source);
  if (params?.assignee_id) search.set("assignee_id", params.assignee_id);
  if (params?.status) search.set("status", params.status);
  if (params?.stream_id) search.set("stream_id", params.stream_id);
  if (params?.completed_from) search.set("completed_from", params.completed_from);
  if (params?.completed_to) search.set("completed_to", params.completed_to);
  for (const id of params?.tag_ids ?? []) {
    search.append("tag_ids", id);
  }
  const qs = search.toString();
  return api.get<AdminTaskRow[]>(`/v1/admin/tasks${qs ? `?${qs}` : ""}`);
}

export function useAdminTasksList(
  filters?: { streamId?: string | null; tagIds?: string[]; completedFrom?: string; completedTo?: string },
  options?: { enabled?: boolean }
) {
  const streamId = filters?.streamId ?? null;
  const tagIds = filters?.tagIds ?? [];
  return useQuery({
    queryKey: queryKeys.adminTasks.list(streamId, tagIds, filters?.completedFrom ?? null, filters?.completedTo ?? null),
    queryFn: () =>
      fetchAdminTasks({
        stream_id: streamId ?? undefined,
        tag_ids: tagIds.length ? tagIds : undefined,
        completed_from: filters?.completedFrom ?? undefined,
        completed_to: filters?.completedTo ?? undefined,
      }),
    enabled: options?.enabled !== false,
  });
}

export function useAdminTasksMyFocus(adminId: string | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.adminTasks.myFocus(adminId),
    queryFn: () => fetchAdminTasks({ assignee_id: adminId ?? undefined }),
    enabled: options?.enabled ?? !!adminId,
  });
}

export function useAdminTasksAi() {
  return useQuery({
    queryKey: queryKeys.adminTasks.ai(),
    queryFn: () => fetchAdminTasks({ source: "ai" }),
  });
}

export function useAdminTasksOpen(options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: queryKeys.adminTasks.open(),
    queryFn: () => fetchAdminTasks({ status: "open" }),
    select: (rows): AdminTaskOpenRow[] =>
      rows.map((t) => ({
        id: t.id,
        title: t.title,
        status: t.status,
        priority: t.priority,
        due_at: t.due_at,
      })),
    enabled: options?.enabled !== false,
  });
}

function invalidateAllAdminTaskLists(qc: ReturnType<typeof useQueryClient>) {
  qc.invalidateQueries({ queryKey: queryKeys.adminTasks.prefix });
}

export function useCreateAdminTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      title: string;
      description?: string | null;
      priority?: string;
      stream_id?: string | null;
      tag_ids?: string[];
      assignee_id?: string | null;
      assignee_ids?: string[];
      due_at: string | null;
      role_assignee?: string | null;
      booking_id?: string | null;
      patient_id?: string | null;
      lead_id?: string | null;
    }) => api.post<AdminTaskRow>("/v1/admin/tasks", payload),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

export function useClaimAdminTaskMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) =>
      api.post<AdminTaskRow>(`/v1/admin/tasks/${taskId}/claim`, {}),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

export function useUpdateAdminTaskStatusMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      status,
      transition_reason,
    }: {
      taskId: string;
      status: string;
      transition_reason?: string | null;
    }) => api.patch<AdminTaskRow>(`/v1/admin/tasks/${taskId}`, { status, transition_reason }),
    onMutate: async (variables) => {
      await qc.cancelQueries({ queryKey: queryKeys.adminTasks.prefix });
      const previous: [QueryKey, AdminTaskRow[] | undefined][] = qc.getQueriesData({
        queryKey: queryKeys.adminTasks.prefix,
      });
      qc.setQueriesData<AdminTaskRow[]>(
        { queryKey: queryKeys.adminTasks.prefix },
        (old) =>
          old?.map((t) =>
            t.id === variables.taskId ? { ...t, status: variables.status } : t
          ) ?? old
      );
      return { previous };
    },
    onError: (
      _err,
      _variables,
      context: { previous: [QueryKey, AdminTaskRow[] | undefined][] } | undefined
    ) => {
      if (context?.previous) {
        context.previous.forEach(([key, data]) => qc.setQueryData(key, data));
      }
    },
    onSettled: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

export function useUpdateAdminTaskMetaMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      taskId,
      rank,
      blocked,
      blocked_reason,
      checklist_done,
    }: {
      taskId: string;
      rank?: number;
      blocked?: boolean;
      blocked_reason?: string | null;
      checklist_done?: boolean;
    }) =>
      api.patch<AdminTaskRow>(`/v1/admin/tasks/${taskId}`, {
        rank,
        blocked,
        blocked_reason,
        checklist_done,
      }),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

/** PATCH assignee_ids (полная замена списка на бэкенде). */
export function usePatchAdminTaskAssigneesMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, assignee_ids }: { taskId: string; assignee_ids: string[] }) =>
      api.patch<AdminTaskRow>(`/v1/admin/tasks/${taskId}`, { assignee_ids }),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

/** PATCH due_at (ISO string or null). */
export function usePatchAdminTaskDueMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, due_at }: { taskId: string; due_at: string | null }) =>
      api.patch<AdminTaskRow>(`/v1/admin/tasks/${taskId}`, { due_at }),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

export function useReorderAdminTasksMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      status,
      ordered_task_ids,
    }: {
      status: string;
      ordered_task_ids: string[];
    }) => api.post<{ status: string; updated_ranks: Array<{ task_id: string; rank: number }> }>("/v1/admin/tasks/reorder", { status, ordered_task_ids }),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

export function useBulkUpdateAdminTaskStatusMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      task_ids,
      to_status,
      reason,
    }: {
      task_ids: string[];
      to_status: string;
      reason?: string | null;
    }) =>
      api.post<{ applied: string[]; rejected: Array<{ task_id: string; code: string; detail: string }> }>(
        "/v1/admin/tasks/bulk/status",
        { task_ids, to_status, reason }
      ),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}

export function useTaskTransitions(taskId: string | null) {
  return useQuery({
    queryKey: ["admin-tasks", "transitions", taskId] as const,
    queryFn: () => api.get<TaskTransitionRow[]>(`/v1/admin/tasks/${taskId}/transitions?limit=50`),
    enabled: !!taskId,
  });
}

export function useTaskWipPolicies() {
  return useQuery({
    queryKey: ["admin-tasks", "wip-policies"] as const,
    queryFn: () => api.get<Record<string, number>>("/v1/admin/tasks/wip-policies"),
  });
}

export function useTaskCalendarContext(taskId: string | null) {
  return useQuery({
    queryKey: ["admin-tasks", "calendar-context", taskId] as const,
    queryFn: () => api.get<TaskCalendarEventContextRow[]>(`/v1/admin/tasks/${taskId}/calendar-context`),
    enabled: !!taskId,
  });
}

export function useInviteTaskCalendarParticipants(taskId: string | null, eventId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (admin_ids: string[]) =>
      api.post<TaskCalendarEventContextRow>(`/v1/admin/tasks/${taskId}/calendar-events/${eventId}/invite`, {
        admin_ids,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-tasks", "calendar-context", taskId] as const });
    },
  });
}

/** Комментарий / чат по задаче (GET /v1/admin/tasks/{id}/comments). */
export interface TaskCommentRow {
  id: string;
  task_id: string;
  author_id: string;
  author_full_name: string | null;
  text: string;
  created_at: string;
}

export function useTaskComments(taskId: string | null) {
  return useQuery({
    queryKey: ["admin-tasks", "comments", taskId] as const,
    queryFn: () => api.get<TaskCommentRow[]>(`/v1/admin/tasks/${taskId}/comments`),
    enabled: !!taskId,
  });
}

export function usePostTaskComment(taskId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (text: string) =>
      api.post<TaskCommentRow>(`/v1/admin/tasks/${taskId}/comments`, { text }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["admin-tasks", "comments", taskId] as const });
    },
  });
}

/** GET /v1/admin/task-boards — раскладка Kanban (колонки = статусы). */
export interface TaskBoardColumnRow {
  id: string;
  sort_order: number;
  mapped_status: string;
  label: string | null;
}

export interface TaskBoardRow {
  id: string;
  clinic_id: string;
  name: string;
  kind: string;
  owner_admin_id: string | null;
  columns: TaskBoardColumnRow[];
}

export function useTaskBoardsQuery() {
  return useQuery({
    queryKey: queryKeys.adminTaskBoards.list(),
    queryFn: () => api.get<TaskBoardRow[]>("/v1/admin/task-boards"),
  });
}

export function useReplaceTaskBoardColumnsMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      boardId,
      columns,
    }: {
      boardId: string;
      columns: { mapped_status: string; label: string | null }[];
    }) =>
      api.put<TaskBoardRow>(`/v1/admin/task-boards/${boardId}/columns`, { columns }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminTaskBoards.list() });
    },
  });
}

export function useCreatePersonalTaskBoardMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api.post<TaskBoardRow>("/v1/admin/task-boards", { name }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminTaskBoards.list() });
    },
  });
}

export interface TaskStreamRow {
  id: string;
  clinic_id: string;
  name: string;
  slug: string;
  sort_order: number;
  is_archived: boolean;
  theme: Record<string, unknown>;
}

export type TaskStreamMantineColor =
  | "gray"
  | "red"
  | "pink"
  | "grape"
  | "violet"
  | "indigo"
  | "blue"
  | "cyan"
  | "teal"
  | "green"
  | "lime"
  | "yellow"
  | "orange";

export type TaskStreamPageTint =
  | "none"
  | "subtle_gray"
  | "subtle_violet"
  | "subtle_blue"
  | "subtle_green"
  | "subtle_amber";

export interface TaskStreamThemeDto {
  mantine_color?: TaskStreamMantineColor;
  page_tint?: TaskStreamPageTint;
}

export interface TaskTagRow {
  id: string;
  clinic_id: string;
  name: string;
  color: string | null;
}

export function useTaskStreamsQuery() {
  return useQuery({
    queryKey: queryKeys.adminTaskStreams.list(),
    queryFn: () => api.get<TaskStreamRow[]>("/v1/admin/task-streams"),
  });
}

export function useTaskTagsQuery() {
  return useQuery({
    queryKey: queryKeys.adminTaskTags.list(),
    queryFn: () => api.get<TaskTagRow[]>("/v1/admin/task-tags"),
  });
}

export function useCreateTaskStreamMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; slug?: string | null }) =>
      api.post<TaskStreamRow>("/v1/admin/task-streams", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminTaskStreams.list() });
    },
  });
}

export function usePatchTaskStreamMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { streamId: string; name?: string | null; theme?: TaskStreamThemeDto | null; is_archived?: boolean | null }) =>
      api.patch<TaskStreamRow>(`/v1/admin/task-streams/${args.streamId}`, {
        ...(args.name !== undefined ? { name: args.name } : {}),
        ...(args.theme !== undefined ? { theme: args.theme } : {}),
        ...(args.is_archived !== undefined ? { is_archived: args.is_archived } : {}),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminTaskStreams.list() });
    },
  });
}

export function useCreateTaskTagMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { name: string; color?: string | null }) =>
      api.post<TaskTagRow>("/v1/admin/task-tags", body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminTaskTags.list() });
    },
  });
}

export function usePatchAdminTaskStreamTagsMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { taskId: string; stream_id?: string; tag_ids?: string[] }) =>
      api.patch<AdminTaskRow>(`/v1/admin/tasks/${args.taskId}`, {
        ...(args.stream_id !== undefined ? { stream_id: args.stream_id } : {}),
        ...(args.tag_ids !== undefined ? { tag_ids: args.tag_ids } : {}),
      }),
    onSuccess: () => {
      invalidateAllAdminTaskLists(qc);
    },
  });
}
