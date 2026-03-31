import { useQuery } from "@tanstack/react-query";
import { api, getAdminToken } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface AdminSessionPayload {
  clinic_id: string;
  permissions: string[];
  roles: string[];
  organization_id?: string | null;
  accessible_clinic_ids?: string[];
}

/** RBAC снимок для UI (лента, staff collab): после логина инвалидируйте ключ `queryKeys.adminSession()`. */
export function useAdminSession() {
  return useQuery({
    queryKey: queryKeys.adminSession(),
    queryFn: () => api.get<AdminSessionPayload>("/v1/admin/auth/session"),
    enabled: typeof window !== "undefined" && !!getAdminToken(),
  });
}
