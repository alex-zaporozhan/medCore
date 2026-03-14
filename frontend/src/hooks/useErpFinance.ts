import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Cashbox, FinancialTransaction } from "@/api/types";

export function useCashboxes(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "finance", "cashboxes"],
    queryFn: () =>
      api.get<Cashbox[]>(`/v1/admin/clinics/${clinicId}/finance/cashboxes`),
    enabled: !!clinicId,
  });
}

export interface FinanceTransactionsFilters {
  cashbox_id?: string | null;
  type?: string | null;
  date_from?: string | null;
  date_to?: string | null;
}

export function useFinanceTransactions(
  clinicId: string | null,
  filters: FinanceTransactionsFilters
) {
  const params = new URLSearchParams();
  if (filters.cashbox_id) params.set("cashbox_id", filters.cashbox_id);
  if (filters.type) params.set("type_filter", filters.type);
  if (filters.date_from) params.set("date_from", filters.date_from);
  if (filters.date_to) params.set("date_to", filters.date_to);

  const qs = params.toString();

  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "finance", "transactions", qs],
    queryFn: () =>
      api.get<FinancialTransaction[]>(
        `/v1/admin/clinics/${clinicId}/finance/transactions${qs ? `?${qs}` : ""}`
      ),
    enabled: !!clinicId,
  });
}

