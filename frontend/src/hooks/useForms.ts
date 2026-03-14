import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  DigitalFormSubmissionWithTemplateAndSignature,
  DigitalFormSubmissionListItem,
  DigitalFormTemplate,
  DigitalFormSubmission,
} from "@/api/types";

export function useAdminFormTemplates() {
  return useQuery({
    queryKey: ["admin", "forms", "templates"],
    queryFn: () => api.get<DigitalFormTemplate[]>("/v1/admin/forms/templates"),
  });
}

export function useAdminFormSubmissions(params: {
  patient_id?: string | null;
  booking_id?: string | null;
  template_code?: string | null;
}) {
  const searchParams = new URLSearchParams();
  if (params.patient_id) searchParams.set("patient_id", params.patient_id);
  if (params.booking_id) searchParams.set("booking_id", params.booking_id);
  if (params.template_code) searchParams.set("template_code", params.template_code);

  return useQuery({
    queryKey: ["admin", "forms", "submissions", params],
    queryFn: () =>
      api.get<DigitalFormSubmissionListItem[]>(
        `/v1/admin/forms/submissions${searchParams.toString() ? `?${searchParams.toString()}` : ""}`
      ),
  });
}

export function useAdminFormSubmissionDetail(submissionId: string | null) {
  return useQuery({
    queryKey: ["admin", "forms", "submission", submissionId],
    queryFn: () =>
      api.get<DigitalFormSubmissionWithTemplateAndSignature>(
        `/v1/admin/forms/submissions/${submissionId}`
      ),
    enabled: !!submissionId,
  });
}

export function useUpsertAdminFormTemplate() {
  const qc = useQueryClient();

  return useMutation({
    mutationFn: (payload: {
      id?: string;
      body: Omit<DigitalFormTemplate, "id" | "clinic_id" | "version">;
    }) => {
      const dto = {
        code: payload.body.code,
        name: payload.body.name,
        description: payload.body.description,
        schema: payload.body.schema,
        requires_signature: payload.body.requires_signature,
        active: payload.body.active,
      };
      if (payload.id) {
        return api.patch<DigitalFormTemplate>(`/v1/admin/forms/templates/${payload.id}`, dto);
      }
      return api.post<DigitalFormTemplate>("/v1/admin/forms/templates", dto);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin", "forms", "templates"] });
    },
  });
}

export function usePatientPendingForms(
  token: string | null,
  params?: { booking_id?: string | null }
) {
  const search = params?.booking_id ? `?booking_id=${encodeURIComponent(params.booking_id)}` : "";
  return useQuery({
    queryKey: ["patient", "forms", "pending", token, params?.booking_id],
    queryFn: () =>
      api.get<DigitalFormTemplate[]>(`/v1/patient/forms/pending${search}`, token ?? undefined),
    enabled: !!token,
  });
}

export function useSubmitPatientForm(token: string | null) {
  return useMutation({
    mutationFn: (payload: {
      templateCode: string;
      body: {
        booking_id?: string | null;
        data: Record<string, unknown>;
        signature_payload?: unknown;
        signer_name?: string | null;
      };
    }) =>
      api.post<DigitalFormSubmission>(
        `/v1/patient/forms/${encodeURIComponent(payload.templateCode)}/submit`,
        payload.body,
        token ?? undefined
      ),
  });
}

