import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { PublicDoctorProfile } from "@/api/types";

export function useAdminPublicDoctorProfileByDoctor(
  clinicId: string | null,
  doctorId: string | null
) {
  return useQuery({
    queryKey: ["admin", "publicDoctorProfiles", "byDoctor", clinicId, doctorId],
    enabled: Boolean(clinicId && doctorId),
    queryFn: async () => {
      const items = await api.get<PublicDoctorProfile[]>(
        `/v1/admin/clinics/${clinicId}/public-doctor-profiles?doctor_id=${encodeURIComponent(
          doctorId ?? ""
        )}`
      );
      return items[0] ?? null;
    },
  });
}

export function useCreateAdminPublicDoctorProfileMutation(clinicId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<PublicDoctorProfile>(`/v1/admin/clinics/${clinicId}/public-doctor-profiles`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "publicDoctorProfiles"] });
    },
  });
}

export function usePatchAdminPublicDoctorProfileMutation(clinicId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ profileId, body }: { profileId: string; body: Record<string, unknown> }) =>
      api.patch<PublicDoctorProfile>(
        `/v1/admin/clinics/${clinicId}/public-doctor-profiles/${profileId}`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "publicDoctorProfiles"] });
    },
  });
}

