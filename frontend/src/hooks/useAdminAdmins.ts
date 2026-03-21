import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface AdminUserRow {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string | null;
  birth_date?: string | null;
}

export function useAdminAdmins() {
  return useQuery({
    queryKey: queryKeys.adminAdmins.list(),
    queryFn: () => api.get<AdminUserRow[]>("/v1/admin/admins"),
  });
}

export function useCreateAdminMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      email: string;
      password: string;
      full_name?: string | null;
      birth_date?: string | null;
    }) => api.post<AdminUserRow>("/v1/admin/admins", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.adminAdmins.list() });
    },
  });
}
