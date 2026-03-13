import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Service } from "@/api/types";

interface ServiceCreate {
  clinic_id: string;
  name: string;
  category: string;
  description?: string | null;
  price: string | number;
  duration_minutes?: number;
  is_active?: boolean;
}

interface ServiceUpdate extends Partial<Omit<ServiceCreate, "clinic_id">> {}

export function useCreateService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ServiceCreate) => api.post<Service>("/v1/services", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
    },
  });
}

export function useUpdateService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: ServiceUpdate }) =>
      api.put<Service>(`/v1/services/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
    },
  });
}

export function useDeleteService() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<unknown>(`/v1/services/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["services"] });
    },
  });
}
