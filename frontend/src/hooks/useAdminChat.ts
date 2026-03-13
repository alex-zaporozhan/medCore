import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type {
  AdminConversationsResponse,
  MessagesResponse,
  ChatMessageDto,
  AssignResponse,
} from "@/api/types";

export interface AdminChatConversationsFilters {
  filter?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

export function useAdminChatConversations(
  filters: AdminChatConversationsFilters = {}
) {
  const params = new URLSearchParams();
  if (filters.filter) params.set("filter", filters.filter);
  if (filters.search) params.set("search", filters.search);
  if (filters.skip !== undefined) params.set("skip", String(filters.skip));
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  const query = params.toString();
  return useQuery({
    queryKey: ["admin-chat-conversations", filters],
    queryFn: () =>
      api.get<AdminConversationsResponse>(
        `/v1/admin/chat/conversations${query ? `?${query}` : ""}`
      ),
    // Обновляем список диалогов раз в несколько секунд, чтобы новые сообщения
    // гарантированно доходили до администратора без ручного обновления страницы.
    refetchInterval: 5000,
  });
}

export function useAdminChatMessages(
  conversationId: string | null,
  cursor: string | null,
  limit: number
) {
  const params = new URLSearchParams();
  if (cursor) params.set("cursor", cursor);
  if (limit) params.set("limit", String(limit));
  const query = params.toString();
  return useQuery({
    queryKey: ["admin-chat-messages", conversationId, cursor, limit],
    queryFn: () =>
      api.get<MessagesResponse>(
        `/v1/admin/chat/conversations/${conversationId}/messages${query ? `?${query}` : ""}`
      ),
    enabled: !!conversationId,
    // Периодически подтягиваем новые сообщения в открытом диалоге.
    refetchInterval: conversationId ? 3000 : false,
  });
}

export function useDeleteAdminMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      messageId,
    }: { conversationId: string; messageId: string }) =>
      api.delete(
        `/v1/admin/chat/conversations/${conversationId}/messages/${messageId}`
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["admin-chat-conversations"],
      });
      queryClient.invalidateQueries({
        queryKey: ["admin-chat-messages", variables.conversationId],
      });
    },
  });
}

export function useSendAdminMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      body = "",
      message_type = "text",
      sticker_key,
    }: { conversationId: string; body?: string; message_type?: string; sticker_key?: string | null }) =>
      api.post<ChatMessageDto>(
        `/v1/admin/chat/conversations/${conversationId}/messages`,
        { body, message_type, sticker_key: sticker_key ?? undefined }
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["admin-chat-conversations"],
      });
      queryClient.invalidateQueries({
        queryKey: ["admin-chat-messages", variables.conversationId],
      });
    },
  });
}

export function useAdminAssignConversation() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      admin_id,
    }: { conversationId: string; admin_id?: string | null }) =>
      api.post<AssignResponse>(
        `/v1/admin/chat/conversations/${conversationId}/assign`,
        admin_id != null ? { admin_id } : {}
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-chat-conversations"] });
      queryClient.invalidateQueries({
        queryKey: ["admin-chat-messages", variables.conversationId],
      });
    },
  });
}

export function useAdminChatMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conversationId,
      up_to_message_id,
    }: { conversationId: string; up_to_message_id?: string | null }) =>
      api.post<void>(
        `/v1/admin/chat/conversations/${conversationId}/mark-read`,
        up_to_message_id != null ? { up_to_message_id } : {}
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-chat-conversations"] });
      queryClient.invalidateQueries({
        queryKey: ["admin-chat-messages", variables.conversationId],
      });
    },
  });
}
