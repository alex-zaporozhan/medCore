import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { queryKeys } from "@/queryKeys";

export interface NamedAdminBrief {
  id: string;
  full_name: string | null;
  avatar_url?: string | null;
}

export interface StaffAttachmentBrief {
  id: string;
  file_name: string;
  content_type: string;
  size_bytes: number;
}

export interface StaffFeedPostResponse {
  id: string;
  title?: string | null;
  body: string;
  author: NamedAdminBrief;
  created_at: string;
  comments_count: number;
  likes_count: number;
  liked_by_me?: boolean;
  acknowledged_by_me?: boolean;
  acknowledged_count?: number;
  audience_total?: number;
  is_announcement?: boolean;
  requires_ack?: boolean;
  priority_level?: "normal" | "priority" | "critical";
  audience_roles?: string[];
  audience_admin_ids?: string[];
  attachments?: StaffAttachmentBrief[];
}

export interface StaffFeedCommentResponse {
  id: string;
  body: string;
  author: NamedAdminBrief;
  created_at: string;
  updated_at?: string | null;
  parent_comment_id?: string | null;
  in_reply_to?: NamedAdminBrief | null;
  attachments?: StaffAttachmentBrief[];
  deleted_at?: string | null;
  deleted_by_admin_id?: string | null;
}

export interface StaffChatRoomResponse {
  id: string;
  kind: string;
  title: string;
  task_id?: string | null;
  last_message_at?: string | null;
  last_message_preview?: string | null;
  unread_count?: number;
  dm_peer?: NamedAdminBrief | null;
}

export interface StaffChatMessageResponse {
  id: string;
  body: string;
  author: NamedAdminBrief;
  created_at: string;
  attachments?: StaffAttachmentBrief[];
}

export interface StaffCalendarEventResponse {
  id: string;
  title: string;
  description: string | null;
  starts_at: string;
  ends_at: string;
  all_day: boolean;
  task_id: string | null;
  reminder_minutes_before?: number | null;
  created_by: NamedAdminBrief;
  /** Приглашённые сотрудники (совещание); организатор может дублироваться в списке на бэкенде. */
  participants?: NamedAdminBrief[];
}

export interface CalendarEventChip {
  id: string;
  title: string;
  starts_at: string;
  ends_at: string;
  all_day: boolean;
  task_id: string | null;
  created_by_admin_id: string;
}

export interface CalendarDayCell {
  date: string;
  is_in_current_month: boolean;
  events: CalendarEventChip[];
  reminder_event_ids: string[];
  unseen_invite_event_ids: string[];
  unseen_invite_count: number;
}

export interface StaffCalendarNotificationSignals {
  unseen_invites_count: number;
  reminders_due_now_count: number;
}

export interface CalendarMonthRange {
  from: string;
  to: string;
}

export interface StaffCalendarMonthGridResponse {
  month: CalendarMonthRange;
  days: CalendarDayCell[];
  notification_signals: StaffCalendarNotificationSignals;
}

export interface StaffCalendarReminderInfo {
  reminder_minutes_before: number | null;
  fire_at: string | null;
  sent_at: string | null;
}

export interface StaffCalendarCreatorAckSummary {
  total_participants: number;
  acknowledged_participants: number;
}

export interface StaffCalendarEventDetailsResponse {
  event: StaffCalendarEventResponse;
  reminder: StaffCalendarReminderInfo;
  invitation_acknowledged_at: string | null;
  creator_ack_summary: StaffCalendarCreatorAckSummary | null;
}

export interface StaffCalendarInvitationAckResponse {
  event_id: string;
  acknowledged_at: string;
  unseen_invite_count: number | null;
}

export interface KnowledgeDocumentResponse {
  id: string;
  folder_key: string;
  title: string;
  body_md: string;
  visible_roles: string[];
  sort_order: number;
  created_by: NamedAdminBrief;
  updated_at: string;
}

export function useStaffFeedPosts(limit = 30) {
  return useQuery({
    queryKey: [...queryKeys.staffCollab.feedPosts(), limit] as const,
    queryFn: () =>
      api.get<StaffFeedPostResponse[]>(`/v1/admin/staff/feed/posts?limit=${encodeURIComponent(String(limit))}`),
  });
}

export function useStaffAnnouncements(limit = 50) {
  return useQuery({
    queryKey: ["staff-collab", "announcements", "posts", limit] as const,
    queryFn: () =>
      api.get<StaffFeedPostResponse[]>(
        `/v1/admin/staff/feed/announcements?limit=${encodeURIComponent(String(limit))}`
      ),
  });
}

