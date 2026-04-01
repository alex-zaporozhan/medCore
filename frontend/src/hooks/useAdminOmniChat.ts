import { useEffect, useMemo, useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { API_BASE, api, getAdminToken } from "@/api/client";
import { flattenOmniMessagePages } from "@/utils/mergeOmniMessages";

export interface OmniChatListItem {
  chat_id: string;
  contact_id: string;
  contact_name: string | null;
  contact_primary_phone: string | null;
  status: string;
  last_message_at: string | null;
  last_actor_type: string | null;
  ai_mode?: string | null;
  assignee_admin_id?: string | null;
  assignee_name?: string | null;
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
  assignee_admin_id?: string | null;
  assignee_name?: string | null;
}

export interface OmniMessageAttachmentDto {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
  source: "omni" | "clinic_chat";
  conversation_id?: string | null;
}

export interface OmniMessageDto {
  id: string;
  direction: string;
  actor_type: string;
  content: string;
  message_content_type?: string;
  attachments?: OmniMessageAttachmentDto[];
  created_at: string | null;
  ui_hidden?: boolean;
  hidden_reason?: string | null;
  channel_id?: string | null;
  channel_type?: string | null;
  sender_admin_id?: string | null;
  delivery_status?: string | null;
  read_status?: string | null;
}

export interface OmniMessagesResponse {
  items: OmniMessageDto[];
}

export interface OmniChatListFilters {
  status?: string;
  search?: string;
  page?: number;
  page_size?: number;
  /** P1-B: только диалоги, назначенные на текущего админа */
  assignee?: "me";
}

export function useAdminOmniChats(filters: OmniChatListFilters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.search) params.set("search", filters.search);
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.page_size !== undefined) params.set("page_size", String(filters.page_size));
  if (filters.assignee === "me") params.set("assignee", "me");
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
    queryKey: ["admin-omni-chat-messages", chatId, limit, after, before, include_hidden],
    queryFn: () =>
      api.get<OmniMessagesResponse>(
        `/v1/admin/omni-chats/${chatId}/messages?${query}`
      ),
    enabled: !!chatId,
    refetchInterval: chatId ? 3000 : false,
  });
}

/**
 * Подгрузка истории: первая страница — последние N сообщений; следующие — `before` = id самого старого в предыдущей странице.
 * P0-B: без refetchInterval у ленты (список чатов остаётся с polling отдельно).
 */
export function useAdminOmniChatMessagesInfinite(
  chatId: string | null,
  options: { limit?: number; include_hidden?: boolean } = {},
) {
  const { limit = 100, include_hidden } = options;

  const query = useInfiniteQuery({
    queryKey: ["admin-omni-chat-messages", chatId, limit, include_hidden, "infinite"],
    initialPageParam: undefined as string | undefined,
    queryFn: async ({ pageParam }) => {
      const params = new URLSearchParams();
      params.set("limit", String(limit));
      if (pageParam) params.set("before", pageParam);
      if (include_hidden) params.set("include_hidden", "true");
      return api.get<OmniMessagesResponse>(
        `/v1/admin/omni-chats/${chatId}/messages?${params.toString()}`,
      );
    },
    getNextPageParam: (lastPage) => {
      if (!lastPage.items.length) return undefined;
      if (lastPage.items.length < limit) return undefined;
      return lastPage.items[0].id;
    },
    enabled: !!chatId,
    refetchInterval: false,
  });

  const mergedMessages = useMemo(
    () => flattenOmniMessagePages(query.data?.pages ?? []),
    [query.data?.pages],
  );

  return { ...query, mergedMessages };
}

/**
 * SSE (P1-A): события `message.created` без текста; при ошибке — fallback polling 12s.
 * Только на странице омника (`enabled`).
 */
