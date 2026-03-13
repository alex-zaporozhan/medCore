import { useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AuthTokenResponse } from "@/api/types";

export interface AgreementSettings {
  clinic_id: string;
  pd_agreement_text: string | null;
  allow_registration_without_mailing_consent: boolean;
}

export function useAgreement() {
  return useQuery({
    queryKey: ["auth", "agreement"],
    queryFn: () => api.get<AgreementSettings>("/v1/auth/agreement"),
  });
}

export function useSendCode() {
  return useMutation({
    mutationFn: (phone: string) =>
      api.post<undefined>("/v1/auth/send-code", { phone }),
  });
}

export function useVerifyCode() {
  return useMutation({
    mutationFn: (body: {
      phone: string;
      code: string;
      consent_pd: boolean;
      consent_mailing: boolean;
      full_name?: string | null;
      birth_date?: string | null;
    }) => api.post<AuthTokenResponse>("/v1/auth/verify-code", body),
  });
}