export function useCreateStaffFeedPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      title?: string | null;
      body: string;
      is_announcement?: boolean;
      requires_ack?: boolean;
      priority_level?: "normal" | "priority" | "critical";
      audience_roles?: string[];
      audience_admin_ids?: string[];
    }) =>
      api.post<StaffFeedPostResponse>(`/v1/admin/staff/feed/posts`, {
        title: payload.title?.trim() ? payload.title.trim() : null,
        body: payload.body,
        is_announcement: Boolean(payload.is_announcement),
        requires_ack: Boolean(payload.requires_ack),
        priority_level: payload.priority_level ?? "normal",
        audience_roles: payload.audience_roles ?? [],
        audience_admin_ids: payload.audience_admin_ids ?? [],
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
    },
  });
}

export interface StaffFeedPostLikeResponse {
  liked: boolean;
  likes_count: number;
}

export function useToggleStaffFeedPostLike() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) =>
      api.post<StaffFeedPostLikeResponse>(`/v1/admin/staff/feed/posts/${postId}/like`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
    },
  });
}

export interface StaffFeedPostAckResponse {
  acknowledged: boolean;
  acknowledged_count: number;
}

export function useAckStaffFeedPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) =>
      api.post<StaffFeedPostAckResponse>(`/v1/admin/staff/feed/posts/${postId}/ack`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
    },
  });
}

export interface StaffFeedAckStatusRow {
  admin_id: string;
  admin_name: string | null;
  acknowledged_at: string | null;
}

export interface StaffFeedPostAckStatusResponse {
  post_id: string;
  acknowledged: StaffFeedAckStatusRow[];
  pending: StaffFeedAckStatusRow[];
}

export function useStaffFeedPostAckStatus(postId: string | null) {
  return useQuery({
    queryKey: ["staff-collab", "feed-post-ack-status", postId] as const,
    queryFn: () =>
      api.get<StaffFeedPostAckStatusResponse>(`/v1/admin/staff/feed/posts/${postId}/ack-status`),
    enabled: !!postId,
  });
}

export function useUpdateStaffFeedPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (vars: { postId: string; title?: string | null; body: string; file?: File | null }) => {
      const fd = new FormData();
      if (vars.title !== undefined) fd.append("title", vars.title ?? "");
      fd.append("body", vars.body);
      if (vars.file) fd.append("file", vars.file);
      return api.patchFormData<StaffFeedPostResponse>(
        `/v1/admin/staff/feed/posts/${vars.postId}`,
        fd
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
    },
  });
}

