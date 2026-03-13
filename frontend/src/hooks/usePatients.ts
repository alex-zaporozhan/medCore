import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Patient } from "@/api/types";

interface UsePatientsFilters {
  phone?: string;
  full_name?: string;
  clinic_id?: string;
  skip?: number;
  limit?: number;
}

export function usePatients(filters: UsePatientsFilters = {}) {
  const params = new URLSearchParams();
  if (filters.clinic_id) params.set("clinic_id", filters.clinic_id);
  if (filters.phone) params.set("phone", filters.phone);
  if (filters.full_name) params.set("full_name", filters.full_name);
  if (filters.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  const query = params.toString();

  return useQuery({
    queryKey: ["patients", filters],
    queryFn: () => api.get<Patient[]>(`/v1/patients${query ? `?${query}` : ""}`),
  });
}
