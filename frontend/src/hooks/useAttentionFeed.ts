import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AttentionFeed } from "@/api/types";

export function useAttentionFeed(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "attention-feed"],
    queryFn: () => api.get<AttentionFeed>(`/v1/admin/clinics/${clinicId}/attention-feed`),
    enabled: !!clinicId,
  });
}

export function useCloseFollowUp(clinicId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (messageId: string) =>
      api.post<{ ok: boolean }>(`/v1/admin/clinics/${clinicId}/attention-feed/follow-up/${messageId}/close`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "clinics", clinicId, "attention-feed"] });
    },
  });
}

