import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Clinic } from "@/api/types";
import { queryKeys } from "@/queryKeys";

export function useClinics(includeDeleted = false) {
  const query = includeDeleted ? "?include_deleted=true" : "";

  return useQuery({
    queryKey: queryKeys.clinics.list(includeDeleted),
    queryFn: () => api.get<Clinic[]>(`/v1/clinics${query}`),
  });
}

/** PATCH/PUT части полей клиники — инвалидация списка клиник. */
export function useUpdateClinicMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ clinicId, body }: { clinicId: string; body: Record<string, unknown> }) =>
      api.put<Clinic>(`/v1/clinics/${clinicId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.clinics.all });
    },
  });
}

export function useCreateClinicMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post<Clinic>("/v1/clinics", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.clinics.all });
    },
  });
}

