import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface RecallSegmentRead {
  id: string;
  clinic_id: string;
  name: string;
  filter_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface RecallSegmentWithCount extends RecallSegmentRead {
  patient_count: number;
}

export interface RecallSegmentCreate {
  name: string;
  filter_json?: Record<string, unknown> | null;
}

export interface RecallSegmentUpdate {
  name?: string;
  filter_json?: Record<string, unknown> | null;
}

export interface RecallTemplateRead {
  id: string;
  clinic_id: string;
  name: string;
  channel: string;
  subject: string | null;
  body_template: string;
  created_at: string;
  updated_at: string;
}

export interface RecallTemplateCreate {
  name: string;
  channel: string;
  subject?: string | null;
  body_template: string;
}

export interface RecallTemplateUpdate {
  name?: string;
  channel?: string;
  subject?: string | null;
  body_template?: string;
}

export interface RecallCampaignRead {
  id: string;
  clinic_id: string;
  segment_id: string;
  template_id: string;
  name: string;
  status: string;
  scheduled_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RecallCampaignCreate {
  segment_id: string;
  template_id: string;
  name: string;
  status?: string;
  scheduled_at?: string | null;
}

export interface RecallCampaignUpdate {
  segment_id?: string;
  template_id?: string;
  name?: string;
  status?: string;
  scheduled_at?: string | null;
}

export interface RecallAutomationRead {
  id: string;
  clinic_id: string;
  name: string;
  trigger_type: string;
  trigger_config_json: Record<string, unknown> | null;
  segment_id: string | null;
  template_id: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecallAutomationCreate {
  name: string;
  trigger_type: string;
  trigger_config_json?: Record<string, unknown> | null;
  segment_id?: string | null;
  template_id: string;
  enabled?: boolean;
}

export interface RecallAutomationUpdate {
  name?: string;
  trigger_type?: string;
  trigger_config_json?: Record<string, unknown> | null;
  segment_id?: string | null;
  template_id?: string;
  enabled?: boolean;
}

export interface RecallLogRead {
  id: string;
  clinic_id: string;
  campaign_id: string | null;
  automation_id: string | null;
  patient_id: string;
  channel: string;
  status: string;
  sent_at: string | null;
  error: string | null;
  created_at: string;
}

const recallKeys = (clinicId: string | null) =>
  ["admin", "clinics", clinicId, "recall"] as const;

export function useAdminRecallSegments(clinicId: string | null) {
  return useQuery({
    queryKey: [...recallKeys(clinicId), "segments"],
    queryFn: () =>
      api.get<RecallSegmentWithCount[]>(
        `/v1/admin/clinics/${clinicId}/recall/segments`
      ),
    enabled: !!clinicId,
  });
}

export function useCreateRecallSegment(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecallSegmentCreate) =>
      api.post<RecallSegmentRead>(
        `/v1/admin/clinics/${clinicId}/recall/segments`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useUpdateRecallSegment(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      segmentId,
      body,
    }: { segmentId: string; body: RecallSegmentUpdate }) =>
      api.put<RecallSegmentRead>(
        `/v1/admin/clinics/${clinicId}/recall/segments/${segmentId}`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useDeleteRecallSegment(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (segmentId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/recall/segments/${segmentId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useAdminRecallTemplates(clinicId: string | null) {
  return useQuery({
    queryKey: [...recallKeys(clinicId), "templates"],
    queryFn: () =>
      api.get<RecallTemplateRead[]>(
        `/v1/admin/clinics/${clinicId}/recall/templates`
      ),
    enabled: !!clinicId,
  });
}

export function useCreateRecallTemplate(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecallTemplateCreate) =>
      api.post<RecallTemplateRead>(
        `/v1/admin/clinics/${clinicId}/recall/templates`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useUpdateRecallTemplate(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      templateId,
      body,
    }: { templateId: string; body: RecallTemplateUpdate }) =>
      api.put<RecallTemplateRead>(
        `/v1/admin/clinics/${clinicId}/recall/templates/${templateId}`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useDeleteRecallTemplate(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (templateId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/recall/templates/${templateId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useAdminRecallCampaigns(clinicId: string | null) {
  return useQuery({
    queryKey: [...recallKeys(clinicId), "campaigns"],
    queryFn: () =>
      api.get<RecallCampaignRead[]>(
        `/v1/admin/clinics/${clinicId}/recall/campaigns`
      ),
    enabled: !!clinicId,
  });
}

export function useCreateRecallCampaign(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecallCampaignCreate) =>
      api.post<RecallCampaignRead>(
        `/v1/admin/clinics/${clinicId}/recall/campaigns`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useUpdateRecallCampaign(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      campaignId,
      body,
    }: { campaignId: string; body: RecallCampaignUpdate }) =>
      api.put<RecallCampaignRead>(
        `/v1/admin/clinics/${clinicId}/recall/campaigns/${campaignId}`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useDeleteRecallCampaign(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/recall/campaigns/${campaignId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useRunRecallCampaign(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (campaignId: string) =>
      api.post<{ sent: number; failed: number }>(
        `/v1/admin/clinics/${clinicId}/recall/campaigns/${campaignId}/run`
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useAdminRecallAutomations(clinicId: string | null) {
  return useQuery({
    queryKey: [...recallKeys(clinicId), "automations"],
    queryFn: () =>
      api.get<RecallAutomationRead[]>(
        `/v1/admin/clinics/${clinicId}/recall/automations`
      ),
    enabled: !!clinicId,
  });
}

export function useCreateRecallAutomation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: RecallAutomationCreate) =>
      api.post<RecallAutomationRead>(
        `/v1/admin/clinics/${clinicId}/recall/automations`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useUpdateRecallAutomation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      automationId,
      body,
    }: { automationId: string; body: RecallAutomationUpdate }) =>
      api.put<RecallAutomationRead>(
        `/v1/admin/clinics/${clinicId}/recall/automations/${automationId}`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useDeleteRecallAutomation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (automationId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/recall/automations/${automationId}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: recallKeys(clinicId) }),
  });
}

export function useAdminRecallLogs(
  clinicId: string | null,
  campaignId: string | null = null
) {
  const params = campaignId ? `?campaign_id=${campaignId}` : "";
  return useQuery({
    queryKey: [...recallKeys(clinicId), "logs", campaignId],
    queryFn: () =>
      api.get<RecallLogRead[]>(
        `/v1/admin/clinics/${clinicId}/recall/logs${params}`
      ),
    enabled: !!clinicId,
  });
}
