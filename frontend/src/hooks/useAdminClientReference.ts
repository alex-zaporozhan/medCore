import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface ClientReferenceResponse {
  content: string;
}

export function useAdminClientReference() {
  return useQuery({
    queryKey: queryKeys.adminClientReference(),
    queryFn: () => api.get<ClientReferenceResponse>("/v1/admin/client-reference"),
  });
}

export function useUpdateAdminClientReferenceMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { content: string }) =>
      api.put<ClientReferenceResponse>("/v1/admin/client-reference", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.adminClientReference() });
    },
  });
}
