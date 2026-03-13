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
  revenue: string;
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
