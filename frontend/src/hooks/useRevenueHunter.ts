/**
 * Revenue Hunter: выручка, спасённая ИИ за ночь. Виджет на Dashboard.
 * Контракт (DEV_ARTIFACT_BACKEND_IMPLEMENTATION B5.3):
 * GET /api/v1/admin/clinics/{clinic_id}/reports/revenue-saved-by-ai
 * Response 200: { "amount": "5000.00", "period": "night" } | { "amount": null }
 * При отключённом Revenue Hunter — null или amount: null; виджет не показываем.
 */

import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { getAdminToken } from "@/api/client";

export interface RevenueHunterSavedResponse {
  amount: string | null;
  period?: string;
}

export function useRevenueHunterSaved(clinicId: string | null) {
  const token = getAdminToken();
  return useQuery({
    queryKey: ["admin", "revenue-hunter", "saved", clinicId ?? ""],
    queryFn: async (): Promise<RevenueHunterSavedResponse | null> => {
      if (!clinicId) return null;
      try {
        const res = await api.get<RevenueHunterSavedResponse>(
          `/v1/admin/clinics/${clinicId}/reports/revenue-saved-by-ai`,
          token
        );
        return res ?? null;
      } catch {
        return null;
      }
    },
    enabled: !!token && !!clinicId,
    staleTime: 60_000,
  });
}

export function isRevenueHunterEnabled(
  data: RevenueHunterSavedResponse | null | undefined
): boolean {
  return !!data && data.amount != null && data.amount !== "";
}
