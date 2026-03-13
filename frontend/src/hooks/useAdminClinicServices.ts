import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AdminServiceRead } from "@/api/types";

export function useAdminClinicServices(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "services"],
    queryFn: () =>
      api.get<AdminServiceRead[]>(`/v1/admin/clinics/${clinicId}/services`),
    enabled: !!clinicId,
  });
}

interface ServiceCreatePayload {
  service: {
    clinic_id: string;
    name: string;
    category: string;
    description?: string | null;
    price: string | number;
    duration_minutes?: number;
    is_active?: boolean;
  };
  doctors: { doctor_id: string; custom_price?: string | null; is_active?: boolean }[];
}

interface ServiceUpdatePayload {
  service: {
    name?: string;
    category?: string;
    description?: string | null;
    price?: string | number;
    duration_minutes?: number;
    is_active?: boolean;
  };
  doctors: { doctor_id: string; custom_price?: string | null; is_active?: boolean }[];
}

export function useCreateAdminClinicService(clinicId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ServiceCreatePayload) =>
      api.post<AdminServiceRead>(`/v1/admin/clinics/${clinicId}/services`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "services"],
      });
    },
  });
}

export function useUpdateAdminClinicService(clinicId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      serviceId,
      body,
    }: {
      serviceId: string;
      body: ServiceUpdatePayload;
    }) =>
      api.put<AdminServiceRead>(
        `/v1/admin/clinics/${clinicId}/services/${serviceId}`,
        body
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "services"],
      });
    },
  });
}

export function useDeleteAdminClinicService(clinicId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (serviceId: string) =>
      api.delete<unknown>(`/v1/admin/clinics/${clinicId}/services/${serviceId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "services"],
      });
    },
  });
}
