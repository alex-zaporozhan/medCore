import { useQuery } from "@tanstack/react-query";
import { api, getAdminToken } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface RetentionSegment {
  id: string;
  name: string;
  description?: string;
  patient_count: number;
}

export interface RetentionCampaignRoi {
  campaign_id: string;
  campaign_name: string;
  sent: number;
  read: number;
  clicked: number;
  booked: number;
  paid: number;
}

export function useAdminRetentionSegments(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: queryKeys.adminRetention.segments(clinicId ?? ""),
    queryFn: async (): Promise<RetentionSegment[]> => {
      if (!clinicId) return [];
      try {
        const res = await api.get<RetentionSegment[]>(
          `/v1/admin/clinics/${clinicId}/retention/segments`,
          token
        );
        return Array.isArray(res) ? res : [];
      } catch {
        return [
          { id: "churn", name: "На грани ухода", patient_count: 0 },
          { id: "discount", name: "Охотники за скидками", patient_count: 0 },
          { id: "vip_sleep", name: "VIP в спячке", patient_count: 0 },
          { id: "due", name: "Пора на процедуру", patient_count: 0 },
        ];
      }
    },
    enabled: !!token && !!clinicId,
  });
}

export function useAdminRetentionCampaignsRoi(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: queryKeys.adminRetention.campaignsRoi(clinicId ?? ""),
    queryFn: async (): Promise<RetentionCampaignRoi[]> => {
      if (!clinicId) return [];
      try {
        const res = await api.get<RetentionCampaignRoi[]>(
          `/v1/admin/clinics/${clinicId}/retention/campaigns`,
          token
        );
        return Array.isArray(res) ? res : [];
      } catch {
        return [];
      }
    },
    enabled: !!token && !!clinicId,
  });
}
