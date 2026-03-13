import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  ConversationResponse,
  MessagesResponse,
  ChatMessageDto,
} from "@/api/types";

export function usePatientConversation(
  patientId: string | null,
  token: string | null
) {
  return useQuery({
    queryKey: ["patient-chat-conversation", patientId],
    queryFn: () =>
      api.get<ConversationResponse>(
        `/v1/patient/chat/conversation?patient_id=${patientId}`,
        token
      ),
    enabled: !!patientId && !!token,
  });
}

export function usePatientChatMessages(
  patientId: string | null,
  cursor: string | null,
  limit: number,
  token: string | null
) {
  const params = new URLSearchParams();
  params.set("patient_id", patientId ?? "");
  if (cursor) params.set("cursor", cursor);
  if (limit) params.set("limit", String(limit));
  return useQuery({
    queryKey: ["patient-chat-messages", patientId, cursor, limit],
    queryFn: () =>
      api.get<MessagesResponse>(
        `/v1/patient/chat/conversation/messages?${params.toString()}`,
        token
      ),
    enabled: !!patientId && !!token,
  });
}

export function useSendPatientMessage(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      patientId,
      body = "",
      message_type = "text",
      sticker_key,
    }: { patientId: string; body?: string; message_type?: string; sticker_key?: string | null }) =>
      api.post<ChatMessageDto>(
        `/v1/patient/chat/conversation/messages?patient_id=${patientId}`,
        { body, message_type, sticker_key: sticker_key ?? undefined },
        token
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["patient-chat-conversation", variables.patientId],
      });
      queryClient.invalidateQueries({
        queryKey: ["patient-chat-messages", variables.patientId],
      });
    },
  });
}

export function useDeletePatientMessage(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      patientId,
      messageId,
    }: { patientId: string; messageId: string }) =>
      api.delete(
        `/v1/patient/chat/conversation/messages/${messageId}?patient_id=${patientId}`,
        token
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["patient-chat-conversation", variables.patientId],
      });
      queryClient.invalidateQueries({
        queryKey: ["patient-chat-messages", variables.patientId],
      });
    },
  });
}

export function usePatientMarkRead(token: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      patientId,
      up_to_message_id,
    }: { patientId: string; up_to_message_id?: string | null }) =>
      api.post<void>(
        `/v1/patient/chat/conversation/mark-read?patient_id=${patientId}`,
        up_to_message_id != null ? { up_to_message_id } : {},
        token
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["patient-chat-conversation", variables.patientId],
      });
    },
  });
}
