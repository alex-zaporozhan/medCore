import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface IntegrationSettings1c {
  provider: string;
  api_url: string | null;
  has_credentials: boolean;
}

export function useAdminIntegrationSettings1c(clinicId: string) {
  return useQuery({
    queryKey: queryKeys.integrationSettings1c(clinicId),
    queryFn: () =>
      api.get<IntegrationSettings1c>(
        `/v1/admin/clinics/${clinicId}/integration-settings/1c`
      ),
    enabled: !!clinicId,
  });
}

export function useUpdateAdminIntegrationSettings1cMutation(clinicId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { api_url?: string | null; credentials?: string | null }) =>
      api.put<IntegrationSettings1c>(
        `/v1/admin/clinics/${clinicId}/integration-settings/1c`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.integrationSettings1c(clinicId) });
    },
  });
}
