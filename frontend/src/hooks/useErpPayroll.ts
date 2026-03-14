import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { PayrollPolicy, SalaryTransaction } from "@/api/types";

export function usePayrollPolicies(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "payroll", "policies"],
    queryFn: () =>
      api.get<PayrollPolicy[]>(`/v1/admin/clinics/${clinicId}/payroll/policies`),
    enabled: !!clinicId,
  });
}

export function useSalaryTransactions(
  clinicId: string | null,
  doctorId: string | null,
  periodStart: string | null,
  periodEnd: string | null
) {
  const params = new URLSearchParams();
  if (doctorId) params.set("doctor_id", doctorId);
  if (periodStart) params.set("period_start", periodStart);
  if (periodEnd) params.set("period_end", periodEnd);
  const qs = params.toString();

  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "payroll", "transactions", qs],
    queryFn: () =>
      api.get<SalaryTransaction[]>(
        `/v1/admin/clinics/${clinicId}/payroll/transactions${qs ? `?${qs}` : ""}`
      ),
    enabled: !!clinicId && !!doctorId,
  });
}

