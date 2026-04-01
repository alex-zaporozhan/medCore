import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export type LeadLogOutcome = "BOOKED" | "NOT_BOOKED" | "UNKNOWN";

export interface AdminLeadLogListItem {
  id: string;
  clinic_id: string;
  omni_chat_id: string;
  contact_id: string;
  contact_name: string | null;
  contact_primary_phone: string | null;
  opened_by_admin_id: string | null;
  opened_by_admin_name: string | null;
  opened_at: string | null;
  closed_at: string;
  title: string;
  outcome: LeadLogOutcome | string;
  lead_id: string | null;
  booking_id: string | null;
  patient_id: string | null;
}

export interface AdminLeadLogDetail extends AdminLeadLogListItem {
  transcript_text: string;
  transcript_json: Record<string, unknown>;
}

export function useAdminLeadLogs(params: { day: string; outcome?: LeadLogOutcome | "ALL" }) {
  const qs = new URLSearchParams();
  qs.set("day", params.day);
  if (params.outcome && params.outcome !== "ALL") qs.set("outcome", params.outcome);
  return useQuery({
    queryKey: ["admin-lead-logs", params],
    queryFn: () => api.get<AdminLeadLogListItem[]>(`/v1/admin/lead-logs?${qs.toString()}`),
  });
}

export function useAdminLeadLogDetail(logId: string | null) {
  return useQuery({
    queryKey: ["admin-lead-log", logId],
    queryFn: () => api.get<AdminLeadLogDetail>(`/v1/admin/lead-logs/${logId}`),
    enabled: !!logId,
  });
}

