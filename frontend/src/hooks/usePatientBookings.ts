import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Booking } from "@/api/types";

export function usePatientBookings(patientId: string | null, token: string | null) {
  return useQuery({
    queryKey: ["patient-bookings", patientId],
    queryFn: () =>
      api.get<Booking[]>(
        `/v1/patient/bookings?patient_id=${patientId}`,
        token
      ),
    enabled: !!patientId && !!token,
  });
}

export function useCreatePatientBooking(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      patientId,
      body,
    }: {
      patientId: string;
      body: {
        clinic_id: string;
        doctor_id: string;
        service_id: string;
        appointment_date: string;
        appointment_time: string;
        notes?: string;
      };
    }) =>
      api.post<Booking>(
        `/v1/patient/bookings?patient_id=${patientId}`,
        body,
        token
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patient-bookings"] });
    },
  });
}

export function useCancelPatientBooking(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      bookingId,
      patientId,
    }: { bookingId: string; patientId: string }) =>
      api.delete<Booking>(
        `/v1/patient/bookings/${bookingId}?patient_id=${patientId}`,
        token
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patient-bookings"] });
    },
  });
}
