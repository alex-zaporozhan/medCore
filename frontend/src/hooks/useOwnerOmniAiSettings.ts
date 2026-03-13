import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface OmniBusinessAiSettings {
  ai_mode: string;
  working_hours_policy: Record<string, unknown> | null;
  confidence_thresholds: Record<string, unknown> | null;
  prompt_profile_id: string | null;
  kb_profile_id: string | null;
}

export interface OmniChannelAiSettings {
  channel_id: string;
  channel_type: string;
  channel_display_name: string;
  ai_mode: string;
}

export interface OmniAiSettingsResponse {
  business: OmniBusinessAiSettings;
  channels: OmniChannelAiSettings[];
}

export interface OmniBusinessAiSettingsUpdate {
  ai_mode?: string;
  working_hours_policy?: Record<string, unknown> | null;
  confidence_thresholds?: Record<string, unknown> | null;
  prompt_profile_id?: string | null;
  kb_profile_id?: string | null;
}

export interface OmniChannelAiSettingsUpdate {
  channel_id: string;
  ai_mode: string;
}

export interface OmniAiSettingsUpdateRequest {
  business?: OmniBusinessAiSettingsUpdate | null;
  channels?: OmniChannelAiSettingsUpdate[] | null;
}

const OMNI_AI_MODES = ["DISABLED", "AUTO_REPLY", "SUGGEST_ONLY"] as const;

export function useOwnerOmniAiSettings() {
  return useQuery({
    queryKey: ["owner-omni-ai-settings"],
    queryFn: () =>
      api.get<OmniAiSettingsResponse>("/v1/owner/omni-ai-settings"),
  });
}

export function useUpdateOwnerOmniAiSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: OmniAiSettingsUpdateRequest) =>
      api.put<OmniAiSettingsResponse>("/v1/owner/omni-ai-settings", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["owner-omni-ai-settings"] });
    },
  });
}

export { OMNI_AI_MODES };
