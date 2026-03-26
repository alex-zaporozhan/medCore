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
  title: string;
  description: string | null;
  status: string;
  priority: string;
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

function fetchAdminTasks(params?: { source?: string; assignee_id?: string; status?: string }) {
  const search = new URLSearchParams();
  if (params?.source) search.set("source", params.source);
  if (params?.assignee_id) search.set("assignee_id", params.assignee_id);
  if (params?.status) search.set("status", params.status);
  const qs = search.toString();
  return api.get<AdminTaskRow[]>(`/v1/admin/tasks${qs ? `?${qs}` : ""}`);
}

export function useAdminTasksList() {
  return useQuery({
    queryKey: queryKeys.adminTasks.list(),
    queryFn: () => fetchAdminTasks(),
  });
}

export function useAdminTasksMyFocus(adminId: string | null) {
  return useQuery({
    queryKey: queryKeys.adminTasks.myFocus(adminId),
    queryFn: () => fetchAdminTasks({ assignee_id: adminId ?? undefined }),
    enabled: !!adminId,
  });
}

export function useAdminTasksAi() {
  return useQuery({
    queryKey: queryKeys.adminTasks.ai(),
    queryFn: () => fetchAdminTasks({ source: "ai" }),
  });
}

export function useAdminTasksOpen() {
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
