import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface MarketingChannelSummaryItem {
  traffic_source_id: string | null;
  campaign_id: string | null;
  traffic_source_code: string | null;
  traffic_source_name: string | null;
  campaign_code: string | null;
  campaign_name: string | null;
  leads_count: number;
  bookings_count: number;
  completed_bookings_count: number;
  unique_patients_count: number;
  revenue_sum: string;
  avg_check: string;
  ad_spend: string | null;
  roi: number | null;
  cac: number | null;
}

export interface AttributionDrillDownItem {
  id: string;
  type: string;
  display_label: string | null;
  happened_at: string | null;
}

export interface AttributionDrillDownResponse {
  items: AttributionDrillDownItem[];
  total: number;
}

export interface MarketingAttributionSummary {
  clinic_id: string;
  date_from: string;
  date_to: string;
  items: MarketingChannelSummaryItem[];
}

export interface MarketingCampaignRead {
  id: string;
  clinic_id: string;
  traffic_source_id: string | null;
  code: string;
  name: string;
  external_id: string | null;
  budget_planned: string | null;
  budget_actual: string | null;
  is_active: boolean;
}

export function useMarketingAttributionSummary(
  clinicId: string | null,
  dateFrom: string | null,
  dateTo: string | null,
  trafficSourceId: string | null,
  campaignId: string | null
) {
  const hasClinic = !!clinicId;
  const hasDates = !!dateFrom && !!dateTo;
  const hasTrafficSource = !!trafficSourceId;
  const hasCampaign = !!campaignId;

  const searchParams = new URLSearchParams();
  if (dateFrom) searchParams.set("date_from", dateFrom);
  if (dateTo) searchParams.set("date_to", dateTo);
  if (hasTrafficSource) searchParams.set("traffic_source_id", trafficSourceId as string);
  if (hasCampaign) searchParams.set("campaign_id", campaignId as string);

  return useQuery({
    queryKey: [
      "admin",
      "attribution",
      "summary",
      clinicId,
      dateFrom,
      dateTo,
      trafficSourceId,
      campaignId,
    ],
    queryFn: () =>
      api.get<MarketingAttributionSummary>(
        `/v1/admin/attribution/summary?${searchParams.toString()}`
      ),
    enabled: hasClinic && hasDates,
  });
}

export function useMarketingCampaigns() {
  return useQuery({
    queryKey: ["admin", "attribution", "campaigns"],
    queryFn: () => api.get<MarketingCampaignRead[]>(`/v1/admin/attribution/campaigns`),
  });
}

export function useMarketingAttributionDrillDown(params: {
  dateFrom: string | null;
  dateTo: string | null;
  drillType: "leads" | "bookings" | "transactions";
  trafficSourceId: string | null;
  campaignId: string | null;
  enabled?: boolean;
}) {
  const { dateFrom, dateTo, drillType, trafficSourceId, campaignId, enabled = true } = params;
  const search = new URLSearchParams();
  if (dateFrom) search.set("date_from", dateFrom);
  if (dateTo) search.set("date_to", dateTo);
  search.set("drill_type", drillType);
  if (trafficSourceId) search.set("traffic_source_id", trafficSourceId);
  if (campaignId) search.set("campaign_id", campaignId);

  return useQuery({
    queryKey: ["admin", "attribution", "drill-down", params],
    queryFn: () =>
      api.get<AttributionDrillDownResponse>(`/v1/admin/attribution/drill-down?${search.toString()}`),
    enabled: !!dateFrom && !!dateTo && enabled,
  });
}