export function useDeleteStaffFeedPost() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (postId: string) => api.delete<void>(`/v1/admin/staff/feed/posts/${postId}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
    },
  });
}

export function useUploadStaffFeedPostAttachment(postId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ file }: { file: File }) => {
      if (!postId) throw new Error("post");
      const fd = new FormData();
      fd.append("file", file);
      return api.postFormData<StaffAttachmentBrief>(
        `/v1/admin/staff/feed/posts/${postId}/attachments`,
        fd
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
    },
  });
}

export async function downloadStaffFeedPostAttachmentFile(attachmentId: string, fileName: string) {
  const blob = await api.getBlob(`/v1/admin/staff/feed/attachments/${attachmentId}/file`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}

export function useStaffFeedComments(postId: string | null) {
  return useQuery({
    queryKey: queryKeys.staffCollab.feedComments(postId),
    queryFn: () =>
      api.get<StaffFeedCommentResponse[]>(`/v1/admin/staff/feed/posts/${postId}/comments`),
    enabled: !!postId,
  });
}

export function useUpdateStaffFeedComment(postId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { commentId: string; body: string }) =>
      api.patch<StaffFeedCommentResponse>(`/v1/admin/staff/feed/comments/${vars.commentId}`, {
        body: vars.body,
      }),
    onSuccess: () => {
      if (postId) {
        void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedComments(postId) });
      }
    },
  });
}

export function useDeleteStaffFeedComment(postId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (commentId: string) => api.delete<void>(`/v1/admin/staff/feed/comments/${commentId}`),
    onSuccess: () => {
      if (postId) {
        void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedComments(postId) });
      }
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
    },
  });
}

export interface StaffAnnouncementPublishPolicyRow {
  scope_type: "role" | "user";
  scope_value: string;
  can_publish: boolean;
}

export interface StaffAnnouncementPublishPolicyResponse {
  policies: StaffAnnouncementPublishPolicyRow[];
}

export function useStaffAnnouncementPublishPolicy() {
  return useQuery({
    queryKey: ["staff-collab", "announcements", "publish-policy"] as const,
    queryFn: () =>
      api.get<StaffAnnouncementPublishPolicyResponse>(`/v1/admin/staff/feed/announcements/publish-policy`),
  });
}

export function useUpdateStaffAnnouncementPublishPolicy() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (rows: StaffAnnouncementPublishPolicyRow[]) =>
      api.put<StaffAnnouncementPublishPolicyResponse>(
        `/v1/admin/staff/feed/announcements/publish-policy`,
        rows
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["staff-collab", "announcements", "publish-policy"] as const });
    },
  });
}

export interface StaffAnnouncementPublishPolicyAuditRow {
  id: string;
  created_at: string;
  actor_admin_id?: string | null;
  actor_name?: string | null;
  snapshot?: any;
}

export interface StaffAnnouncementPublishPolicyAuditListResponse {
  items: StaffAnnouncementPublishPolicyAuditRow[];
}

export function useStaffAnnouncementPublishPolicyAudit(limit = 200) {
  return useQuery({
    queryKey: ["staff-collab", "announcements", "publish-policy", "audit", limit] as const,
    queryFn: () =>
      api.get<StaffAnnouncementPublishPolicyAuditListResponse>(
        `/v1/admin/staff/feed/announcements/publish-policy/audit?limit=${encodeURIComponent(String(limit))}`
      ),
  });
}

export function useAddStaffFeedComment(postId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (payload: { body: string; parent_comment_id?: string | null }) => {
      if (!postId) throw new Error("post");
      return api.post<StaffFeedCommentResponse>(`/v1/admin/staff/feed/posts/${postId}/comments`, {
        body: payload.body,
        parent_comment_id: payload.parent_comment_id ?? null,
      });
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
      if (postId) {
        void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedComments(postId) });
      }
    },
  });
}

export function useUploadStaffFeedCommentAttachment(postId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ commentId, file }: { commentId: string; file: File }) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.postFormData<StaffAttachmentBrief>(
        `/v1/admin/staff/feed/comments/${commentId}/attachments`,
        fd
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
      if (postId) {
        void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.feedComments(postId) });
      }
    },
  });
}

export function useStaffChatRooms() {
  return useQuery({
    queryKey: queryKeys.staffCollab.chatRooms(),
    queryFn: () => api.get<StaffChatRoomResponse[]>(`/v1/admin/staff/chat/rooms`),
  });
}

export function useMarkStaffChatRoomRead() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (roomId: string) => {
      if (!roomId) throw new Error("room");
      return api.post<void>(`/v1/admin/staff/chat/rooms/${roomId}/read`, {});
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.chatRooms() });
    },
  });
}

export function useStaffChatMessages(roomId: string | null) {
  return useQuery({
    queryKey: queryKeys.staffCollab.chatMessages(roomId),
    queryFn: () =>
      api.get<StaffChatMessageResponse[]>(
        `/v1/admin/staff/chat/rooms/${roomId}/messages?limit=100`
      ),
    enabled: !!roomId,
  });
}

export function usePostStaffChatMessage(roomId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: string) =>
      api.post<StaffChatMessageResponse>(`/v1/admin/staff/chat/rooms/${roomId}/messages`, { body }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.chatMessages(roomId) });
    },
  });
}

export function useCreateStaffDmRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (peer_admin_id: string) =>
      api.post<StaffChatRoomResponse>(`/v1/admin/staff/chat/rooms/dm`, { peer_admin_id }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.chatRooms() });
    },
  });
}

export function useCreateStaffGroupRoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { title: string; member_admin_ids: string[] }) =>
      api.post<StaffChatRoomResponse>(`/v1/admin/staff/chat/rooms/group`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.chatRooms() });
    },
  });
}

export function useStaffTaskChatRoom(taskId: string | null) {
  return useQuery({
    queryKey: ["staff-collab", "task-room", taskId] as const,
    queryFn: () => api.get<StaffChatRoomResponse>(`/v1/admin/staff/chat/task-rooms/${taskId}`),
    enabled: !!taskId,
  });
}

export function useUploadStaffChatAttachment(roomId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ messageId, file }: { messageId: string; file: File }) => {
      const fd = new FormData();
      fd.append("file", file);
      return api.postFormData<StaffAttachmentBrief>(
        `/v1/admin/staff/chat/messages/${messageId}/attachments`,
        fd
      );
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.chatMessages(roomId) });
    },
  });
}

export function useInviteStaffRoomMember(roomId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (invitee_admin_id: string) =>
      api.post<StaffChatRoomResponse>(`/v1/admin/staff/chat/rooms/${roomId}/members`, {
        invitee_admin_id,
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.chatRooms() });
    },
  });
}

export async function downloadStaffChatAttachmentFile(attachmentId: string, fileName: string) {
  const blob = await api.getBlob(`/v1/admin/staff/attachments/${attachmentId}/file`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}

export function useStaffCalendarEvents(fromIso: string, toIso: string) {
  const params = new URLSearchParams({
    from: fromIso,
    to: toIso,
  });
  return useQuery({
    queryKey: queryKeys.staffCollab.calendarEvents(fromIso, toIso),
    queryFn: () =>
      api.get<StaffCalendarEventResponse[]>(`/v1/admin/staff/calendar/events?${params.toString()}`),
  });
}

export function useStaffCalendarMonthGrid(fromIso: string, toIso: string) {
  const params = new URLSearchParams({
    from: fromIso,
    to: toIso,
  });
  return useQuery({
    queryKey: queryKeys.staffCollab.calendarMonth(fromIso, toIso),
    queryFn: () =>
      api.get<StaffCalendarMonthGridResponse>(`/v1/admin/staff/calendar/month?${params.toString()}`),
    // Enterprise UX: polling keeps "new" markers + sound triggers responsive.
    refetchInterval: typeof window !== "undefined" ? 30000 : false,
  });
}

export function useStaffCalendarEventDetails(eventId: string | null) {
  return useQuery({
    queryKey: queryKeys.staffCollab.calendarEventDetails(eventId ?? ""),
    queryFn: () => api.get<StaffCalendarEventDetailsResponse>(`/v1/admin/staff/calendar/events/${eventId}`),
    enabled: !!eventId,
  });
}

export function useAckStaffCalendarInvitation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (eventId: string) =>
      api.post<StaffCalendarInvitationAckResponse>(`/v1/admin/staff/calendar/events/${eventId}/invitations/ack`),
    onSuccess: (_data, eventId) => {
      // month grid depends on invitations/reminders; safest is to invalidate all calendar queries.
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.calendarPrefix });
      void qc.invalidateQueries({ queryKey: ["staff-collab", "calendar-month"] as const });
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.calendarEventDetails(eventId) });
    },
  });
}

export function useCreateStaffCalendarEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      title: string;
      description?: string | null;
      starts_at: string;
      ends_at: string;
      all_day?: boolean;
      task_id?: string | null;
      /** 0 или null — без напоминания; если поле не передать, бэкенд по умолчанию 15 мин. */
      reminder_minutes_before?: number | null;
      /** Требует права invite_staff_calendar_participants на бэкенде. */
      participant_admin_ids?: string[];
    }) => api.post<StaffCalendarEventResponse>(`/v1/admin/staff/calendar/events`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.calendarPrefix });
      void qc.invalidateQueries({ queryKey: ["staff-collab", "calendar-month"] as const });
    },
  });
}

/** PATCH /v1/admin/staff/calendar/events/{id} — частичное обновление; `participant_admin_ids` заменяет список целиком. */
export function useUpdateStaffCalendarEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      eventId,
      body,
    }: {
      eventId: string;
      body: {
        title?: string;
        description?: string | null;
        starts_at?: string;
        ends_at?: string;
        all_day?: boolean;
        reminder_minutes_before?: number | null;
        task_id?: string | null;
        participant_admin_ids?: string[];
      };
    }) => api.patch<StaffCalendarEventResponse>(`/v1/admin/staff/calendar/events/${eventId}`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.calendarPrefix });
      void qc.invalidateQueries({ queryKey: ["staff-collab", "calendar-month"] as const });
    },
  });
}

export function useKnowledgeDocuments() {
  return useQuery({
    queryKey: queryKeys.staffCollab.knowledgeDocs(),
    queryFn: () => api.get<KnowledgeDocumentResponse[]>(`/v1/admin/staff/knowledge/documents`),
  });
}

export function useCreateKnowledgeDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      folder_key?: string;
      title: string;
      body_md: string;
      visible_roles?: string[];
      sort_order?: number;
    }) => api.post<KnowledgeDocumentResponse>(`/v1/admin/staff/knowledge/documents`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.knowledgeDocs() });
    },
  });
}

export function useUpdateKnowledgeDocument(docId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      folder_key?: string | null;
      title?: string | null;
      body_md?: string | null;
      visible_roles?: string[] | null;
      sort_order?: number | null;
    }) => api.patch<KnowledgeDocumentResponse>(`/v1/admin/staff/knowledge/documents/${docId}`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: queryKeys.staffCollab.knowledgeDocs() });
    },
  });
}
