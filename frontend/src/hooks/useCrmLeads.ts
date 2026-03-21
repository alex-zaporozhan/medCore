import type { QueryKey } from "@tanstack/react-query";
import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
} from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

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

/** Full lead row (list + details). */
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

/** Kanban projection: smaller payload from GET /leads?projection=kanban */
export interface LeadKanbanCard {
  id: string;
  clinic_id: string;
  pipeline_id: string;
  stage_id: string;
  omnichannel_contact_id: string | null;
  title: string;
  source: string;
  estimated_value: string;
  actual_value: string;
  status: string;
  created_at: string;
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

export interface LeadKanbanListResponse {
  items: LeadKanbanCard[];
  total: number | null;
  next_cursor?: string | null;
}

/** Cursor pagination (Kanban column load-more). */
export interface LeadKanbanCursorResponse {
  items: LeadKanbanCard[];
  total: number | null;
  next_cursor: string | null;
}

export interface LeadDetailsResponse {
  lead: LeadCard;
  notes: LeadNote[];
}

export interface AiLeadSummaryResponse {
  summary: string;
  highlights: string[];
  risks: string[];
  suggested_actions: string[];
  ai_status?: string | null;
  trace_id?: string | null;
}

export interface AiSuggestNextStageResponse {
  suggested_stage_id: string | null;
  confidence: number;
  rationale?: string | null;
  ai_status?: string | null;
  trace_id?: string | null;
}

export interface AiUpdateLeadStageRequest {
  clinic_id: string;
  target_stage_id: string;
  reason?: string | null;
  initiated_by_ai?: boolean;
}

export interface AiUpdateLeadStageResponse {
  success: boolean;
  lead?: {
    lead_token: string;
    clinic_id: string;
    pipeline_id: string;
    stage_id: string;
    status: string;
    title: string;
    source: string;
    estimated_value: string;
    actual_value: string;
    created_at?: string | null;
    closed_at?: string | null;
  } | null;
  error_code?: string | null;
  error_message?: string | null;
  trace_id?: string | null;
}

export interface AiCreateLeadTaskRequest {
  clinic_id: string;
  title: string;
  description?: string | null;
  priority?: string;
  due_at?: string | null;
  reason?: string | null;
  initiated_by_ai?: boolean;
}

export interface AiCreateLeadTaskResponse {
  success: boolean;
  task_id?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  trace_id?: string | null;
}

export interface AiIgnoreRecommendationRequest {
  clinic_id: string;
  kind: string;
  reason?: string | null;
  trace_id?: string | null;
}

export interface AiIgnoreRecommendationResponse {
  success: boolean;
  trace_id?: string | null;
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
  /** `kanban` uses lighter items and backend load_only (PERF). */
  projection?: "full" | "kanban";
}

export function useCrmPipelines() {
  return useQuery({
    queryKey: queryKeys.crm.pipelines(),
    queryFn: () => api.get<LeadPipeline[]>("/v1/admin/crm/pipelines"),
  });
}

export function useCrmStages(pipelineId: string | null) {
  return useQuery({
    queryKey: queryKeys.crm.stages(pipelineId),
    enabled: !!pipelineId,
    queryFn: () =>
      api.get<LeadStage[]>(
        `/v1/admin/crm/stages?pipeline_id=${encodeURIComponent(pipelineId!)}`
      ),
  });
}

/** GET /v1/admin/crm/pipelines/{id}/stage-semantics — QA_ARCH W4.2 D4. */
export interface PipelineStageSemanticsResponse {
  pipeline_id: string;
  supported_semantics: string[];
  mappings: { semantic: string; stage_id: string }[];
  /** Same resolution as server transition checks (explicit map + code infer). */
  resolved_stage_semantics?: { stage_id: string; semantic: string | null }[];
}

export function usePipelineStageSemantics(pipelineId: string | null) {
  return useQuery({
    queryKey: queryKeys.crm.pipelineSemantics(pipelineId),
    enabled: !!pipelineId,
    queryFn: () =>
      api.get<PipelineStageSemanticsResponse>(
        `/v1/admin/crm/pipelines/${encodeURIComponent(pipelineId!)}/stage-semantics`
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
  const projection = filters.projection ?? "full";
  if (projection !== "full") params.set("projection", projection);
  const query = params.toString();

  return useQuery({
    queryKey: [...queryKeys.crm.leadsListPrefix, filters],
    queryFn: () =>
      api.get<LeadListResponse | LeadKanbanListResponse>(
        `/v1/admin/crm/leads${query ? `?${query}` : ""}`
      ),
  });
}

export interface CrmKanbanStageInfiniteFilters {
  stageId: string;
  status?: string;
  search?: string;
  pageSize?: number;
  enabled?: boolean;
}

/** Per-column Kanban leads with cursor pagination (Engine L2). */
export function useCrmKanbanStageLeadsInfinite(filters: CrmKanbanStageInfiniteFilters) {
  const pageSize = filters.pageSize ?? 40;
  return useInfiniteQuery({
    queryKey: queryKeys.crm.kanbanInfinite(
      filters.stageId,
      filters.status ?? "",
      filters.search ?? "",
      pageSize
    ),
    enabled: filters.enabled !== false && !!filters.stageId,
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams();
      params.set("stage_id", filters.stageId);
      params.set("projection", "kanban");
      params.set("pagination", "cursor");
      params.set("page_size", String(pageSize));
      if (filters.status) params.set("status", filters.status);
      if (filters.search) params.set("search", filters.search);
      if (pageParam) params.set("cursor", pageParam);
      return api.get<LeadKanbanCursorResponse>(
        `/v1/admin/crm/leads?${params.toString()}`
      );
    },
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

export function useCrmLeadDetails(leadId: string | null) {
  return useQuery({
    queryKey: queryKeys.crm.leadDetails(leadId),
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
      enforceSemanticTransition,
    }: {
      leadId: string;
      newStageId: string;
      /** When true, backend rejects invalid semantic transitions (parity with strict Kanban UI). */
      enforceSemanticTransition?: boolean;
    }) =>
      api.patch<LeadCard>(`/v1/admin/crm/leads/${leadId}/stage`, {
        new_stage_id: newStageId,
        enforce_semantic_transition: enforceSemanticTransition ?? false,
      }),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.crm.leadsListPrefix });
      const previous: [QueryKey, LeadListResponse | undefined][] = queryClient.getQueriesData(
        { queryKey: queryKeys.crm.leadsListPrefix }
      );
      queryClient.setQueriesData<LeadListResponse>(
        { queryKey: queryKeys.crm.leadsListPrefix },
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
      queryClient.invalidateQueries({ queryKey: queryKeys.crm.leadsListPrefix });
      queryClient.invalidateQueries({ queryKey: queryKeys.crm.kanbanPrefix });
      queryClient.invalidateQueries({
        queryKey: queryKeys.crm.leadDetails(variables.leadId),
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
        queryKey: queryKeys.crm.leadDetails(variables.leadId),
      });
    },
  });
}

export function useAiLeadSummary(leadId: string | null) {
  return useQuery({
    queryKey: queryKeys.crm.leadAiSummary(leadId),
    enabled: false,
    queryFn: () => api.get<AiLeadSummaryResponse>(`/v1/admin/crm/leads/${leadId}/ai/summary`),
  });
}

export function useAiSuggestNextStage(leadId: string | null) {
  return useQuery({
    queryKey: queryKeys.crm.leadAiSuggest(leadId),
    enabled: false,
    queryFn: () =>
      api.get<AiSuggestNextStageResponse>(
        `/v1/admin/crm/leads/${leadId}/ai/suggest-next-stage`
      ),
  });
}

export function useAiUpdateLeadStage(leadId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: AiUpdateLeadStageRequest) =>
      api.patch<AiUpdateLeadStageResponse>(`/v1/admin/crm/leads/${leadId}/ai/stage`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.crm.leadsListPrefix });
      if (leadId) queryClient.invalidateQueries({ queryKey: queryKeys.crm.leadDetails(leadId) });
    },
  });
}

export function useAiCreateTaskForLead(leadId: string | null) {
  return useMutation({
    mutationFn: (body: AiCreateLeadTaskRequest) =>
      api.post<AiCreateLeadTaskResponse>(`/v1/admin/crm/leads/${leadId}/ai/tasks`, body),
  });
}

export function useAiIgnoreLeadRecommendation(leadId: string | null) {
  return useMutation({
    mutationFn: (body: AiIgnoreRecommendationRequest) =>
      api.post<AiIgnoreRecommendationResponse>(
        `/v1/admin/crm/leads/${leadId}/ai/recommendations/ignore`,
        body
      ),
  });
}

