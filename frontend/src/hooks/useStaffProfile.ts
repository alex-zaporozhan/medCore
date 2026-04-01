import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface StaffProfileDto {
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

export function useStaffProfile(adminId: string | null) {
  return useQuery({
    queryKey: ["staff-profile", adminId] as const,
    queryFn: () => api.get<StaffProfileDto>(`/v1/admin/staff/profiles/${adminId}`),
    enabled: Boolean(adminId),
  });
}

