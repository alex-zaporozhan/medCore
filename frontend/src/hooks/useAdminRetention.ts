import { useMutation, useQuery } from "@tanstack/react-query";
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

export interface RetentionOfferItem {
  patient_id: string;
  offer_text: string;
}

export function useAdminRetentionSegments(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: queryKeys.adminRetention.segments(clinicId ?? ""),
    queryFn: async (): Promise<RetentionSegment[]> => {
      if (!clinicId) return [];
      const res = await api.get<{ segments: RetentionSegment[] }>(
        `/v1/admin/clinics/${clinicId}/retention/segments`,
        token
      );
      const list = res?.segments;
      return Array.isArray(list) ? list : [];
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
      const res = await api.get<RetentionCampaignRoi[]>(
        `/v1/admin/clinics/${clinicId}/retention/campaigns/roi-summary`,
        token
      );
      return Array.isArray(res) ? res : [];
    },
    enabled: !!token && !!clinicId,
  });
}

export function useGenerateRetentionOffers() {
  return useMutation({
    mutationFn: async (segmentId: string): Promise<RetentionOfferItem[]> => {
      const token = getAdminToken();
      const res = await api.post<{ offers: RetentionOfferItem[] }>(
        "/v1/ai/generate-offers",
        { segment_id: segmentId },
        token
      );
      return Array.isArray(res?.offers) ? res.offers : [];
    },
  });
}
