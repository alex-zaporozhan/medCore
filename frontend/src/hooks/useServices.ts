import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Service } from "@/api/types";

interface UseServicesFilters {
  clinic_id?: string;
  category?: string;
  skip?: number;
  limit?: number;
}

export function useServices(filters: UseServicesFilters = {}) {
  const params = new URLSearchParams();
  if (filters.clinic_id) params.set("clinic_id", filters.clinic_id);
  if (filters.category) params.set("category", filters.category);
  if (filters.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  const query = params.toString();

  return useQuery({
    queryKey: ["services", filters],
    queryFn: () => api.get<Service[]>(`/v1/services${query ? `?${query}` : ""}`),
  });
}

export function useService(id: string | null) {
  return useQuery({
    queryKey: ["service", id],
    queryFn: () => api.get<Service>(`/v1/services/${id}`),
    enabled: !!id,
  });
}
