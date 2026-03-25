import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AdminTaskRow } from "./useAdminTasks";

/** Узкий хук для календарного prefill: GET /v1/admin/tasks/{task_id}. */
export function useAdminTaskDetails(taskId: string | null) {
  return useQuery({
    queryKey: ["admin-tasks", "details", taskId] as const,
    queryFn: () => api.get<AdminTaskRow>(`/v1/admin/tasks/${taskId}`),
    enabled: !!taskId,
  });
}
