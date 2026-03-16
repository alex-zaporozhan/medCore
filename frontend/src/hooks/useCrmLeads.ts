import type { QueryKey } from "@tanstack/react-query";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface LeadPipeline {
  id: string;
  clinic_id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface LeadStage {
  id: string;
  clinic_id: string;
  pipeline_id: string;
  order: number;
  code: string;
  name: string;
  probability: number;
  color: string;
  created_at: string;
  updated_at: string;
  /** B4.1: aggregates for Kanban column header */
  leads_count?: number;
  sum_estimated_value?: string;
}

export interface LeadCard {
  id: string;
  clinic_id: string;
  pipeline_id: string;
  stage_id: string;
  omnichannel_contact_id: string | null;
  patient_id: string | null;
  primary_booking_id: string | null;
  visit_attribution_id: string | null;
  title: string;
  source: string;
  utm_source: string | null;
  utm_medium: string | null;
  utm_campaign: string | null;
  utm_content: string | null;
  utm_term: string | null;
  estimated_value: string;
  actual_value: string;
  status: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  lost_reason: string | null;
}

export interface LeadNote {
  id: string;
  clinic_id: string;
  lead_id: string;
  author_admin_id: string;
  text: string;
  created_at: string;
}

export interface LeadListResponse {
  items: LeadCard[];
  total: number;
}

export interface LeadDetailsResponse {
  lead: LeadCard;
  notes: LeadNote[];
}

export interface CrmLeadFilters {
  stage_id?: string;
  status?: string;
  date_from?: string;
  date_to?: string;
  source?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export function useCrmPipelines() {
  return useQuery({
    queryKey: ["crm-pipelines"],
    queryFn: () => api.get<LeadPipeline[]>("/v1/admin/crm/pipelines"),
  });
}

export function useCrmStages(pipelineId: string | null) {
  return useQuery({
    queryKey: ["crm-stages", pipelineId],
    enabled: !!pipelineId,
    queryFn: () =>
      api.get<LeadStage[]>(
        `/v1/admin/crm/stages?pipeline_id=${encodeURIComponent(pipelineId!)}`
      ),
  });
}

export function useCrmLeads(filters: CrmLeadFilters = {}) {
  const params = new URLSearchParams();
  if (filters.stage_id) params.set("stage_id", filters.stage_id);
  if (filters.status) params.set("status", filters.status);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);
  if (filters.source) params.set("source", filters.source);
  if (filters.search) params.set("search", filters.search);
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.page_size !== undefined) params.set("page_size", String(filters.page_size));
  const query = params.toString();

  return useQuery({
    queryKey: ["crm-leads", filters],
    queryFn: () =>
      api.get<LeadListResponse>(
        `/v1/admin/crm/leads${query ? `?${query}` : ""}`
      ),
  });
}

export function useCrmLeadDetails(leadId: string | null) {
  return useQuery({
    queryKey: ["crm-lead-details", leadId],
    enabled: !!leadId,
    queryFn: () =>
      api.get<LeadDetailsResponse>(`/v1/admin/crm/leads/${leadId}`),
  });
}

export function useUpdateLeadStage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      leadId,
      newStageId,
    }: {
      leadId: string;
      newStageId: string;
    }) =>
      api.patch<LeadCard>(`/v1/admin/crm/leads/${leadId}/stage`, {
        new_stage_id: newStageId,
      }),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: ["crm-leads"] });
      const previous: [QueryKey, LeadListResponse | undefined][] = queryClient.getQueriesData(
        { queryKey: ["crm-leads"] }
      );
      queryClient.setQueriesData<LeadListResponse>(
        { queryKey: ["crm-leads"] },
        (old) => {
          if (!old?.items) return old;
          return {
            ...old,
            items: old.items.map((lead) =>
              lead.id === variables.leadId
                ? { ...lead, stage_id: variables.newStageId }
                : lead
            ),
          };
        }
      );
      return { previous };
    },
    onError: (_err, _variables, context: { previous: [QueryKey, LeadListResponse | undefined][] } | undefined) => {
      if (context?.previous) {
        context.previous.forEach(([key, data]) => queryClient.setQueryData(key, data));
      }
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: ["crm-leads"] });
      queryClient.invalidateQueries({
        queryKey: ["crm-lead-details", variables.leadId],
      });
    },
  });
}

export function useCreateLeadNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      leadId,
      text,
    }: {
      leadId: string;
      text: string;
    }) =>
      api.post<LeadNote>(`/v1/admin/crm/leads/${leadId}/notes`, {
        text,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["crm-lead-details", variables.leadId],
      });
    },
  });
}

