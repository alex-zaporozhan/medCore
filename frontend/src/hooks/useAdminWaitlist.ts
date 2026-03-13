import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface WaitlistEntryRead {
  id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string | null;
  speciality: string | null;
  time_preferences_json: Record<string, unknown> | null;
  preferred_date: string | null;
  preferred_time: string | null;
  priority: number;
  status: string;
}

/** Alias for compatibility with WaitlistPanel */
export type WaitlistEntry = WaitlistEntryRead;

export interface WaitlistEntryCreate {
  clinic_id: string;
  patient_id: string;
  doctor_id?: string | null;
  speciality?: string | null;
  time_preferences_json?: Record<string, unknown> | null;
  preferred_date?: string | null;
  preferred_time?: string | null;
  priority?: number;
  status?: string;
}

export interface WaitlistEntryUpdate {
  patient_id?: string;
  doctor_id?: string | null;
  speciality?: string | null;
  time_preferences_json?: Record<string, unknown> | null;
  preferred_date?: string | null;
  preferred_time?: string | null;
  priority?: number;
  status?: string;
}

export interface QueuePolicyRead {
  id: string;
  clinic_id: string;
  mode: string;
  broadcast_size: number;
  response_timeout_minutes: number;
  max_notifications_per_entry: number | null;
}

export interface QueuePolicyUpdate {
  mode?: string;
  broadcast_size?: number;
  response_timeout_minutes?: number;
  max_notifications_per_entry?: number | null;
}

export function useAdminWaitlistEntries(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "waitlist"],
    queryFn: () =>
      api.get<WaitlistEntryRead[]>(`/v1/admin/clinics/${clinicId}/waitlist`),
    enabled: !!clinicId,
  });
}

export function useCreateWaitlistEntry(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: WaitlistEntryCreate) =>
      api.post<WaitlistEntryRead>(
        `/v1/admin/clinics/${clinicId}/waitlist`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "waitlist"],
      }),
  });
}

export function useUpdateWaitlistEntry(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      entryId,
      body,
    }: {
      entryId: string;
      body: WaitlistEntryUpdate;
    }) =>
      api.put<WaitlistEntryRead>(
        `/v1/admin/clinics/${clinicId}/waitlist/${entryId}`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "waitlist"],
      }),
  });
}

export function useDeleteWaitlistEntry(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (entryId: string) =>
      api.delete(`/v1/admin/clinics/${clinicId}/waitlist/${entryId}`),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "waitlist"],
      }),
  });
}

export function useAdminQueuePolicy(clinicId: string | null) {
  return useQuery({
    queryKey: ["admin", "clinics", clinicId, "queue-policy"],
    queryFn: () =>
      api.get<QueuePolicyRead | null>(
        `/v1/admin/clinics/${clinicId}/queue-policy`
      ),
    enabled: !!clinicId,
  });
}

export function useUpsertQueuePolicy(clinicId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: QueuePolicyUpdate) =>
      api.put<QueuePolicyRead>(
        `/v1/admin/clinics/${clinicId}/queue-policy`,
        body
      ),
    onSuccess: () =>
      qc.invalidateQueries({
        queryKey: ["admin", "clinics", clinicId, "queue-policy"],
      }),
  });
}

/** Entries for schedule panel: filter by doctor (and optional date). */
export function useAdminWaitlist(
  clinicId: string | null,
  doctorId: string | null,
  _date: string | null
) {
  const q = useAdminWaitlistEntries(clinicId);
  const filtered =
    q.data?.filter(
      (e) =>
        (!doctorId || e.doctor_id === doctorId || e.doctor_id === null)
    ) ?? [];
  return { ...q, data: filtered };
}

export function useCancelWaitlistEntry(clinicId: string | null) {
  return useDeleteWaitlistEntry(clinicId);
}
