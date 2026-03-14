import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";

export interface OmniChatListItem {
  chat_id: string;
  contact_id: string;
  contact_name: string | null;
  contact_primary_phone: string | null;
  status: string;
  last_message_at: string | null;
  last_actor_type: string | null;
  ai_mode?: string | null;
}

export interface OmniChatsResponse {
  items: OmniChatListItem[];
  total: number;
}

export interface OmniChatDetail {
  chat_id: string;
  contact_id: string;
  contact_name: string | null;
  contact_primary_phone: string | null;
  channel_id: string | null;
  channel_type: string | null;
  status: string;
  ai_mode: string;
  last_message_at: string | null;
  last_actor_type: string | null;
  created_at: string | null;
  lead_id: string | null;
  lead_stage_id: string | null;
  lead_stage_name: string | null;
  lead_estimated_value: string | null;
  lead_actual_value: string | null;
}

export interface OmniMessageDto {
  id: string;
  direction: string;
  actor_type: string;
  content: string;
  created_at: string | null;
  ui_hidden?: boolean;
  hidden_reason?: string | null;
   channel_type?: string | null;
}

export interface OmniMessagesResponse {
  items: OmniMessageDto[];
}

export interface OmniChatListFilters {
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export function useAdminOmniChats(filters: OmniChatListFilters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.search) params.set("search", filters.search);
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.page_size !== undefined) params.set("page_size", String(filters.page_size));
  const query = params.toString();
  return useQuery({
    queryKey: ["admin-omni-chats", filters],
    queryFn: () =>
      api.get<OmniChatsResponse>(
        `/v1/admin/omni-chats${query ? `?${query}` : ""}`
      ),
    refetchInterval: 5000,
  });
}

export function useAdminOmniChatDetail(chatId: string | null) {
  return useQuery({
    queryKey: ["admin-omni-chat-detail", chatId],
    queryFn: () => api.get<OmniChatDetail>(`/v1/admin/omni-chats/${chatId}`),
    enabled: !!chatId,
  });
}

export function useAdminOmniChatMessages(
  chatId: string | null,
  options: { limit?: number; after?: string | null; before?: string | null; include_hidden?: boolean } = {}
) {
  const { limit = 50, after, before, include_hidden } = options;
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (after) params.set("after", after);
  if (before) params.set("before", before);
  if (include_hidden) params.set("include_hidden", "true");
  const query = params.toString();
  return useQuery({
    queryKey: ["admin-omni-chat-messages", chatId, limit, after, before],
    queryFn: () =>
      api.get<OmniMessagesResponse>(
        `/v1/admin/omni-chats/${chatId}/messages?${query}`
      ),
    enabled: !!chatId,
    refetchInterval: chatId ? 3000 : false,
  });
}

export function useSendAdminOmniMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      chatId,
      content,
    }: { chatId: string; content: string }) =>
      api.post<OmniMessageDto>(`/v1/admin/omni-chats/${chatId}/messages`, {
        content,
      }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
      queryClient.invalidateQueries({
        queryKey: ["admin-omni-chat-messages", variables.chatId],
      });
      queryClient.invalidateQueries({
        queryKey: ["admin-omni-chat-detail", variables.chatId],
      });
    },
  });
}

export function useHideAdminOmniMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      chatId,
      messageId,
      reason,
    }: { chatId: string; messageId: string; reason: string }) =>
      api.post(
        `/v1/admin/omni-chats/${chatId}/messages/${messageId}/hide`,
        { reason }
      ),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["admin-omni-chat-messages", variables.chatId],
      });
    },
  });
}

export const OMNI_CHAT_AI_MODES = ["DISABLED", "AUTO_REPLY", "SUGGEST_ONLY"] as const;

export function useUpdateOmniChatAiMode() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      chatId,
      ai_mode,
    }: { chatId: string; ai_mode: string }) =>
      api.post(`/v1/admin/omni-chats/${chatId}/ai-mode`, { ai_mode }),
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({
        queryKey: ["admin-omni-chat-detail", variables.chatId],
      });
      queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
    },
  });
}
