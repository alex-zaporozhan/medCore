import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { AggregatedSchedule, DailySchedule } from "@/api/types";

export function useDoctorSchedule(doctorId: string | null, date: string | null) {
  return useQuery({
    queryKey: ["schedule", doctorId, date],
    queryFn: () =>
      api.get<DailySchedule>(
        `/v1/doctors/${doctorId}/schedule?date=${date}`
      ),
    enabled: !!doctorId && !!date,
  });
}

export function useDoctorScheduleAdmin(doctorId: string | null, date: string | null) {
  return useQuery({
    queryKey: ["schedule-admin", doctorId, date],
    queryFn: () =>
      api.get<DailySchedule>(
        `/v1/doctors/admin/${doctorId}/schedule?date=${date}`
      ),
    enabled: !!doctorId && !!date,
  });
}

export function useAdminSchedule(
  clinicId: string | null,
  doctorIds: string[],
  date: string | null
) {
  const ids = doctorIds.filter(Boolean);
  return useQuery({
    queryKey: ["admin-schedule", clinicId, ids.join(","), date],
    queryFn: () => {
      const params = new URLSearchParams();
      params.set("date", date ?? "");
      params.set("doctor_ids", ids.join(","));
      return api.get<AggregatedSchedule>(
        `/v1/admin/clinics/${clinicId}/schedule?${params.toString()}`
      );
    },
    enabled: !!clinicId && ids.length > 0 && !!date,
  });
}
