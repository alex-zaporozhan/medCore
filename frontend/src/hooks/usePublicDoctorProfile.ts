import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { PublicDoctorProfilePublicDto } from "@/api/types";

export function usePublicDoctorProfileBySlugs(
  clinicSlug: string | null,
  doctorSlug: string | null
) {
  return useQuery({
    queryKey: ["public", "doctorProfile", clinicSlug, doctorSlug],
    enabled: Boolean(clinicSlug && doctorSlug),
    queryFn: () =>
      api.get<PublicDoctorProfilePublicDto>(
        `/v1/public/clinics/by-slug/${encodeURIComponent(
          clinicSlug ?? ""
        )}/doctors/${encodeURIComponent(doctorSlug ?? "")}`
      ),
  });
}

