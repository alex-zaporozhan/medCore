import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, getAdminToken } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export const OMNI_VAULT_EXPORT_PRESETS = [
  { id: "tax", label: "Для налоговой", columns: ["date", "patient", "service", "amount", "payment_type"] },
  { id: "vip_sleep", label: "Спящие VIP-клиенты", columns: ["patient", "ltv", "last_visit", "segment"] },
  { id: "consumables", label: "Расходники за период", columns: ["date", "service", "product", "amount", "warehouse"] },
] as const;

export type OmniVaultExportPreset = (typeof OMNI_VAULT_EXPORT_PRESETS)[number];

export interface OmniVaultMediaResponse {
  items: {
    id: string;
    url: string;
    type: string;
    patient_name?: string;
    channel?: string;
    created_at?: string;
  }[];
}

export function useOmniVaultMediaGallery(
  clinicId: string | null,
  filters: { type?: string; date_from?: string } = {}
) {
  const token = getAdminToken();
  return useQuery({
    queryKey: queryKeys.omniVault.media(clinicId ?? "", filters),
    queryFn: async () => {
      if (!clinicId) return { items: [] };
      try {
        const params = new URLSearchParams();
        if (filters.type) params.set("type", filters.type);
        if (filters.date_from) params.set("date_from", filters.date_from);
        const res = await api.get<OmniVaultMediaResponse>(
          `/v1/admin/clinics/${clinicId}/media?${params}`,
          token
        );
        return res ?? { items: [] };
      } catch {
        return { items: [] };
      }
    },
    enabled: !!token && !!clinicId,
  });
}

export function useOmniVaultExportPresets(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: queryKeys.omniVault.exportPresets(clinicId ?? ""),
    queryFn: async () => {
      if (!clinicId) return [...OMNI_VAULT_EXPORT_PRESETS];
      try {
        const res = await api.get<typeof OMNI_VAULT_EXPORT_PRESETS>(
          `/v1/admin/clinics/${clinicId}/export/presets`,
          token
        );
        return Array.isArray(res) && res.length > 0 ? res : [...OMNI_VAULT_EXPORT_PRESETS];
      } catch {
        return [...OMNI_VAULT_EXPORT_PRESETS];
      }
    },
    enabled: !!token && !!clinicId,
  });
}

export function useRequestOmniVaultBackupMutation(clinicId: string | null) {
  const token = getAdminToken();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      if (!clinicId) throw new Error("clinicId is required");
      return api.post<{ task_id: string }>(
        `/v1/admin/clinics/${clinicId}/backup/request`,
        {},
        token
      );
    },
    onSuccess: () => {
      if (clinicId) {
        qc.invalidateQueries({ queryKey: queryKeys.omniVault.backup(clinicId) });
      }
    },
  });
}

export function useOmniVaultBackupStatus(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: queryKeys.omniVault.backup(clinicId ?? ""),
    queryFn: async () => {
      if (!clinicId) return null;
      try {
        return await api.get<{ task_id: string; status: string; download_url?: string }>(
          `/v1/admin/clinics/${clinicId}/backup/status`,
          token
        );
      } catch {
        return null;
      }
    },
    enabled: !!token && !!clinicId,
  });
}
