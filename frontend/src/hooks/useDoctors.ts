import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Doctor } from "@/api/types";

interface UseDoctorsFilters {
  is_active?: boolean;
  clinic_id?: string;
  skip?: number;
  limit?: number;
}

export function useDoctors(filters: UseDoctorsFilters = {}) {
  const params = new URLSearchParams();
  if (filters.is_active !== undefined) params.set("is_active", String(filters.is_active));
  if (filters.clinic_id) params.set("clinic_id", filters.clinic_id);
  if (filters.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  const query = params.toString();

  return useQuery({
    queryKey: ["doctors", filters],
    queryFn: () => api.get<Doctor[]>(`/v1/doctors${query ? `?${query}` : ""}`),
  });
}

export function useDoctor(id: string | null) {
  return useQuery({
    queryKey: ["doctor", id],
    queryFn: () => api.get<Doctor>(`/v1/doctors/${id}`),
    enabled: !!id,
  });
}
