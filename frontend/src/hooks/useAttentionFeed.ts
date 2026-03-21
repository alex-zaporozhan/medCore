import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AttentionFeed } from "@/api/types";
import { queryKeys } from "@/queryKeys";

export function useAttentionFeed(clinicId: string | null) {
  return useQuery({
    queryKey: queryKeys.attentionFeed(clinicId),
    queryFn: () => api.get<AttentionFeed>(`/v1/admin/clinics/${clinicId}/attention-feed`),
    enabled: !!clinicId,
  });
}

export function useCloseFollowUp(clinicId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (messageId: string) => {
      if (!clinicId) {
        return Promise.reject(new Error("clinicId is required"));
      }
      return api.post<{ ok: boolean }>(
        `/v1/admin/clinics/${clinicId}/attention-feed/follow-up/${messageId}/close`
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.attentionFeed(clinicId) });
    },
  });
}

export function useCreateAttentionFeedTask(clinicId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      kind: "follow_up" | "retention_gap" | "conflict";
      id: string;
      title: string;
      description?: string | null;
    }) => {
      if (!clinicId) {
        return Promise.reject(new Error("clinicId is required"));
      }
      return api.post(
        `/v1/admin/clinics/${clinicId}/attention-feed/${vars.kind}/${vars.id}/tasks`,
        {
          title: vars.title,
          description: vars.description ?? null,
        }
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.attentionFeed(clinicId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.adminTasks.prefix });
    },
  });
}

