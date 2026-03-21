import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface DiscountRead {
  id: string;
  clinic_id: string;
  name: string;
  discount_type: string;
  service_id: string | null;
  doctor_id: string | null;
  valid_from: string | null;
  valid_until: string | null;
  percent_off: string | null;
  amount_off: string | null;
  is_active: boolean;
}

export interface DiscountCreate {
  name: string;
  discount_type: "first_visit" | "service" | "doctor" | "period";
  service_id?: string | null;
  doctor_id?: string | null;
  valid_from?: string | null;
  valid_until?: string | null;
  percent_off?: number | string | null;
  amount_off?: number | string | null;
  is_active?: boolean;
}

export function useAdminDiscounts(clinicId: string | null) {
  return useQuery({
    queryKey: queryKeys.adminDiscounts(clinicId),
    queryFn: () => api.get<DiscountRead[]>(`/v1/admin/clinics/${clinicId}/discounts`),
    enabled: !!clinicId,
  });
}

export function useCreateAdminDiscountMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: DiscountCreate) =>
      api.post<DiscountRead>(`/v1/admin/clinics/${clinicId}/discounts`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.adminDiscounts(clinicId) });
    },
  });
}

export function useUpdateAdminDiscountMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<DiscountCreate> }) =>
      api.put<DiscountRead>(`/v1/admin/clinics/${clinicId}/discounts/${id}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.adminDiscounts(clinicId) });
    },
  });
}

export function useDeleteAdminDiscountMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/discounts/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.adminDiscounts(clinicId) });
    },
  });
}
