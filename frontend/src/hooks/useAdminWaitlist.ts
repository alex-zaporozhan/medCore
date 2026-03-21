import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface WaitlistEntryRead {
  id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string | null;
  preferred_service_id: string | null;
  speciality: string | null;
  time_preferences_json: Record<string, unknown> | null;
  preferred_date: string | null;
  preferred_time: string | null;
  priority: number;
  status: string;
  source: string | null;
  notes: string | null;
  booking_id: string | null;
  created_by_id: string | null;
  updated_by_id: string | null;
}

/** Alias for compatibility with WaitlistPanel */
export type WaitlistEntry = WaitlistEntryRead;

export interface WaitlistEntryCreate {
  clinic_id: string;
  patient_id: string;
  doctor_id?: string | null;
  preferred_service_id?: string | null;
  speciality?: string | null;
  time_preferences_json?: Record<string, unknown> | null;
  preferred_date?: string | null;
  preferred_time?: string | null;
  priority?: number;
  status?: string;
  source?: string | null;
  notes?: string | null;
}

export interface WaitlistEntryUpdate {
  patient_id?: string;
  doctor_id?: string | null;
  preferred_service_id?: string | null;
  speciality?: string | null;
  time_preferences_json?: Record<string, unknown> | null;
  preferred_date?: string | null;
  preferred_time?: string | null;
  priority?: number;
  status?: string;
  source?: string | null;
  notes?: string | null;
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

export type AdminWaitlistListOptions = {
  /** When true, include rows already linked to a booking (default true for admin list page). */
  includeBooked?: boolean;
  includeInactive?: boolean;
};

function waitlistQueryString(options?: AdminWaitlistListOptions): string {
  const includeBooked = options?.includeBooked ?? true;
  const includeInactive = options?.includeInactive ?? false;
  const qs = new URLSearchParams();
  if (includeInactive) qs.set("include_inactive", "true");
  if (includeBooked) qs.set("include_booked", "true");
  const s = qs.toString();
  return s ? `?${s}` : "";
}

export function useAdminWaitlistEntries(
  clinicId: string | null,
  options?: AdminWaitlistListOptions
) {
  const includeBooked = options?.includeBooked ?? true;
  const includeInactive = options?.includeInactive ?? false;
  return useQuery({
    queryKey: [
      "admin",
      "clinics",
      clinicId,
      "waitlist",
      { includeBooked, includeInactive },
    ],
    queryFn: () =>
      api.get<WaitlistEntryRead[]>(
        `/v1/admin/clinics/${clinicId}/waitlist${waitlistQueryString(options)}`
      ),
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

/** Entries for schedule panel: filter by doctor (and optional date). Active queue only (no booked). */
export function useAdminWaitlist(
  clinicId: string | null,
  doctorId: string | null,
  _date: string | null
) {
  const q = useAdminWaitlistEntries(clinicId, { includeBooked: false });
  const filtered =
    q.data?.filter(
      (e) =>
        !doctorId || e.doctor_id === doctorId || e.doctor_id === null
    ) ?? [];
  return { ...q, data: filtered };
}

export function useCancelWaitlistEntry(clinicId: string | null) {
  return useDeleteWaitlistEntry(clinicId);
}
