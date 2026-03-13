import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { CreatePaymentResponse } from "@/api/types";

export function useCreatePayment(token: string | null) {
  return useMutation({
    mutationFn: (params: { bookingId: string; gatewayId?: string }) =>
      api.post<CreatePaymentResponse>(
        "/v1/payments",
        {
          booking_id: params.bookingId,
          ...(params.gatewayId ? { gateway_id: params.gatewayId } : {}),
        },
        token
      ),
  });
}
