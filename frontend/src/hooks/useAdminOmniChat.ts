import { useEffect, useMemo, useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { API_BASE, api, getAdminToken } from "@/api/client";
import { flattenOmniMessagePages } from "@/utils/mergeOmniMessages";

export function getAdminClinicChatAttachmentBlob(conversationId: string, attachmentId: string): Promise<Blob> {
  return api.getBlob(`/v1/admin/chat/conversations/${conversationId}/attachments/${attachmentId}/file`);
}

export function getAdminOmniAttachmentBlob(chatId: string, messageId: string, attachmentId: string): Promise<Blob> {
  return api.getBlob(`/v1/admin/omni-chats/${chatId}/messages/${messageId}/attachments/${attachmentId}/file`);
}

export interface OmniChatListItem {
  chat_id: string;
  contact_id: string;
  contact_name: string | null;
  contact_primary_phone: string | null;
  channel_id?: string | null;
  channel_type?: string | null;
  channel_types?: string[];
  status: string;
  last_message_at: string | null;
  last_actor_type: string | null;
  ai_mode?: string | null;
  assignee_admin_id?: string | null;
  assignee_name?: string | null;
  needs_attention?: boolean;
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
  claimed_at?: string | null;
  closed_at?: string | null;
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
  channel_types?: string[];
  page?: number;
  page_size?: number;
  /** P1-B: только диалоги, назначенные на текущего админа */
  assignee?: "me" | "unassigned";
}

export function useAdminOmniChats(filters: OmniChatListFilters = {}) {
  const params = new URLSearchParams();
  if (filters.status) params.set("status", filters.status);
  if (filters.search) params.set("search", filters.search);
  for (const t of filters.channel_types ?? []) {
    if (!t) continue;
    params.append("channel_types", t);
  }
  if (filters.page !== undefined) params.set("page", String(filters.page));
  if (filters.page_size !== undefined) params.set("page_size", String(filters.page_size));
  if (filters.assignee === "me") params.set("assignee", "me");
  if (filters.assignee === "unassigned") params.set("assignee", "unassigned");
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

export interface OmniChatClaimResponse {
  chat: OmniChatDetail;
}

export function useClaimAdminOmniChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ chatId }: { chatId: string }) =>
      api.post<OmniChatClaimResponse>(`/v1/admin/omni-chats/${chatId}/claim`, {}),
    onSuccess: (data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-detail", variables.chatId] });
      void queryClient.setQueryData(["admin-omni-chat-detail", variables.chatId], data.chat);
    },
  });
}

export interface OmniChatClosureTagDto {
  id: string;
  title: string;
  is_active: boolean;
  sort_order: number;
}

export function useOmniChatClosureTags(enabled: boolean) {
  return useQuery({
    queryKey: ["admin-omni-chat-closure-tags"],
    queryFn: () => api.get<{ items: OmniChatClosureTagDto[] }>("/v1/admin/omni-chat-closure-tags"),
    enabled,
  });
}

export type OmniCloseOutcome = "BOOKED" | "THINKING" | "UNHAPPY" | "OTHER";

export interface CloseOmniChatRequest {
  outcome: OmniCloseOutcome;
  tag_ids: string[];
  comment?: string | null;
}

export interface OmniChatCloseResponse {
  chat: OmniChatDetail;
}

export function useCloseAdminOmniChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ chatId, body }: { chatId: string; body: CloseOmniChatRequest }) =>
      api.post<OmniChatCloseResponse>(`/v1/admin/omni-chats/${chatId}/close`, body),
    onSuccess: (data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-detail", variables.chatId] });
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-messages", variables.chatId] });
      void queryClient.setQueryData(["admin-omni-chat-detail", variables.chatId], data.chat);
    },
  });
}

export interface OmniChatResolveResponse {
  lead_log_id: string;
  task_id?: string;
  outcome?: string;
}

export interface OmniChatPresenceRequest {
  client_event_id: string;
  tab_id: string;
  event: "OPEN" | "HEARTBEAT" | "CLOSE";
}

export interface OmniChatPresenceResponse {
  lease: {
    chat_id: string;
    admin_id: string;
    tab_id: string;
    expires_at: string;
    last_heartbeat_at: string;
  } | null;
  claimed: boolean;
  assignee_admin_id: string | null;
}

export function useAdminOmniChatPresence() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ chatId, body }: { chatId: string; body: OmniChatPresenceRequest }) =>
      api.post<OmniChatPresenceResponse>(`/v1/admin/omni-chats/${chatId}/presence`, body),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-detail", variables.chatId] });
    },
  });
}

export function useResolveAdminOmniChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ chatId }: { chatId: string }) =>
      api.post<OmniChatResolveResponse>(`/v1/admin/omni-chats/${chatId}/resolve`, {}),
    onSuccess: (_data, variables) => {
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-detail", variables.chatId] });
      void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-messages", variables.chatId] });
    },
  });
}

export interface OmniChatOutcomeStatDto {
  outcome: string;
  count: number;
}

export interface OmniChatAdminStatDto {
  admin_id: string;
  admin_name: string | null;
  claimed_count: number;
  closed_count: number;
}

export interface OmniChatAnalyticsResponse {
  date_from: string;
  date_to: string;
  total_chats_created: number;
  total_claimed: number;
  total_closed: number;
  avg_time_to_claim_seconds: number | null;
  avg_time_to_close_seconds: number | null;
  outcomes: OmniChatOutcomeStatDto[];
  by_admin: OmniChatAdminStatDto[];
}

export function useOmniChatAnalytics(
  enabled: boolean,
  params: { date_from: string; date_to: string },
) {
  const qs = new URLSearchParams();
  qs.set("date_from", params.date_from);
  qs.set("date_to", params.date_to);
  return useQuery({
    queryKey: ["admin-omni-chat-analytics", params],
    queryFn: () =>
      api.get<OmniChatAnalyticsResponse>(
        `/v1/admin/omni-chats/analytics?${qs.toString()}`,
      ),
    enabled,
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
    let es: EventSource | null = null;
    let reconnectTimer: number | null = null;
    let reconnectAttempt = 0;
    let disposed = false;
    let sseToken: string | null = null;

    const buildUrl = () => {
      if (!sseToken) return null;
      return `${API_BASE}/v1/admin/omni-chats/events?access_token=${encodeURIComponent(sseToken)}`;
    };

    const fetchSseToken = async () => {
      // needs regular admin JWT in Authorization header (api client reads from storage)
      const t = getAdminToken();
      if (!t) return null;
      const res = await api.get<{ token: string; expires_in_seconds: number }>(`/v1/admin/omni-chats/sse-token`);
      return res?.token || null;
    };

    const connect = () => {
      if (disposed) return;
      const url = buildUrl();
      if (!url) return;
      es = new EventSource(url);
      es.onopen = () => {
        reconnectAttempt = 0;
        setSseBroken(false);
      };
      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as { type?: string; chat_id?: string };
          if (data.type !== "message.created" && data.type !== "chat.updated") return;
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
          void (async () => {
            try {
              const next = await fetchSseToken();
              if (next) sseToken = next;
            } catch {
              /* ignore */
            }
            connect();
          })();
        }, delayMs);
      };
    };

    void (async () => {
      try {
        sseToken = await fetchSseToken();
      } catch {
        sseToken = null;
      }
      connect();
    })();
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
