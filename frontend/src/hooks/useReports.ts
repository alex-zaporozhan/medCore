import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  DashboardReport,
  NoShowReport,
  RevenueReport,
} from "@/api/types";

export function useReportsDashboard(date: string | null, period: "day" | "week" | "month" = "day") {
  return useQuery({
    queryKey: ["reports-dashboard", date, period],
    queryFn: () =>
      api.get<DashboardReport>(
        `/v1/reports/dashboard?date=${date}&period=${period}`
      ),
    enabled: !!date,
  });
}

export function useReportsNoShow(dateFrom: string | null, dateTo: string | null) {
  return useQuery({
    queryKey: ["reports-no-show", dateFrom, dateTo],
    queryFn: () =>
      api.get<NoShowReport>(
        `/v1/reports/no-show?date_from=${dateFrom}&date_to=${dateTo}`
      ),
    enabled: !!dateFrom && !!dateTo,
  });
}

export function useReportsRevenue(dateFrom: string | null, dateTo: string | null) {
  return useQuery({
    queryKey: ["reports-revenue", dateFrom, dateTo],
    queryFn: () =>
      api.get<RevenueReport>(
        `/v1/reports/revenue?date_from=${dateFrom}&date_to=${dateTo}`
      ),
    enabled: !!dateFrom && !!dateTo,
  });
}
