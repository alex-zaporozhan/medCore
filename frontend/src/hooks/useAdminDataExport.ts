import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export type DataExportSummaryDto = {
  organization_id: string;
  clinics: { id: string; name: string }[];
  approximate_counts: Record<string, number>;
  formats_note?: string;
};

export type DataExportRequestDto = {
  request_id: string;
  status: string;
  message: string;
};

export function useAdminDataExportSummary(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.adminDataExport.summary(),
    queryFn: () => api.get<DataExportSummaryDto>("/v1/admin/organization/data-export/summary"),
    enabled,
  });
}

export function useRequestDataExportMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { export_kind?: string; note?: string | null }) =>
      api.post<DataExportRequestDto>("/v1/admin/organization/data-export/request", payload),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: queryKeys.adminDataExport.summary() });
    },
  });
}
