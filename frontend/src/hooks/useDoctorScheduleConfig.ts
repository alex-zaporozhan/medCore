import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface WorkingHoursRead {
  id: string;
  doctor_id: string;
  weekday: number;
  start_time: string;
  end_time: string;
}

export interface WorkingHoursCreate {
  weekday: number;
  start_time: string;
  end_time: string;
}

export interface WorkingHoursUpdate {
  start_time?: string;
  end_time?: string;
}

export interface AbsenceRead {
  id: string;
  doctor_id: string;
  date_from: string;
  date_to: string;
  reason: string | null;
}

export interface AbsenceCreate {
  date_from: string;
  date_to: string;
  reason?: string | null;
}

const workingHoursQueryKey = (doctorId: string) =>
  ["admin", "doctor-schedule", doctorId, "working-hours"] as const;
const absenceQueryKey = (doctorId: string) =>
  ["admin", "doctor-schedule", doctorId, "absence"] as const;

export function useWorkingHours(doctorId: string | null) {
  return useQuery({
    queryKey: workingHoursQueryKey(doctorId ?? ""),
    queryFn: () =>
      api.get<WorkingHoursRead[]>(
        `/v1/admin/doctors/${doctorId}/working-hours`
      ),
    enabled: !!doctorId,
  });
}

export function useCreateOrUpdateWorkingHours(doctorId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WorkingHoursCreate) =>
      api.post<WorkingHoursRead>(
        `/v1/admin/doctors/${doctorId}/working-hours`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workingHoursQueryKey(doctorId) });
      qc.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}

export function useUpdateWorkingHours(doctorId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      whId,
      body,
    }: {
      whId: string;
      body: WorkingHoursUpdate;
    }) =>
      api.put<WorkingHoursRead>(
        `/v1/admin/doctors/${doctorId}/working-hours/${whId}`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workingHoursQueryKey(doctorId) });
      qc.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}

export function useDeleteWorkingHours(doctorId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (whId: string) =>
      api.delete(`/v1/admin/doctors/${doctorId}/working-hours/${whId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: workingHoursQueryKey(doctorId) });
      qc.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}

export function useAbsence(doctorId: string | null) {
  return useQuery({
    queryKey: absenceQueryKey(doctorId ?? ""),
    queryFn: () =>
      api.get<AbsenceRead[]>(`/v1/admin/doctors/${doctorId}/absence`),
    enabled: !!doctorId,
  });
}

export function useCreateAbsence(doctorId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: AbsenceCreate) =>
      api.post<AbsenceRead>(`/v1/admin/doctors/${doctorId}/absence`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: absenceQueryKey(doctorId) });
      qc.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}

export function useDeleteAbsence(doctorId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (absenceId: string) =>
      api.delete(`/v1/admin/doctors/${doctorId}/absence/${absenceId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: absenceQueryKey(doctorId) });
      qc.invalidateQueries({ queryKey: ["admin-schedule"] });
    },
  });
}
