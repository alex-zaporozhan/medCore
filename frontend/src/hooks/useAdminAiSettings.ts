import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export type AiMode = "draft_only" | "safe_autoreply" | "analytics_only";

export interface AdminClinicAiSettings {
  ai_enabled: boolean;
  ai_mode: AiMode;
  ai_business_prompt: string | null;
  ai_allowed_intents: string[];
  ai_autoreply_enabled: boolean;
  ai_autoreply_hours: Record<string, unknown> | null;
  ai_provider_type: string;
}

export interface AdminAiStatusResponse {
  ai_mode: "disabled" | "fallback_local" | "external_active";
  features: Record<string, boolean>;
}

export function useAdminClinicAiSettings(clinicId: string | null) {
  return useQuery({
    queryKey: queryKeys.adminAi.clinicSettings(clinicId),
    queryFn: () =>
      api.get<AdminClinicAiSettings>(`/v1/admin/clinics/${clinicId}/ai-settings`),
    enabled: !!clinicId,
  });
}

/** GET /v1/admin/ai-status — без клиники; ошибки не блокируют экран настроек. */
export function useAdminAiStatus() {
  return useQuery({
    queryKey: queryKeys.adminAi.status(),
    queryFn: () => api.get<AdminAiStatusResponse>("/v1/admin/ai-status"),
    retry: false,
  });
}

export function useUpdateAdminClinicAiSettingsMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AdminClinicAiSettings) => {
      if (!clinicId) {
        return Promise.reject(new Error("clinicId is required"));
      }
      return api.put<AdminClinicAiSettings>(
        `/v1/admin/clinics/${clinicId}/ai-settings`,
        body
      );
    },
    onSuccess: () => {
      if (clinicId) {
        qc.invalidateQueries({ queryKey: queryKeys.adminAi.clinicSettings(clinicId) });
      }
    },
  });
}
