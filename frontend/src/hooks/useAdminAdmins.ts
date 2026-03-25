import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface AdminUserRow {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string | null;
  birth_date?: string | null;
  /** active | terminated — уволенный не может войти */
  employment_status: string;
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

export function usePatchAdminEmploymentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (args: { adminId: string; employment_status: "active" | "terminated" }) =>
      api.patch<AdminUserRow>(`/v1/admin/admins/${args.adminId}`, {
        employment_status: args.employment_status,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.adminAdmins.list() });
    },
  });
}
