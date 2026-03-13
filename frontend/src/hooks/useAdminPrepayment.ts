import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface PrepaymentPolicyRead {
  id: string;
  clinic_id: string;
  scope_type: string;
  scope_doctor_id: string | null;
  scope_service_id: string | null;
  mode: string;
  amount_type: string;
  min_amount: string;
  deadline_hours_before_visit: number | null;
  priority: number;
  enabled: boolean;
}

export interface PrepaymentPolicyCreate {
  clinic_id: string;
  scope_type: string;
  scope_doctor_id?: string | null;
  scope_service_id?: string | null;
  mode: string;
  amount_type: string;
  min_amount?: string | number;
  deadline_hours_before_visit?: number | null;
  priority?: number;
  enabled?: boolean;
}

export interface PrepaymentPolicyUpdate {
  scope_type?: string;
  scope_doctor_id?: string | null;
  scope_service_id?: string | null;
  mode?: string;
  amount_type?: string;
  min_amount?: string | number;
  deadline_hours_before_visit?: number | null;
  priority?: number;
  enabled?: boolean;
}

export function useAdminPrepaymentPolicies(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "prepayment", "policies"],
    queryFn: () =>
      api.get<PrepaymentPolicyRead[]>(
        `/v1/admin/clinics/${clinicId}/prepayment/policies`
      ),
    enabled: !!clinicId,
  });
}

export function useCreatePrepaymentPolicy(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: PrepaymentPolicyCreate) =>
      api.post<PrepaymentPolicyRead>(
        `/v1/admin/clinics/${clinicId}/prepayment/policies`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "prepayment", "policies"],
      }),
  });
}

export function useUpdatePrepaymentPolicy(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      policyId,
      body,
    }: {
      policyId: string;
      body: PrepaymentPolicyUpdate;
    }) =>
      api.put<PrepaymentPolicyRead>(
        `/v1/admin/clinics/${clinicId}/prepayment/policies/${policyId}`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "prepayment", "policies"],
      }),
  });
}

export function useDeletePrepaymentPolicy(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (policyId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/prepayment/policies/${policyId}`),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "prepayment", "policies"],
      }),
  });
}
