import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface NotificationChannelConfigRead {
  id: string;
  clinic_id: string;
  channel: "telegram" | "sms" | "email";
  config_json: Record<string, unknown> | null;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface NotificationChannelConfigCreate {
  channel: "telegram" | "sms" | "email";
  enabled: boolean;
  config_json?: Record<string, unknown> | null;
}

export function useChannelConfigs(clinicId: string | null) {
  return useQuery({
    queryKey: ["channel-configs", clinicId],
    queryFn: () =>
      api.get<NotificationChannelConfigRead[]>(
        `/v1/admin/clinics/${clinicId}/channel-configs`
      ),
    enabled: !!clinicId,
  });
}

export function useUpsertChannelConfig(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      channel,
      body,
    }: {
      channel: "telegram" | "sms" | "email";
      body: NotificationChannelConfigCreate;
    }) =>
      api.put<NotificationChannelConfigRead>(
        `/v1/admin/clinics/${clinicId}/channel-configs/${channel}`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["channel-configs", clinicId] });
    },
  });
}
