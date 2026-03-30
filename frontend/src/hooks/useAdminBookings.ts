import type { QueryKey } from "@tanstack/react-query";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Booking } from "@/api/types";

/** Response of GET /admin/bookings/{id}/checkout-info (Checkout Hub). */
export interface EligibleSubscriptionItem {
  customer_subscription_id: string;
  package_name: string;
  remaining_visits: number | null;
  remaining_amount: string | null;
}

export interface CheckoutInfoResponse {
  eligible_subscriptions: EligibleSubscriptionItem[];
}

export function useCheckoutInfo(bookingId: string | null) {
  return useQuery({
    queryKey: ["admin-bookings", "checkout-info", bookingId],
    queryFn: () =>
      api.get<CheckoutInfoResponse>(
        `/v1/admin/bookings/${bookingId}/checkout-info`
      ),
    enabled: !!bookingId,
  });
}

export interface AdminBookingsFilters {
  doctor_id?: string;
  date?: string;
  status?: string;
  patient_phone?: string;
  skip?: number;
  limit?: number;
}

export interface RescheduleBookingPayload {
  id: string;
  doctor_id: string;
  date: string;
  time: string;
}

export interface CreateAdminBookingPayload {
  clinic_id: string;
  patient_id: string;
  doctor_id: string;
  service_id: string;
  appointment_date: string;
  appointment_time: string;
  status?: string;
  prepayment_amount?: string;
  notes?: string;
}

export function useAdminBookings(filters: AdminBookingsFilters = {}) {
  const params = new URLSearchParams();
  if (filters.doctor_id) params.set("doctor_id", filters.doctor_id);
  if (filters.date) params.set("date", filters.date);
  if (filters.status) params.set("status", filters.status);
  if (filters.patient_phone) params.set("patient_phone", filters.patient_phone);
  if (filters.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  const query = params.toString();

  return useQuery({
    queryKey: ["admin-bookings", filters],
    queryFn: () =>
      api.get<Booking[]>(`/v1/admin/bookings${query ? `?${query}` : ""}`),
  });
}

export function useRescheduleBookingAdmin() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: RescheduleBookingPayload) =>
      api.put<Booking>(`/v1/admin/bookings/${payload.id}/reschedule`, {
        appointment_date: payload.date,
        appointment_time:
          payload.time.length === 5 ? `${payload.time}:00` : payload.time,
        to_doctor_id: payload.doctor_id,
      }),
    onMutate: async (payload) => {
      await queryClient.cancelQueries({ queryKey: ["admin-bookings"] });
      const previousBookings = queryClient.getQueriesData<Booking[]>({
        queryKey: ["admin-bookings"],
      });
      queryClient.setQueriesData<Booking[]>(
        { queryKey: ["admin-bookings"] },
        (list) =>
          list?.map((b) =>
            b.id === payload.id
              ? {
                  ...b,
                  appointment_date: payload.date,
                  appointment_time: payload.time,
                  doctor_id: payload.doctor_id,
                }
              : b,
          ) ?? list,
      );
      return { previousBookings };
    },
    onError: (_error, _variables, context) => {
      const previous = (context as { previousBookings?: [QueryKey, Booking[]][] })
        ?.previousBookings;
      if (previous) {
        previous.forEach(([key, data]) => queryClient.setQueryData(key, data));
      }
    },
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-bookings"] });
      queryClient.invalidateQueries({
        queryKey: ["schedule-admin", variables.doctor_id, variables.date],
      });
      queryClient.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}

export function useCreateAdminBooking() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload: CreateAdminBookingPayload) =>
      api.post<Booking>("/v1/admin/bookings", {
        clinic_id: payload.clinic_id,
        patient_id: payload.patient_id,
        doctor_id: payload.doctor_id,
        service_id: payload.service_id,
        appointment_date: payload.appointment_date,
        appointment_time: payload.appointment_time,
        status: payload.status ?? "pending",
        prepayment_amount: payload.prepayment_amount,
        notes: payload.notes,
      }),
    onSettled: (_data, _error, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-bookings"] });
      queryClient.invalidateQueries({
        queryKey: ["schedule-admin", variables.doctor_id, variables.appointment_date],
      });
      queryClient.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}

export interface PatchBookingAdminPayload {
  id: string;
  notes?: string | null;
  status?: string;
}

export function usePatchBookingAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, notes, status }: PatchBookingAdminPayload) => {
      const body: Record<string, unknown> = {};
      if (notes !== undefined) body.notes = notes;
      if (status !== undefined) body.status = status;
      return api.patch<Booking>(`/v1/admin/bookings/${id}`, body);
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-bookings"] });
      queryClient.invalidateQueries({ queryKey: ["admin-schedule"] });
      queryClient.invalidateQueries({ queryKey: ["reports-dashboard"] });
    },
  });
}

export function useCancelBookingAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.put<Booking>(`/v1/admin/bookings/${id}/cancel`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["admin-bookings"] });
      const previous = queryClient.getQueriesData<Booking[]>({
        queryKey: ["admin-bookings"],
      });
      queryClient.setQueriesData<Booking[]>(
        { queryKey: ["admin-bookings"] },
        (list) =>
          list?.map((b) =>
            b.id === id ? { ...b, status: "cancelled" as const } : b
          ) ?? list
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      const prev = (context as { previous?: [QueryKey, Booking[]][] })
        ?.previous;
      if (prev) {
        prev.forEach(([key, data]) => queryClient.setQueryData(key, data));
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-bookings"] });
      queryClient.invalidateQueries({ queryKey: ["reports-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}

export interface CompleteBookingPayload {
  bookingId: string;
  use_subscription_id?: string | null;
}

export function useCompleteBookingAdmin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ bookingId, use_subscription_id }: CompleteBookingPayload) =>
      api.put<Booking>(`/v1/admin/bookings/${bookingId}/complete`, {
        use_subscription_id: use_subscription_id ?? undefined,
      }),
    onMutate: async ({ bookingId }) => {
      await queryClient.cancelQueries({ queryKey: ["admin-bookings"] });
      const previous = queryClient.getQueriesData<Booking[]>({
        queryKey: ["admin-bookings"],
      });
      queryClient.setQueriesData<Booking[]>(
        { queryKey: ["admin-bookings"] },
        (list) =>
          list?.map((b) =>
            b.id === bookingId ? { ...b, status: "completed" as const } : b
          ) ?? list
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      const prev = (context as { previous?: [QueryKey, Booking[]][] })
        ?.previous;
      if (prev) {
        prev.forEach(([key, data]) => queryClient.setQueryData(key, data));
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-bookings"] });
      queryClient.invalidateQueries({ queryKey: ["reports-dashboard"] });
    },
  });
}
