import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, API_BASE } from "@/api/client";

export interface PatientMedicalVisitDto {
  id: string;
  clinic_id: string;
  patient_id: string;
  doctor_id: string | null;
  booking_id: string | null;
  visit_date: string;
  notes_md: string | null;
  created_by_admin_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientDiagnosisDto {
  id: string;
  clinic_id: string;
  patient_id: string;
  visit_id: string | null;
  diagnosis_date: string;
  icd10_code: string | null;
  title: string;
  description: string | null;
  author_admin_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface PatientMedicalFileDto {
  id: string;
  clinic_id: string;
  patient_id: string;
  visit_id: string | null;
  file_name: string;
  content_type: string;
  size_bytes: number;
  sha256: string | null;
  created_at: string;
}

export function useAdminPatientMedicalVisits(clinicId: string | null, patientId: string | null) {
  return useQuery({
    queryKey: ["admin", "patientMedical", "visits", clinicId, patientId],
    enabled: Boolean(clinicId && patientId),
    queryFn: () =>
      api.get<PatientMedicalVisitDto[]>(
        `/v1/admin/clinics/${clinicId}/patients/${patientId}/medical/visits`
      ),
  });
}

export function useCreateAdminPatientMedicalVisit(clinicId: string, patientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<PatientMedicalVisitDto>(
        `/v1/admin/clinics/${clinicId}/patients/${patientId}/medical/visits`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "patientMedical"] });
    },
  });
}

export function useAdminPatientDiagnoses(clinicId: string | null, patientId: string | null) {
  return useQuery({
    queryKey: ["admin", "patientMedical", "diagnoses", clinicId, patientId],
    enabled: Boolean(clinicId && patientId),
    queryFn: () =>
      api.get<PatientDiagnosisDto[]>(
        `/v1/admin/clinics/${clinicId}/patients/${patientId}/medical/diagnoses`
      ),
  });
}

export function useCreateAdminPatientDiagnosis(clinicId: string, patientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Record<string, unknown>) =>
      api.post<PatientDiagnosisDto>(
        `/v1/admin/clinics/${clinicId}/patients/${patientId}/medical/diagnoses`,
        body
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "patientMedical"] });
    },
  });
}

export function useAdminPatientMedicalFiles(clinicId: string | null, patientId: string | null) {
  return useQuery({
    queryKey: ["admin", "patientMedical", "files", clinicId, patientId],
    enabled: Boolean(clinicId && patientId),
    queryFn: () =>
      api.get<PatientMedicalFileDto[]>(
        `/v1/admin/clinics/${clinicId}/patients/${patientId}/medical/files`
      ),
  });
}

export function useUploadAdminPatientMedicalFile(clinicId: string, patientId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ file, visitId }: { file: File; visitId?: string | null }) => {
      const fd = new FormData();
      fd.append("file", file);
      const qs = visitId ? `?visit_id=${encodeURIComponent(visitId)}` : "";
      return api.post<PatientMedicalFileDto>(
        `/v1/admin/clinics/${clinicId}/patients/${patientId}/medical/files:upload${qs}`,
        fd
      );
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "patientMedical"] });
    },
  });
}

export async function fetchAdminPatientMedicalFileDownloadUrl(opts: {
  clinicId: string;
  patientId: string;
  fileId: string;
}): Promise<string> {
  const res = await api.post<{ token: string; expires_in_seconds: number }>(
    `/v1/admin/clinics/${opts.clinicId}/patients/${opts.patientId}/medical/files/${opts.fileId}:download-token`,
    {}
  );
  return `${API_BASE}/v1/admin/clinics/${opts.clinicId}/patients/${opts.patientId}/medical/files/${opts.fileId}:stream?token=${encodeURIComponent(
    res.token
  )}`;
}

