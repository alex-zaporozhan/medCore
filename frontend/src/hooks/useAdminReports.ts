import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface DashboardReport {
  date: string;
  bookings_pending: number;
  bookings_confirmed: number;
  bookings_completed: number;
  bookings_cancelled: number;
  bookings_no_show: number;
  new_patients: number;
  /** Approx. count of new CRM cards/leads (used as "Количество обращений" in UI). */
  new_leads_count?: number;
  /** Unique patients who wrote to admins today (chat_messages: sender_type='patient'). */
  chat_writers_count?: number;
  revenue: string;
  empty_slot_hours?: number;
  day_pulse_score?: number;
}

export interface NoShowReport {
  date_from: string;
  date_to: string;
  total: number;
  no_show_count: number;
  no_show_rate: number;
}

export interface RevenueReport {
  date_from: string;
  date_to: string;
  total_revenue: string;
  points: { date: string; amount: string }[];
}

export interface OwnerDashboardReport {
  clinic_id: string;
  dashboard: DashboardReport;
  no_show_rate: number;
  total_revenue: string;
  prepayment_transactions_count: number;
  waitlist_entries_count: number;
  recall_campaigns_count: number;
}

export function useAdminReportsDashboard(
  clinicId: string | null,
  dateStr: string | null,
  period: "day" | "week" | "month" = "day"
) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "reports", "dashboard", dateStr, period],
    queryFn: () =>
      api.get<DashboardReport>(
        `/v1/admin/clinics/${clinicId}/reports/dashboard?date=${dateStr}&period=${period}`
      ),
    enabled: !!clinicId && !!dateStr,
  });
}

export function useAdminReportsDashboardAggregate(
  dateStr: string | null,
  period: "day" | "week" | "month" = "day"
) {
  return useQuery({
    queryKey: ["admin", "reports", "dashboard-aggregate", dateStr, period],
    queryFn: () =>
      api.get<DashboardReport>(
        `/v1/admin/reports/dashboard-aggregate?date=${dateStr}&period=${period}`
      ),
    enabled: !!dateStr,
  });
}

/**
 * Dashboard aggregate for selected clinics. Pass null or [] for "all clinics".
 */
export function useAdminReportsDashboardByClinics(
  dateStr: string | null,
  period: "day" | "week" | "month",
  clinicIds: string[] | null
) {
  const ids = clinicIds?.length ? clinicIds : null;
  return useQuery({
    queryKey: ["admin", "reports", "dashboard-aggregate", dateStr, period, ids?.slice().sort().join(",") ?? "all"],
    queryFn: () => {
      const params = new URLSearchParams({ date: dateStr!, period });
      if (ids?.length) params.set("clinic_ids", ids.join(","));
      return api.get<DashboardReport>(
        `/v1/admin/reports/dashboard-aggregate?${params.toString()}`
      );
    },
    enabled: !!dateStr,
  });
}

export function useAdminReportsNoShow(
  clinicId: string | null,
  dateFrom: string | null,
  dateTo: string | null
) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "reports", "no-show", dateFrom, dateTo],
    queryFn: () =>
      api.get<NoShowReport>(
        `/v1/admin/clinics/${clinicId}/reports/no-show?date_from=${dateFrom}&date_to=${dateTo}`
      ),
    enabled: !!clinicId && !!dateFrom && !!dateTo,
  });
}

export function useAdminReportsRevenue(
  clinicId: string | null,
  dateFrom: string | null,
  dateTo: string | null
) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "reports", "revenue", dateFrom, dateTo],
    queryFn: () =>
      api.get<RevenueReport>(
        `/v1/admin/clinics/${clinicId}/reports/revenue?date_from=${dateFrom}&date_to=${dateTo}`
      ),
    enabled: !!clinicId && !!dateFrom && !!dateTo,
  });
}

export function useOwnerDashboard(
  clinicId: string | null,
  dateStr: string | null,
  dateFrom: string | null,
  dateTo: string | null
) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "reports", "owner-dashboard", dateStr, dateFrom, dateTo],
    queryFn: () =>
      api.get<OwnerDashboardReport>(
        `/v1/admin/clinics/${clinicId}/reports/owner-dashboard?date=${dateStr}&date_from=${dateFrom}&date_to=${dateTo}`
      ),
    enabled: !!clinicId && !!dateStr && !!dateFrom && !!dateTo,
  });
}
