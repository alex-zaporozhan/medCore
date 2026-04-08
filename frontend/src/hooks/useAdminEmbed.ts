import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export type AdminEmbedSettingsDto = {
  inbound_route_token: string;
  webhook_configured: boolean;
  webhook_bearer_prefix: string | null;
};

export type AdminEmbedApiKeyItem = {
  id: string;
  label: string | null;
  key_prefix: string;
  created_at: string;
  revoked_at: string | null;
};

export type AdminEmbedApiKeyListDto = {
  items: AdminEmbedApiKeyItem[];
};

export type AdminEmbedApiKeyCreatedDto = {
  id: string;
  token: string;
  key_prefix: string;
};

export type AdminEmbedWebhookRotateDto = {
  webhook_secret: string;
};

export function useAdminEmbedSettings(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.adminEmbed.settings(),
    queryFn: () => api.get<AdminEmbedSettingsDto>("/v1/admin/organization/embed/settings"),
    enabled,
  });
}

export function useAdminEmbedApiKeys(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.adminEmbed.apiKeys(),
    queryFn: () => api.get<AdminEmbedApiKeyListDto>("/v1/admin/organization/embed/api-keys"),
    enabled,
  });
}

export function useCreateAdminEmbedApiKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (label: string | null) =>
      api.post<AdminEmbedApiKeyCreatedDto>("/v1/admin/organization/embed/api-keys", {
        label: label?.trim() || null,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminEmbed.apiKeys() });
    },
  });
}

export function useRevokeAdminEmbedApiKeyMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (keyId: string) =>
      api.post<void>(`/v1/admin/organization/embed/api-keys/${keyId}/revoke`, {}),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminEmbed.apiKeys() });
    },
  });
}

export function useRotateAdminEmbedWebhookMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () =>
      api.post<AdminEmbedWebhookRotateDto>(
        "/v1/admin/organization/embed/webhook-secret/rotate",
        {}
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.adminEmbed.settings() });
    },
  });
}
