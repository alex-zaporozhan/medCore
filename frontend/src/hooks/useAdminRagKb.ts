import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export type RagKbDocumentItem = {
  id: string;
  title: string;
  body_preview: string;
  updated_at: string;
};

export type RagKbListDto = { items: RagKbDocumentItem[] };

export type RagKbDocumentDetail = {
  id: string;
  title: string;
  body: string;
  updated_at: string;
};

export function useAdminRagKbDocuments(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.adminRagKb.documents(),
    queryFn: () => api.get<RagKbListDto>("/v1/admin/organization/rag-kb/documents"),
    enabled,
  });
}

export function useAdminRagKbDocument(documentId: string | null, enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.adminRagKb.document(documentId ?? ""),
    queryFn: () =>
      api.get<RagKbDocumentDetail>(`/v1/admin/organization/rag-kb/documents/${documentId}`),
    enabled: Boolean(documentId) && enabled,
  });
}

export function useCreateRagKbDocumentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { title: string; body: string }) =>
      api.post<RagKbDocumentItem>("/v1/admin/organization/rag-kb/documents", payload),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: queryKeys.adminRagKb.documents() });
    },
  });
}

export function useUpdateRagKbDocumentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: { title?: string; body?: string };
    }) =>
      api.patch<RagKbDocumentDetail>(
        `/v1/admin/organization/rag-kb/documents/${id}`,
        payload,
      ),
    onSuccess: async (_data, variables) => {
      await qc.invalidateQueries({ queryKey: queryKeys.adminRagKb.documents() });
      await qc.invalidateQueries({
        queryKey: queryKeys.adminRagKb.document(variables.id),
      });
    },
  });
}

export function useDeleteRagKbDocumentMutation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      api.delete<void>(`/v1/admin/organization/rag-kb/documents/${id}`, null),
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: queryKeys.adminRagKb.documents() });
    },
  });
}
