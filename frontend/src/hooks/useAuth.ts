import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AuthTokenResponse } from "@/api/types";
import { usePatientEntry } from "@/contexts/PatientEntryContext";

export interface AgreementSettings {
  clinic_id: string;
  pd_agreement_text: string | null;
  allow_registration_without_mailing_consent: boolean;
}

export function useAgreement() {
  const { clinicSlug } = usePatientEntry();
  return useQuery({
    queryKey: ["auth", "agreement", clinicSlug],
    queryFn: () => {
      const q = clinicSlug ? `?clinic_slug=${encodeURIComponent(clinicSlug)}` : "";
      return api.get<AgreementSettings>(`/v1/auth/agreement${q}`);
    },
  });
}

export function useSendCode() {
  const { clinicSlug } = usePatientEntry();
  return useMutation({
    mutationFn: (phone: string) =>
      api.post<undefined>("/v1/auth/send-code", {
        phone,
        clinic_slug: clinicSlug ?? undefined,
      }),
  });
}

export function useVerifyCode() {
  const { clinicSlug } = usePatientEntry();
  return useMutation({
    mutationFn: (body: {
      phone: string;
      code: string;
      consent_pd: boolean;
      consent_mailing: boolean;
      full_name?: string | null;
      birth_date?: string | null;
      session_id?: string | null;
      utm_source?: string | null;
      utm_medium?: string | null;
      utm_campaign?: string | null;
      utm_content?: string | null;
      utm_term?: string | null;
      landing_page?: string | null;
      anchor?: string | null;
    }) =>
      api.post<AuthTokenResponse>("/v1/auth/verify-code", {
        ...body,
        clinic_slug: clinicSlug ?? undefined,
      }),
  });
}
