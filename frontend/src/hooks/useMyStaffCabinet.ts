import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface MyStaffProfileDto {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string | null;
  birth_date: string | null;
  employment_status: string;
  profession_category_id: string | null;
  profession_category_name: string | null;
  bio?: string | null;
  avatar_url?: string | null;
}

export function useMyStaffProfile() {
  return useQuery({
    queryKey: ["staff-me-profile"] as const,
    queryFn: () => api.get<MyStaffProfileDto>(`/v1/admin/staff/me/profile`),
  });
}

export function usePatchMyStaffProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { bio?: string }) => api.patch<MyStaffProfileDto>(`/v1/admin/staff/me/profile`, payload),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["staff-me-profile"] as const });
    },
  });
}

export function useUploadMyStaffAvatar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.postFormData<{ avatar_url: string }>(`/v1/admin/staff/me/avatar`, fd);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["staff-me-profile"] as const });
    },
  });
}

