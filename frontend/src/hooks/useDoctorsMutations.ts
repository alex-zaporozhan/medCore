import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Doctor } from "@/api/types";

interface DoctorCreate {
  full_name: string;
  specialization: string;
  photo_url?: string | null;
  rating?: string | number;
  experience_years?: number | null;
  is_active?: boolean;
  specialist_role?: string;
  specialist_role_custom_name?: string | null;
}

interface DoctorUpdate extends Partial<DoctorCreate> {}

export function useCreateDoctor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: DoctorCreate) =>
      api.post<Doctor>("/v1/doctors", body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
    },
  });
}

export function useUpdateDoctor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: DoctorUpdate }) =>
      api.put<Doctor>(`/v1/doctors/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
    },
  });
}

export function useDeleteDoctor() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<unknown>(`/v1/doctors/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["doctors"] });
    },
  });
}
