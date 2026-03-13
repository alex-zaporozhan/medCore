import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface SetClinicPaymentGatewayCredentialsRequest {
  gateway: string;
  payload: string;
}

export function useSetClinicPaymentGatewayCredentials(clinicId: string | null) {
  return useMutation({
    mutationFn: (body: SetClinicPaymentGatewayCredentialsRequest) => {
      if (!clinicId) {
        return Promise.reject(new Error("clinicId is required"));
      }
      return api.post<void>(
        `/v1/admin/clinics/${clinicId}/payment-gateway/credentials`,
        body
      );
    },
  });
}

