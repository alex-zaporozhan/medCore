import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface AgreementSettings {
  clinic_id: string;
  pd_agreement_text: string | null;
  allow_registration_without_mailing_consent: boolean;
}

export function useAdminAgreementSettings(clinicId: string | null) {
  return useQuery({
    queryKey: queryKeys.agreementSettings(clinicId),
    queryFn: () =>
      api.get<AgreementSettings>(`/v1/admin/clinics/${clinicId}/agreement-settings`),
    enabled: !!clinicId,
  });
}

export function useUpdateAdminAgreementSettingsMutation(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      pd_agreement_text: string | null;
      allow_registration_without_mailing_consent: boolean;
    }) =>
      api.put<AgreementSettings>(
        `/v1/admin/clinics/${clinicId}/agreement-settings`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.agreementSettings(clinicId) });
    },
  });
}