export function useOmniChatSse(enabled: boolean, selectedChatId: string | null) {
  const queryClient = useQueryClient();
  const [sseBroken, setSseBroken] = useState(false);

  useEffect(() => {
    if (!enabled) {
      setSseBroken(false);
      return;
    }
    const token = getAdminToken();
    if (!token) return;
    const url = `${API_BASE}/v1/admin/omni-chats/events?access_token=${encodeURIComponent(token)}`;
    let es: EventSource | null = null;
    let reconnectTimer: number | null = null;
    let reconnectAttempt = 0;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      es = new EventSource(url);
      es.onopen = () => {
        reconnectAttempt = 0;
        setSseBroken(false);
      };
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as { type?: string; chat_id?: string };
          if (data.type !== "message.created") return;
          void queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
          if (selectedChatId && data.chat_id === selectedChatId) {
            void queryClient.invalidateQueries({
              queryKey: ["admin-omni-chat-messages", selectedChatId],
            });
            void queryClient.invalidateQueries({
              queryKey: ["admin-omni-chat-detail", selectedChatId],
            });
          }
        } catch {
          /* ignore */
        }
      };
      es.onerror = () => {
        if (es) {
          es.close();
          es = null;
        }
        if (disposed) return;
        setSseBroken(true);
        const delayMs = Math.min(30_000, 1_000 * (2 ** Math.min(reconnectAttempt, 5)));
        reconnectAttempt += 1;
        reconnectTimer = window.setTimeout(() => {
          connect();
        }, delayMs);
      };
    };

    connect();
    return () => {
      disposed = true;
      if (es) es.close();
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      setSseBroken(false);
    };
  }, [enabled, selectedChatId, queryClient]);

  useEffect(() => {
    if (!enabled || !sseBroken) return;
    const id = window.setInterval(() => {
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
      if (selectedChatId) {
        void queryClient.invalidateQueries({
          queryKey: ["admin-omni-chat-messages", selectedChatId],
        });
        void queryClient.invalidateQueries({
          queryKey: ["admin-omni-chat-detail", selectedChatId],
        });
      }
    }, 12000);
    return () => window.clearInterval(id);
  }, [enabled, sseBroken, selectedChatId, queryClient]);

  return { sseBroken };
}

export interface OmniQuickReply {
  id: string;
  clinic_id: string;
  title: string;
  body: string;
  sort_order: number;
  created_at: string | null;
}

export function useOmniQuickReplies(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-omni-quick-replies"],
    queryFn: () => api.get<{ items: OmniQuickReply[] }>("/v1/admin/omni-chats/quick-replies"),
    enabled,
  });
}

export function usePatchOmniChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      chatId,
      assignee_admin_id,
      status,
    }: {
      chatId: string;
      assignee_admin_id?: string | null;
      status?: string | null;
    }) =>
      api.patch<OmniChatDetail>(`/v1/admin/omni-chats/${chatId}`, {
        ...(assignee_admin_id !== undefined ? { assignee_admin_id } : {}),
        ...(status !== undefined ? { status } : {}),
      }),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({
        queryKey: ["admin-omni-chat-detail", variables.chatId],
      });
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
    },
  });
}

export function useSendAdminOmniMessage() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      chatId,
      content,
      reply_channel_id,
    }: {
      chatId: string;
      content: string;
      reply_channel_id?: string | null;
    }) =>
      api.post<OmniMessageDto>(`/v1/admin/omni-chats/${chatId}/messages`, {
        content,
        ...(reply_channel_id ? { reply_channel_id } : {}),
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

export function useSendAdminOmniMessageWithFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      chatId,
      body,
      file,
      reply_channel_id,
    }: {
      chatId: string;
      body: string;
      file: File;
      reply_channel_id?: string | null;
    }) => {
      const fd = new FormData();
      fd.append("body", body);
      fd.append("file", file);
      if (reply_channel_id) {
        fd.append("reply_channel_id", reply_channel_id);
      }
      return api.postFormData<OmniMessageDto>(
        `/v1/admin/omni-chats/${chatId}/messages/upload`,
        fd
      );
    },
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
