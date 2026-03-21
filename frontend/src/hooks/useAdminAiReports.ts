import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface ConflictItem {
  conversation_id: string;
  sentiment: string;
  issue_category: string;
  is_conflict: boolean;
  is_resolved: boolean;
  admin_mistakes: string[];
  business_root_causes: string[];
  suggested_playbook: string[];
  created_at: string;
}

export interface ConflictSummary {
  total: number;
  unresolved_conflicts: number;
  top_issue_categories: string[];
}

export interface ConflictReportResponse {
  summary: ConflictSummary;
  items: ConflictItem[];
  ai_status?: string | null;
}

export function useAdminAiConflictReport(dateFrom: string, dateTo: string) {
  return useQuery({
    queryKey: queryKeys.adminAiReports.conflicts(dateFrom, dateTo),
    queryFn: async () => {
      const params = new URLSearchParams();
      if (dateFrom) params.set("date_from", dateFrom);
      if (dateTo) params.set("date_to", dateTo);
      return api.get<ConflictReportResponse>(
        `/v1/admin/ai-reports/conflicts?${params.toString()}`
      );
    },
    enabled: !!dateFrom && !!dateTo,
  });
}
