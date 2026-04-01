import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface LeadLogRoutingRuleRow {
  id: string;
  channel_type: string | null;
  source_key: string | null;
  target_stream_id: string;
  is_active: boolean;
  sort_order: number;
}

export interface LeadLogRoutingRuleUpsertItem {
  channel_type: string | null;
  source_key: string | null;
  target_stream_id: string;
  is_active: boolean;
  sort_order: number;
}

export interface SimulateLeadLogRoutingRequest {
  channel_type: string | null;
  source_key: string | null;
}

export interface SimulateLeadLogRoutingResponse {
  matched_rule_id: string | null;
  target_stream_id: string | null;
}

export function useAdminLeadLogRoutingRules() {
  return useQuery({
    queryKey: ["admin-leads-log-routing-rules"],
    queryFn: () => api.get<LeadLogRoutingRuleRow[]>("/v1/admin/leads-log/routing-rules"),
  });
}

export function useSimulateAdminLeadLogRoutingMutation() {
  return useMutation({
    mutationFn: async (body: SimulateLeadLogRoutingRequest) => {
      return api.post<SimulateLeadLogRoutingResponse>("/v1/admin/leads-log/routing-rules/simulate", body);
    },
  });
}

export function useReplaceAdminLeadLogRoutingRulesMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (rules: LeadLogRoutingRuleUpsertItem[]) => {
      return api.put<LeadLogRoutingRuleRow[]>("/v1/admin/leads-log/routing-rules", { rules });
    },
    onSuccess: (data) => {
      qc.setQueryData(["admin-leads-log-routing-rules"], data);
      qc.invalidateQueries({ queryKey: ["admin-leads-log-routing-rules"] });
    },
  });
}

