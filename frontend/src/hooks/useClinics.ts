import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Clinic } from "@/api/types";

export function useClinics(includeDeleted = false) {
  const query = includeDeleted ? "?include_deleted=true" : "";

  return useQuery({
    queryKey: ["clinics", { includeDeleted }],
    queryFn: () => api.get<Clinic[]>(`/v1/clinics${query}`),
  });
}

