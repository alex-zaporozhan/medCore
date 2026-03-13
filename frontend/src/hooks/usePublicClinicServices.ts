import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { PublicService } from "@/api/types";

export function usePublicClinicServices(clinicId: string | null) {
  return useQuery({
    queryKey: ["public", "clinics", clinicId, "services"],
    queryFn: () =>
      api.get<PublicService[]>(`/v1/public/clinics/${clinicId}/services`),
    enabled: !!clinicId,
  });
}
