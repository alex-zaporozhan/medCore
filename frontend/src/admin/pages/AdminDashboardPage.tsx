import { useAdminReportsDashboardByClinics } from "@/hooks/useAdminReports";
import {
  useCreateStaffFeedPost,
  useStaffFeedPosts,
  useToggleStaffFeedPostLike,
  useUpdateStaffFeedPost,
  useDeleteStaffFeedPost,
  downloadStaffFeedPostAttachmentFile,
  useStaffFeedComments,
  useAddStaffFeedComment,
  useUploadStaffFeedCommentAttachment,
  useUpdateStaffFeedComment,
  useDeleteStaffFeedComment,
} from "@/hooks/useStaffCollab";
import type {
  StaffAttachmentBrief,
  StaffFeedCommentResponse,
  StaffFeedPostResponse,
} from "@/hooks/useStaffCollab";
import { api, ApiErrorWithCode, getAdminId } from "@/api/client";
import { ChatInlineAudioPlayer } from "@/shared/ChatInlineAudioPlayer";
import {
  useRevenueHunterSaved,
  isRevenueHunterEnabled,
  useAdminSession,
  useMyStaffProfile,
} from "@/hooks";
import {
  PageSkeleton,
  EmptyState,
  ContextBar,
  QueryErrorAlert,
  GlassModal,
  PersonNameLink,
} from "@/shared/ui";
import { EmojiMartPopoverPicker, AppleEmojiOverlayTextarea } from "@/shared/ui";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { STAFF_FEED_CHROME } from "@/shared/staffFeedChrome";
import {
  Grid,
  Group,
  MultiSelect,
  Stack,
  Text,
  Button,
  ThemeIcon,
  Input,
  TextInput,
  Progress,
  Anchor,
  ActionIcon,
  Paper,
  Menu,
  Box,
  Skeleton,
  Avatar,
  UnstyledButton,
  Alert,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { useState, useMemo, useEffect, useLayoutEffect, useRef, useCallback } from "react";
import { useMediaQuery } from "@mantine/hooks";
import { useTranslation } from "react-i18next";
import { ROUTE_PATHS } from "@/routePaths";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { feedRevenuePeriodLabel } from "@/shared/feedI18n";
import {
  IconUsers,
  IconX,
  IconRobot,
  IconMail,
  IconStack2,
  IconCalendarStats,
  IconClock,
  IconAlertTriangle,
  IconPaperclip,
  IconPhoto,
  IconMicrophone,
  IconHeart,
  IconMessageCircle,
  IconDots,
} from "@tabler/icons-react";

function feedDateLocale(lng: string): string {
  return lng.toLowerCase().startsWith("ru") ? "ru-RU" : "en-US";
}

function staffInitials(fullName: string | null | undefined): string {
  const t = (fullName ?? "").trim();
  if (!t) return "—";
  const parts = t.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0]!.slice(0, 1)}${parts[1]!.slice(0, 1)}`.toUpperCase();
  }
  return t.slice(0, 2).toUpperCase();
}

function parseHours(v: string | number | undefined): number {
  if (v === undefined || v === null) return 0;
  const n = typeof v === "number" ? v : Number.parseFloat(String(v));
  return Number.isFinite(n) ? n : 0;
}

function StaffFeedAttachmentPreview({ attachment }: { attachment: StaffAttachmentBrief }) {
  const { t } = useTranslation("feed");
  const [url, setUrl] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoadFailed(false);
    async function run() {
      try {
        const blob = await api.getBlob(
          `/v1/admin/staff/feed/attachments/${attachment.id}/file`
        );
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch (e) {
        console.error("staff feed attachment preview failed", e);
        if (!cancelled) setLoadFailed(true);
      }
    }
    void run();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attachment.id]);

  const ct = (attachment.content_type || "").toLowerCase();

  if (!url && !loadFailed) {
    if (ct.startsWith("image/")) {
      return (
        <Box mt="md" mb="md">
          <Skeleton height={220} radius="md" />
        </Box>
      );
    }
    if (ct.startsWith("audio/")) {
      return <Skeleton height={54} radius="md" my="sm" />;
    }
    if (ct.startsWith("video/")) {
      return (
        <Box mt="md" mb="md">
          <Skeleton height={240} radius="md" />
        </Box>
      );
    }
  }

  if (url && ct.startsWith("image/")) {
    return (
      <Box mt="md" mb="md">
        <img
          src={url}
          alt={attachment.file_name}
          style={{
            width: "100%",
            maxHeight: 320,
            objectFit: "contain",
            borderRadius: "var(--mantine-radius-md)",
          }}
        />
      </Box>
    );
  }

  if (url && ct.startsWith("audio/")) {
    return <ChatInlineAudioPlayer src={url} style={{ width: "100%" }} />;
  }

  if (url && ct.startsWith("video/")) {
    return (
      <video
        controls
        src={url}
        style={{ width: "100%", maxHeight: 360, objectFit: "contain", borderRadius: "var(--radius-md)" }}
      />
    );
  }

  if (loadFailed) {
    return (
      <Text size="xs" c="dimmed">
        {t("attachmentUnavailable")}
      </Text>
    );
  }

  return (
    <Anchor
      component="button"
      type="button"
      size="sm"
      onClick={() => void downloadStaffFeedPostAttachmentFile(attachment.id, attachment.file_name)}
      style={{ textAlign: "left", cursor: "pointer" }}
    >
      {attachment.file_name}
    </Anchor>
  );
}

const FEED_COMMENT_MAX_FILE_BYTES = 5 * 1024 * 1024;
const FEED_COMMENT_DOC_ACCEPT =
  ".pdf,.doc,.docx,.txt,.xlsx,.xls,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain";

function staffFeedComposerDraftKey(clinicId: string | null): string {
  return `staffFeedComposerDraft:v1:${clinicId ?? "none"}`;
}

function StaffFeedPostComments({
  postId,
  isOpen,
  regionId,
}: {
  postId: string;
  isOpen: boolean;
  /** Связка с `aria-controls` у кнопки «комментарии». */
  regionId?: string;
}) {
  const [body, setBody] = useState("");
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [fileHint, setFileHint] = useState<string | null>(null);
  const [replyTo, setReplyTo] = useState<StaffFeedCommentResponse | null>(null);
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const commentFileRef = useRef<HTMLInputElement>(null);
  const { data: comments, isLoading } = useStaffFeedComments(isOpen ? postId : null);
  const addComment = useAddStaffFeedComment(isOpen ? postId : null);
  const uploadCommentAtt = useUploadStaffFeedCommentAttachment(isOpen ? postId : null);
  const updateComment = useUpdateStaffFeedComment(isOpen ? postId : null);
  const deleteComment = useDeleteStaffFeedComment(isOpen ? postId : null);
  const { data: session } = useAdminSession();
  const myAdminId = getAdminId();
  const canModerateComments =
    Boolean(session?.roles?.includes("owner")) ||
    Boolean(session?.permissions?.includes("staff.feed.comments.moderate"));

  const triggerCommentAttachPick = useCallback((mode: "doc" | "image") => {
    const el = commentFileRef.current;
    if (!el) return;
    el.accept = mode === "image" ? "image/*" : FEED_COMMENT_DOC_ACCEPT;
    el.value = "";
    el.click();
  }, []);

  useEffect(() => {
    if (!isOpen) {
      setBody("");
      setReplyTo(null);
      setPendingFiles([]);
      setFileHint(null);
      setEditingCommentId(null);
      setEditBody("");
    }
  }, [isOpen]);

  const { t, i18n } = useTranslation("feed");
  const listLocale = feedDateLocale(i18n.language);

  const replyLabel = (c: StaffFeedCommentResponse) => c.author.full_name?.trim() || t("staffFallback");

  if (!isOpen) return null;

  return (
    <Box
      id={regionId}
      role="region"
      aria-label={t("commentsRegion")}
      bg="gray.0"
      p="md"
      style={{ borderRadius: "var(--mantine-radius-md)" }}
    >
      <Stack gap="md" mt={0}>
        {isLoading ? (
          <Text size="xs" c="dimmed">
            {t("loading")}
          </Text>
        ) : comments && comments.length ? (
          <Stack gap="md">
            {comments.map((c) => (
              <Box key={c.id} id={`staff-feed-comment-${c.id}`}>
                <Group
                  justify="space-between"
                  align="flex-start"
                  wrap="nowrap"
                  gap="sm"
                >
                <Avatar size="sm" radius="xl" color="gray.5" variant="light">
                  {staffInitials(replyLabel(c))}
                </Avatar>
                <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                  <Text size="xs" c="dimmed">
                    <Text span fw={500} c="gray.8">
                      {replyLabel(c)}
                    </Text>
                    {" · "}
                    {new Date(c.created_at).toLocaleString(listLocale)}
                  </Text>
                  {c.in_reply_to ? (
                    <Text size="xs" c="dimmed" style={{ fontStyle: "italic" }}>
                      <Anchor
                        component="button"
                        type="button"
                        size="xs"
                        c="dimmed"
                        onClick={() => {
                          const el = document.getElementById(
                            `staff-feed-comment-${c.parent_comment_id}`
                          );
                          el?.scrollIntoView({ behavior: "smooth", block: "nearest" });
                        }}
                      >
                        {c.in_reply_to.full_name?.trim() || t("staffFallback")}
                      </Anchor>
                      , —{" "}
                    </Text>
                  ) : null}
                  {c.deleted_at ? (
                    <Text size="sm" c="dimmed" style={{ textDecoration: "line-through", whiteSpace: "pre-wrap" }}>
                      <AppleEmojiRichText text={c.body || t("deleted")} />
                    </Text>
                  ) : editingCommentId === c.id ? (
                    <Stack gap="xs">
                      <AppleEmojiOverlayTextarea
                        value={editBody}
                        onChange={(e) => setEditBody(e.currentTarget.value)}
                        minRows={2}
                      />
                      <Group justify="flex-end" gap="xs">
                        <Button
                          {...STAFF_FEED_CHROME.subtleButton}
                          size="compact-xs"
                          onClick={() => {
                            setEditingCommentId(null);
                            setEditBody("");
                          }}
                          disabled={updateComment.isPending}
                        >
                          {t("cancel")}
                        </Button>
                        <Button
                          {...STAFF_FEED_CHROME.primaryButton}
                          size="compact-xs"
                          onClick={async () => {
                            if (!editBody.trim()) return;
                            try {
                              await updateComment.mutateAsync({ commentId: c.id, body: editBody.trim() });
                              setEditingCommentId(null);
                              setEditBody("");
                            } catch (e) {
                              setFileHint(
                                e instanceof ApiErrorWithCode
                                  ? e.message
                                  : t("saveCommentFailed")
                              );
                            }
                          }}
                          loading={updateComment.isPending}
                          disabled={!editBody.trim() || updateComment.isPending}
                        >
                          {t("save")}
                        </Button>
                      </Group>
                    </Stack>
                  ) : c.body.trim() ? (
                    <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                      <AppleEmojiRichText text={c.body} />
                    </Text>
                  ) : null}
                  {(c.attachments ?? []).length > 0 ? (
                    <Stack gap="xs" mt={4}>
                      {(c.attachments ?? []).map((att) => (
                        <StaffFeedAttachmentPreview key={att.id} attachment={att} />
                      ))}
                    </Stack>
                  ) : null}
                </Stack>
                <Group gap={4} align="flex-start" wrap="nowrap">
                  <Button
                    variant="subtle"
                    color="gray"
                    size="compact-xs"
                    disabled={Boolean(c.deleted_at)}
                    onClick={() => {
                      setReplyTo(c);
                      textareaRef.current?.focus();
                    }}
                  >
                    {t("reply")}
                  </Button>
                  {(!c.deleted_at && (c.author.id === myAdminId || canModerateComments)) ? (
                    <Menu position="bottom-end" withinPortal>
                      <Menu.Target>
                        <ActionIcon variant="subtle" color="gray" size="sm" aria-label={t("actions")}>
                          <IconDots size={16} stroke={1.5} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        {c.author.id === myAdminId ? (
                          <Menu.Item
                            onClick={() => {
                              setFileHint(null);
                              setEditingCommentId(c.id);
                              setEditBody(c.body ?? "");
                            }}
                          >
                            {t("edit")}
                          </Menu.Item>
                        ) : null}
                        <Menu.Item
                          color="red"
                          disabled={deleteComment.isPending}
                          onClick={async () => {
                            const ok = window.confirm(t("deleteCommentConfirm"));
                            if (!ok) return;
                            setFileHint(null);
                            try {
                              await deleteComment.mutateAsync(c.id);
                            } catch (e) {
                              setFileHint(
                                e instanceof ApiErrorWithCode
                                  ? e.message
                                  : t("deleteCommentFailed")
                              );
                            }
                          }}
                        >
                          {t("delete")}
                        </Menu.Item>
                      </Menu.Dropdown>
                    </Menu>
                  ) : null}
                </Group>
              </Group>
              </Box>
            ))}
          </Stack>
        ) : (
          <Text size="xs" c="dimmed">
            {t("emptyComments")}
          </Text>
        )}

      {replyTo ? (
        <Group gap="xs" align="center">
          <Text size="xs" c="dimmed">
            {t("replyingTo")}{" "}
            <Text span fw={600} c="gray.8">
              {replyLabel(replyTo)}
            </Text>
          </Text>
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            aria-label={t("cancelReply")}
            onClick={() => setReplyTo(null)}
          >
            <IconX size={16} stroke={1.5} />
          </ActionIcon>
        </Group>
      ) : null}

      <AppleEmojiOverlayTextarea
        ref={textareaRef}
        value={body}
        onChange={(e) => setBody(e.currentTarget.value)}
        minRows={2}
        placeholder={t("commentPlaceholder")}
      />
      <input
        ref={commentFileRef}
        type="file"
        style={{ display: "none" }}
        onChange={(e) => {
          const f = e.target.files?.[0] ?? null;
          e.target.value = "";
          setFileHint(null);
          if (!f) return;
          if (f.size > FEED_COMMENT_MAX_FILE_BYTES) {
            setFileHint(t("fileTooLarge"));
            return;
          }
          setPendingFiles((prev) => [...prev, f]);
        }}
      />
      {fileHint ? (
        <Text size="xs" c="red">
          {fileHint}
        </Text>
      ) : null}
      {pendingFiles.length > 0 ? (
        <Text size="xs" c="dimmed">
          {t("commentFiles")}{" "}
          {pendingFiles.map((f) => f.name).join(", ")}{" "}
          <Anchor
            component="button"
            type="button"
            size="xs"
            c="red.7"
            onClick={() => setPendingFiles([])}
          >
            {t("removeFiles")}
          </Anchor>
        </Text>
      ) : null}
      <Group justify="space-between" align="center" wrap="wrap">
        <Group gap="xs">
          <EmojiMartPopoverPicker
            onPick={(native) => setBody((prev) => prev + native)}
            onInserted={() => textareaRef.current?.focus()}
          />
          <ActionIcon
            {...STAFF_FEED_CHROME.actionIcon}
            aria-label={t("ariaDoc")}
            onClick={() => triggerCommentAttachPick("doc")}
          >
            <IconPaperclip size={18} />
          </ActionIcon>
          <ActionIcon
            {...STAFF_FEED_CHROME.actionIcon}
            aria-label={t("ariaImage")}
            onClick={() => triggerCommentAttachPick("image")}
          >
            <IconPhoto size={18} />
          </ActionIcon>
        </Group>
        <Button
          color="slate"
          variant="filled"
          size="xs"
          onClick={async () => {
            if (!body.trim() && pendingFiles.length === 0) return;
            for (const f of pendingFiles) {
              if (f.size > FEED_COMMENT_MAX_FILE_BYTES) {
                setFileHint(t("fileTooLarge"));
                return;
              }
            }
            setFileHint(null);
            const filesSnapshot = [...pendingFiles];
            try {
              const comment = await addComment.mutateAsync({
                body: body.trim(),
                parent_comment_id: replyTo?.id ?? null,
              });
              const cid = String(comment.id);
              for (const f of filesSnapshot) {
                await uploadCommentAtt.mutateAsync({ commentId: cid, file: f });
              }
              setBody("");
              setPendingFiles([]);
              setReplyTo(null);
            } catch (e) {
              const msg =
                e instanceof ApiErrorWithCode
                  ? e.message
                  : t("sendFailed");
              setFileHint(msg);
            }
          }}
          disabled={
            (!body.trim() && pendingFiles.length === 0) ||
            addComment.isPending ||
            uploadCommentAtt.isPending
          }
          loading={addComment.isPending || uploadCommentAtt.isPending}
        >
          {t("send")}
        </Button>
      </Group>
      </Stack>
    </Box>
  );
}

export default function AdminDashboardPage() {
  const { t, i18n } = useTranslation("feed");
  const listLocale = feedDateLocale(i18n.language);
  const { clinics, currentClinicId } = useAdminClinic();
  const composerDraftStorageKey = useMemo(() => staffFeedComposerDraftKey(currentClinicId), [currentClinicId]);
  const composerDraftPersistReady = useRef(false);
  const [selectedClinicIds, setSelectedClinicIds] = useState<string[]>([]);
  const [feedTitle, setFeedTitle] = useState("");
  const [feedBody, setFeedBody] = useState("");
  const [feedFiles, setFeedFiles] = useState<File[]>([]);
  const [isComposerOpen, setIsComposerOpen] = useState(false);
  const [feedPublishError, setFeedPublishError] = useState<string | null>(null);
  /** Пост создан, но часть вложений не загрузилась — показываем предупреждение на странице. */
  const [staffFeedAttachmentWarning, setStaffFeedAttachmentWarning] = useState<string | null>(null);
  const feedFileRef = useRef<HTMLInputElement>(null);
  const toggleLike = useToggleStaffFeedPostLike();
  const updatePost = useUpdateStaffFeedPost();
  const deletePost = useDeleteStaffFeedPost();

  const [editingPost, setEditingPost] = useState<StaffFeedPostResponse | null>(null);
  const [editTitle, setEditTitle] = useState<string>("");
  const [editBody, setEditBody] = useState<string>("");
  const [editFile, setEditFile] = useState<File | null>(null);
  const [editFilePreviewUrl, setEditFilePreviewUrl] = useState<string | null>(null);
  const editFileRef = useRef<HTMLInputElement>(null);

  const [openCommentsByPostId, setOpenCommentsByPostId] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!editingPost) return;
    setEditTitle(editingPost.title ?? "");
    setEditBody(editingPost.body ?? "");
    setEditFile(null);
    setEditFilePreviewUrl(null);
  }, [editingPost?.id]);

  useEffect(() => {
    if (!editFile) {
      setEditFilePreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(editFile);
    setEditFilePreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [editFile]);
  const today = dayjs().format("YYYY-MM-DD");
  const dashboardClinicFilterInitialized = useRef(false);

  useEffect(() => {
    if (dashboardClinicFilterInitialized.current || !currentClinicId) return;
    dashboardClinicFilterInitialized.current = true;
    setSelectedClinicIds([currentClinicId]);
  }, [currentClinicId]);

  const clinicOptions = clinics.map((c) => ({ value: c.id, label: c.name }));

  const { data: reportData, isLoading: reportLoading, isError: reportError, error: reportErr } =
    useAdminReportsDashboardByClinics(
      today,
      "day",
      selectedClinicIds.length > 0 ? selectedClinicIds : null
    );

  const { data: staffPosts, isLoading: staffPostsLoading } = useStaffFeedPosts(20);
  const { data: myStaffProfile } = useMyStaffProfile();
  const createPost = useCreateStaffFeedPost();
  const { data: revenueHunter } = useRevenueHunterSaved(currentClinicId ?? null);
  const { data: adminSession, isLoading: sessionLoading } = useAdminSession();
  const isWideLayout = useMediaQuery("(min-width: 48em)");
  const canPostToStaffFeed = adminSession?.permissions?.includes("manage_staff_collab") ?? false;
  /** Выручка на ленте: владелец или связка маркетинг+финансы (не линейный admin без finance). */
  const canViewRevenueDashboard =
    (adminSession?.roles?.includes("owner") ?? false) ||
    ((adminSession?.permissions?.includes("view_marketing_analytics") ?? false) &&
      (adminSession?.permissions?.includes("view_finance") ?? false));

  const unreadAttentionCount = useMemo(
    () =>
      (staffPosts ?? []).filter(
        (post) => post.is_announcement && post.requires_ack && !post.acknowledged_by_me
      ).length,
    [staffPosts]
  );
  const hasUnreadAttention = unreadAttentionCount > 0;

  const isLoading = reportLoading;
  const isError = reportError;
  const error = reportErr;

  const myAdminIdForComposer = getAdminId();
  const composerDisplayName = useMemo(() => {
    const fromProfile = myStaffProfile?.full_name?.trim();
    if (fromProfile) return fromProfile;
    if (!myAdminIdForComposer || !staffPosts?.length) return t("staffFallback");
    const post = staffPosts.find((x) => x.author.id === myAdminIdForComposer);
    return post?.author.full_name?.trim() || t("staffFallback");
  }, [myStaffProfile?.full_name, staffPosts, myAdminIdForComposer, t]);

  const feedWallPosts = useMemo(() => {
    const list = staffPosts ?? [];
    return list
      .filter((p) => !p.is_announcement)
      .slice()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [staffPosts]);

  useLayoutEffect(() => {
    composerDraftPersistReady.current = false;
    setFeedFiles([]);
    if (feedFileRef.current) feedFileRef.current.value = "";
    try {
      const raw = sessionStorage.getItem(composerDraftStorageKey);
      if (raw) {
        const d = JSON.parse(raw) as { title?: string; body?: string };
        setFeedTitle(typeof d.title === "string" ? d.title : "");
        setFeedBody(typeof d.body === "string" ? d.body : "");
      } else {
        setFeedTitle("");
        setFeedBody("");
      }
    } catch {
      /* ignore */
    }
    composerDraftPersistReady.current = true;
  }, [composerDraftStorageKey]);

  useEffect(() => {
    if (!composerDraftPersistReady.current) return;
    try {
      const empty = !feedTitle.trim() && !feedBody.trim() && feedFiles.length === 0;
      if (empty) {
        sessionStorage.removeItem(composerDraftStorageKey);
        return;
      }
      sessionStorage.setItem(
        composerDraftStorageKey,
        JSON.stringify({
          title: feedTitle,
          body: feedBody,
          fileNames: feedFiles.map((f) => f.name),
        })
      );
    } catch {
      /* ignore */
    }
  }, [feedTitle, feedBody, feedFiles, composerDraftStorageKey]);

  useEffect(() => {
    setOpenCommentsByPostId((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const p of feedWallPosts) {
        if ((p.comments_count ?? 0) > 0 && next[p.id] === undefined) {
          next[p.id] = true;
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [feedWallPosts]);

  const discardComposerDraft = useCallback(() => {
    try {
      sessionStorage.removeItem(composerDraftStorageKey);
    } catch {
      /* ignore */
    }
    setFeedTitle("");
    setFeedBody("");
    setFeedFiles([]);
    if (feedFileRef.current) feedFileRef.current.value = "";
  }, [composerDraftStorageKey]);

  const publishPost = () => {
    const body = feedBody.trim();
    if (!body) return;
    const filesToUpload = [...feedFiles];
    setFeedPublishError(null);
    createPost.mutate(
      { title: feedTitle.trim() || null, body },
      {
        onSuccess: async (post) => {
          try {
            sessionStorage.removeItem(composerDraftStorageKey);
          } catch {
            /* ignore */
          }
          setFeedTitle("");
          setFeedBody("");
          setFeedFiles([]);
          if (feedFileRef.current) feedFileRef.current.value = "";
          const failedFileNames: string[] = [];
          for (const f of filesToUpload) {
            try {
              const fd = new FormData();
              fd.append("file", f);
              await api.postFormData<unknown>(
                `/v1/admin/staff/feed/posts/${post.id}/attachments`,
                fd
              );
            } catch (e) {
              console.error("feed attachment upload", e);
              failedFileNames.push(f.name);
            }
          }
          if (failedFileNames.length > 0) {
            setStaffFeedAttachmentWarning(
              failedFileNames.length === 1
                ? t("attachmentWarnOne", { name: failedFileNames[0] })
                : t("attachmentWarnMany", { names: failedFileNames.join(", ") })
            );
          } else {
            setStaffFeedAttachmentWarning(null);
          }
          setFeedPublishError(null);
          setIsComposerOpen(false);
        },
        onError: (err: unknown) => {
          setFeedPublishError(
            err instanceof ApiErrorWithCode
              ? err.message
              : t("publishFailed")
          );
        },
      }
    );
  };

  if (isLoading) {
    return (
      <Stack gap="lg">
        <ContextBar title={t("title")} />
        {clinics.length > 0 ? (
          <Box maw={750}>
            <MultiSelect
              label={t("clinics")}
              placeholder={t("clinicsPlaceholder")}
              data={clinicOptions}
              value={selectedClinicIds}
              onChange={setSelectedClinicIds}
              searchable
              clearable
            />
          </Box>
        ) : null}
        <Text size="sm" c="dimmed">
          {t("backendHint")}
        </Text>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col span={{ base: 12, md: 7 }}>
            <PageSkeleton variant="table" rows={4} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 5 }}>
            <PageSkeleton variant="table" rows={6} />
          </Grid.Col>
        </Grid>
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack gap="lg">
        <ContextBar title={t("title")} />
        {clinics.length > 0 ? (
          <Box maw={750}>
            <MultiSelect
              label={t("clinics")}
              placeholder={t("clinicsPlaceholder")}
              data={clinicOptions}
              value={selectedClinicIds}
              onChange={setSelectedClinicIds}
              searchable
              clearable
            />
          </Box>
        ) : null}
        <QueryErrorAlert error={error} />
        <Text size="sm" c="dimmed">
          {t("backendHint")}
        </Text>
      </Stack>
    );
  }

  const data = reportData;
  const emptyH = parseHours(data?.empty_slot_hours);
  const pulse = data?.day_pulse_score ?? 50;
  const requestsCount = data?.chat_writers_count ?? 0;

  return (
    <Stack gap="md">
      <ContextBar title={t("title")} />

      {staffFeedAttachmentWarning ? (
        <Alert
          color="orange"
          variant="light"
          title={t("attachmentWarningTitle")}
          withCloseButton
          onClose={() => setStaffFeedAttachmentWarning(null)}
        >
          {staffFeedAttachmentWarning}
        </Alert>
      ) : null}

      {clinics.length > 0 ? (
        <Box maw={750}>
          <MultiSelect
            label={t("clinics")}
            placeholder={t("clinicsPlaceholder")}
            data={clinicOptions}
            value={selectedClinicIds}
            onChange={setSelectedClinicIds}
            searchable
            clearable
          />
        </Box>
      ) : null}

      <Group justify="space-between" align="center" wrap="wrap">
        <Button
          component={Link}
          to={ROUTE_PATHS.admin.attention}
          variant={hasUnreadAttention ? "filled" : "light"}
          color={hasUnreadAttention ? "orange" : "slate"}
          leftSection={<IconAlertTriangle size={18} />}
          className={hasUnreadAttention ? "admin-emergency-blink" : undefined}
        >
          {unreadAttentionCount > 0
            ? t("priorityMessagesCount", { count: unreadAttentionCount })
            : t("priorityMessages")}
        </Button>
      </Group>

      <Group align="flex-start" gap="lg" wrap="wrap" justify="space-between">
        <Paper
          withBorder
          radius="md"
          p="md"
          bg="white"
          style={{ flex: "1 1 360px", maxWidth: 750, minWidth: 0, borderColor: "var(--mantine-color-gray-2)" }}
        >
        <Box style={{ width: "100%", minWidth: 0 }}>
          <Box
            id="clinic-wall"
            style={
              isWideLayout
                ? {
                    maxHeight: "calc(100vh - 220px)",
                    overflowY: "auto",
                    paddingRight: 6,
                    paddingBottom: "var(--mantine-spacing-lg)",
                  }
                : { paddingBottom: "var(--mantine-spacing-lg)" }
            }
          >
            <Stack gap="md" pr="xs">
              {canPostToStaffFeed && !sessionLoading ? (
                <Paper withBorder radius="md" p="sm" bg="white">
                  <UnstyledButton
                    type="button"
                    w="100%"
                    onClick={() => {
                      setFeedPublishError(null);
                      setStaffFeedAttachmentWarning(null);
                      setIsComposerOpen(true);
                    }}
                    style={{ textAlign: "left", cursor: "pointer" }}
                    aria-label={t("composeAria")}
                  >
                    <Group wrap="nowrap" gap="sm" align="center">
                      <Avatar
                        size="md"
                        radius="xl"
                        color="slate"
                        variant="light"
                        src={myStaffProfile?.avatar_url ?? undefined}
                        alt=""
                      >
                        {staffInitials(composerDisplayName)}
                      </Avatar>
                      <Box
                        style={{
                          flex: 1,
                          minWidth: 0,
                          borderRadius: 9999,
                          padding: "10px 14px",
                          background: "var(--mantine-color-gray-1)",
                          border: "1px solid var(--mantine-color-gray-3)",
                        }}
                      >
                        <Text size="sm" c="dimmed">
                          {t("composePlaceholder")}
                        </Text>
                      </Box>
                    </Group>
                  </UnstyledButton>
                </Paper>
              ) : null}

              {!sessionLoading && !canPostToStaffFeed ? (
                <Text size="xs" c="dimmed" maw={480}>
                  {t("noPostPermission")}
                </Text>
              ) : null}

              {staffPostsLoading ? (
                <PageSkeleton variant="table" rows={2} />
              ) : feedWallPosts.length === 0 ? (
                <EmptyState
                  title={t("emptyTitle")}
                  description={t("emptyHint")}
                />
              ) : (
                <Stack gap="md">
                  {feedWallPosts.map((p) => (
                      <Paper
                        key={p.id}
                        withBorder
                        radius="md"
                        p={0}
                        bg="white"
                        styles={{ root: { borderColor: "var(--mantine-color-gray-2)" } }}
                      >
                        <Stack gap={0}>
                          <Box p="md">
                            <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
                              <Group align="flex-start" gap="sm" wrap="nowrap" style={{ flex: 1, minWidth: 0 }}>
                                <Avatar size="md" radius="xl" color="gray.5" variant="light">
                                  {staffInitials(p.author.full_name)}
                                </Avatar>
                                <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                                  <Text size="sm" fw={500} lineClamp={2}>
                                    <PersonNameLink
                                      kind="staff"
                                      id={p.author.id}
                                      label={p.author.full_name}
                                      size="sm"
                                    />
                                  </Text>
                                  <Text size="xs" c="dimmed">
                                    {new Date(p.created_at).toLocaleString(listLocale)}
                                  </Text>
                                  {p.title ? (
                                    <Text size="sm" fw={600} c="gray.9">
                                      {p.title}
                                    </Text>
                                  ) : null}
                                  <Text size="sm" style={{ whiteSpace: "pre-wrap" }} maw="100%">
                                    <AppleEmojiRichText text={p.body ?? ""} />
                                  </Text>
                                </Stack>
                              </Group>
                              {canPostToStaffFeed ? (
                                <Menu position="bottom-end" withinPortal>
                                  <Menu.Target>
                                    <ActionIcon variant="subtle" color="gray" size="sm" aria-label={t("postActions")}>
                                      <IconDots size={18} stroke={1.5} />
                                    </ActionIcon>
                                  </Menu.Target>
                                  <Menu.Dropdown>
                                    <Menu.Item
                                      onClick={() => {
                                        setEditingPost(p);
                                      }}
                                    >
                                      {t("edit")}
                                    </Menu.Item>
                                    <Menu.Item
                                      color="red"
                                      disabled={deletePost.isPending}
                                      onClick={() => {
                                        const ok = window.confirm(t("deletePostConfirm"));
                                        if (!ok) return;
                                        void deletePost.mutateAsync(p.id).then(() => {
                                          setEditingPost(null);
                                        });
                                      }}
                                    >
                                      {t("delete")}
                                    </Menu.Item>
                                  </Menu.Dropdown>
                                </Menu>
                              ) : null}
                            </Group>
                            {(p.attachments ?? []).length > 0 ? (
                              <Stack gap="xs" mt="sm">
                                {(p.attachments ?? []).map((att) => (
                                  <StaffFeedAttachmentPreview key={att.id} attachment={att} />
                                ))}
                              </Stack>
                            ) : null}
                          </Box>

                          <Group gap="xs" align="center" px="md" pb="sm" pt={0} wrap="wrap">
                            <Button
                              variant="subtle"
                              color="gray"
                              size="sm"
                              aria-label={
                                p.liked_by_me
                                  ? t("likeOn", { count: p.likes_count ?? 0 })
                                  : t("likeOff", { count: p.likes_count ?? 0 })
                              }
                              aria-pressed={Boolean(p.liked_by_me)}
                              leftSection={
                                <IconHeart
                                  size={18}
                                  stroke={1.5}
                                  style={{
                                    color: p.liked_by_me
                                      ? "var(--mantine-color-pink-6)"
                                      : "var(--mantine-color-gray-6)",
                                  }}
                                />
                              }
                              loading={toggleLike.isPending && toggleLike.variables === p.id}
                              onClick={() => toggleLike.mutate(p.id)}
                            >
                              {p.likes_count ?? 0}
                            </Button>
                            <Button
                              variant="subtle"
                              color="gray"
                              size="sm"
                              aria-label={t("commentsAria", { count: p.comments_count ?? 0 })}
                              aria-expanded={Boolean(openCommentsByPostId[p.id])}
                              aria-controls={`staff-feed-comments-${p.id}`}
                              leftSection={<IconMessageCircle size={18} stroke={1.5} />}
                              onClick={() =>
                                setOpenCommentsByPostId((prev) => ({
                                  ...prev,
                                  [p.id]: !prev[p.id],
                                }))
                              }
                              styles={{
                                section: {
                                  color: openCommentsByPostId[p.id]
                                    ? "var(--mantine-color-gray-9)"
                                    : undefined,
                                },
                              }}
                            >
                              {typeof p.comments_count === "number"
                                ? t("commentsCount", { count: p.comments_count })
                                : t("comments")}
                            </Button>
                          </Group>

                          <StaffFeedPostComments
                            postId={p.id}
                            isOpen={Boolean(openCommentsByPostId[p.id])}
                            regionId={`staff-feed-comments-${p.id}`}
                          />
                        </Stack>
                      </Paper>
                    ))}
                </Stack>
              )}
            </Stack>
          </Box>
        </Box>
        </Paper>

        <Box
          w={350}
          maw="100%"
          style={{
            flexShrink: 0,
            position: "sticky",
            top: 4,
            alignSelf: "flex-start",
            background: "transparent",
          }}
        >
          <Stack gap="sm">
            <Paper radius="md" bg="gray.0" p="sm" style={{ border: "1px solid var(--mantine-color-gray-2)" }}>
              <Group gap={6} mb={2} wrap="nowrap">
                <ThemeIcon variant="light" color="slate" size="sm" radius="md">
                  <IconCalendarStats size={16} />
                </ThemeIcon>
                <Text size="10px" c="dimmed" tt="uppercase" fw={600} lineClamp={2}>
                  {t("metricVisits")}
                </Text>
              </Group>
              <Text fw={700} fz="md" c="gray.9">
                {data?.bookings_completed ?? 0}
              </Text>
              <Text size="10px" c="dimmed" mt={0} lineClamp={2}>
                {t("metricVisitsHint")}
              </Text>
            </Paper>

            <Paper radius="md" bg="gray.0" p="sm" style={{ border: "1px solid var(--mantine-color-gray-2)" }}>
              <Group gap={6} mb={2} wrap="nowrap">
                <ThemeIcon variant="light" color="slate" size="sm" radius="md">
                  <IconUsers size={16} />
                </ThemeIcon>
                <Text size="10px" c="dimmed" tt="uppercase" fw={600} lineClamp={2}>
                  {t("metricNewPatients")}
                </Text>
              </Group>
              <Text fw={700} fz="md" c="gray.9">
                {data?.new_patients ?? 0}
              </Text>
              <Text size="10px" c="dimmed" mt={0} lineClamp={2}>
                {t("metricNewPatientsHint")}
              </Text>
            </Paper>

            <Paper radius="md" bg="gray.0" p="sm" style={{ border: "1px solid var(--mantine-color-gray-2)" }}>
              <Group gap={6} mb={2} wrap="nowrap">
                <ThemeIcon variant="light" color="slate" size="sm" radius="md">
                  <IconX size={16} />
                </ThemeIcon>
                <Text size="10px" c="dimmed" tt="uppercase" fw={600} lineClamp={2}>
                  {t("metricCancels")}
                </Text>
              </Group>
              <Text fw={700} fz="md" c="gray.9">
                {(data?.bookings_cancelled ?? 0) + (data?.bookings_no_show ?? 0)}
              </Text>
              <Text size="10px" c="dimmed" mt={0} lineClamp={2}>
                {t("metricCancelsHint", {
                  cancelled: data?.bookings_cancelled ?? 0,
                  noShow: data?.bookings_no_show ?? 0,
                })}
              </Text>
            </Paper>

            {canViewRevenueDashboard ? (
              <Paper radius="md" bg="gray.0" p="sm" style={{ border: "1px solid var(--mantine-color-gray-2)" }}>
                <Group gap={6} mb={2} wrap="nowrap">
                  <ThemeIcon variant="light" color="slate" size="sm" radius="md">
                    <IconMail size={16} />
                  </ThemeIcon>
                  <Text size="10px" c="dimmed" tt="uppercase" fw={600} lineClamp={2}>
                    {t("metricRequests")}
                  </Text>
                </Group>
                <Text fw={700} fz="md" c="gray.9">
                  {requestsCount}
                </Text>
                <Text size="10px" c="dimmed" mt={0} lineClamp={2}>
                  {t("metricRequestsHint")}
                </Text>
              </Paper>
            ) : null}

            <Paper radius="md" bg="gray.0" p="sm" style={{ border: "1px solid var(--mantine-color-gray-2)" }}>
              <Group gap={6} mb={2} wrap="nowrap">
                <ThemeIcon variant="light" color="slate" size="sm" radius="md">
                  <IconStack2 size={16} />
                </ThemeIcon>
                <Text size="10px" c="dimmed" tt="uppercase" fw={600} lineClamp={2}>
                  {t("metricDensity")}
                </Text>
              </Group>
              <Progress value={pulse} size="xs" radius="md" color="slate" mb={2} />
              <Text fw={600} fz="md" c="gray.9">
                {pulse} / 100
              </Text>
              <Text size="10px" c="dimmed" mt={0} lineClamp={2}>
                {t("metricDensityHint")}
              </Text>
            </Paper>

            <Paper radius="md" bg="gray.0" p="sm" style={{ border: "1px solid var(--mantine-color-gray-2)" }}>
              <Group gap={6} mb={2} wrap="nowrap">
                <ThemeIcon variant="light" color="slate" size="sm" radius="md">
                  <IconClock size={16} />
                </ThemeIcon>
                <Text size="10px" c="dimmed" tt="uppercase" fw={600} lineClamp={2}>
                  {t("metricEmptyWindows")}
                </Text>
              </Group>
              <Text fw={700} fz="md" c="gray.9">
                {t("metricEmptyHours", { hours: emptyH.toFixed(1) })}
              </Text>
              <Text size="10px" c="dimmed" mt={0} lineClamp={2}>
                {t("metricEmptyHint")}
              </Text>
            </Paper>

            {revenueHunter && isRevenueHunterEnabled(revenueHunter) && canViewRevenueDashboard ? (
              <Paper radius="md" bg="gray.0" p="sm" style={{ border: "1px solid var(--mantine-color-gray-2)" }}>
                <Group gap="xs" mb={4} wrap="nowrap">
                  <ThemeIcon variant="light" color="slate" size="sm" radius="md">
                    <IconRobot size={16} />
                  </ThemeIcon>
                  <Text size="10px" c="dimmed" tt="uppercase" fw={600} lineClamp={3}>
                    {t("revenueRetained")}{" "}
                    {feedRevenuePeriodLabel(revenueHunter.period)}
                  </Text>
                </Group>
                <Text fw={700} fz="lg" c="slate.8">
                  {revenueHunter.amount} ₽
                </Text>
              </Paper>
            ) : null}
          </Stack>
        </Box>
      </Group>

      <GlassModal
        opened={isComposerOpen}
        onClose={() => {
          setIsComposerOpen(false);
          setFeedPublishError(null);
        }}
        title={t("newPost")}
        size="xl"
        padding="md"
        styles={{
          content: {
            width: "calc(100vw - 2rem)",
            maxWidth: "calc(100vw - 2rem)",
            maxHeight: "calc(100vh - 2rem)",
          },
          body: {
            maxHeight: "calc(100vh - 7rem)",
            overflowY: "auto",
          },
        }}
      >
        <Stack gap="sm">
          {feedPublishError ? (
            <Alert color="red" variant="light" title={t("publishFailedTitle")} onClose={() => setFeedPublishError(null)} withCloseButton>
              {feedPublishError}
            </Alert>
          ) : null}
          <TextInput
            label={t("topic")}
            placeholder={t("topicPlaceholder")}
            value={feedTitle}
            onChange={(e) => setFeedTitle(e.currentTarget.value)}
          />
          <Input.Wrapper label={t("body")}>
            <AppleEmojiOverlayTextarea
              placeholder={t("bodyPlaceholder")}
              minRows={16}
              value={feedBody}
              onChange={(e) => setFeedBody(e.currentTarget.value)}
            />
          </Input.Wrapper>
          <Group gap="xs">
            <input
              ref={feedFileRef}
              type="file"
              multiple
              style={{ display: "none" }}
              onChange={(e) => {
                const list = e.target.files;
                if (!list?.length) return;
                setFeedFiles(Array.from(list));
              }}
            />
            <ActionIcon
              variant="subtle"
              color="gray"
              aria-label={t("attachFiles")}
              onClick={() => feedFileRef.current?.click()}
            >
              <IconPaperclip size={20} stroke={1.5} />
            </ActionIcon>
            <ActionIcon
              variant="subtle"
              color="gray"
              aria-label={t("ariaImage")}
              onClick={() => feedFileRef.current?.click()}
            >
              <IconPhoto size={20} stroke={1.5} />
            </ActionIcon>
            <ActionIcon
              variant="subtle"
              color="gray"
              aria-label={t("audioSoon")}
              title={t("audioSoonTitle")}
              disabled
              styles={{ root: { opacity: 0.45 } }}
            >
              <IconMicrophone size={20} stroke={1.5} />
            </ActionIcon>
            {feedFiles.length > 0 ? (
              <Text size="xs" c="dimmed">
                {t("filesQueued", { count: feedFiles.length })}
              </Text>
            ) : null}
          </Group>
          <Group justify="flex-end" mt="md">
            <Button
              variant="default"
              onClick={() => {
                discardComposerDraft();
                setFeedPublishError(null);
                setIsComposerOpen(false);
              }}
              disabled={createPost.isPending}
            >
              {t("cancel")}
            </Button>
            <Button
              color="slate"
              variant="filled"
              onClick={() => void publishPost()}
              loading={createPost.isPending}
              disabled={!feedBody.trim()}
            >
              {t("publish")}
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        opened={!!editingPost}
        onClose={() => setEditingPost(null)}
        title={t("editPost")}
        size="xl"
        padding="md"
        styles={{
          content: {
            width: "calc(100vw - 2rem)",
            maxWidth: "calc(100vw - 2rem)",
            maxHeight: "calc(100vh - 2rem)",
          },
          body: {
            maxHeight: "calc(100vh - 7rem)",
            overflowY: "auto",
          },
        }}
      >
        {editingPost ? (
          <Stack gap="md">
            <TextInput
              label={t("titleLabel")}
              placeholder={t("titleOptional")}
              value={editTitle}
              onChange={(e) => setEditTitle(e.currentTarget.value)}
            />
            <Input.Wrapper label={t("body")}>
              <AppleEmojiOverlayTextarea
                value={editBody}
                onChange={(e) => setEditBody(e.currentTarget.value)}
                minRows={14}
              />
            </Input.Wrapper>

            <Text size="sm" fw={700} c="gray.9">
              {t("attachmentSection")}
            </Text>
            {editingPost.attachments?.length ? (
              <Stack gap="xs">
                {editingPost.attachments.slice(0, 3).map((att) => (
                  <StaffFeedAttachmentPreview key={att.id} attachment={att} />
                ))}
              </Stack>
            ) : (
              <Text size="xs" c="dimmed">
                {t("noAttachments")}
              </Text>
            )}

            <input
              ref={editFileRef}
              type="file"
              accept="image/*,audio/*,video/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                setEditFile(f);
              }}
            />
            <Group justify="space-between" align="center">
              <Button
                {...STAFF_FEED_CHROME.subtleButton}
                size="xs"
                onClick={() => editFileRef.current?.click()}
                disabled={updatePost.isPending}
              >
                {t("chooseFile")}
              </Button>
              {editFile ? (
                <Text size="xs" c="dimmed">
                  {editFile.name}
                </Text>
              ) : null}
            </Group>

            {editFilePreviewUrl && (editFile?.type || "").toLowerCase().startsWith("image/") ? (
              <img
                src={editFilePreviewUrl}
                alt={t("previewAlt")}
                style={{ width: "100%", maxHeight: 320, objectFit: "contain", borderRadius: "var(--radius-md)" }}
              />
            ) : null}
            {editFilePreviewUrl && (editFile?.type || "").toLowerCase().startsWith("audio/") ? (
              <ChatInlineAudioPlayer src={editFilePreviewUrl} style={{ width: "100%" }} />
            ) : null}
            {editFilePreviewUrl && (editFile?.type || "").toLowerCase().startsWith("video/") ? (
              <video
                controls
                src={editFilePreviewUrl}
                style={{ width: "100%", maxHeight: 360, objectFit: "contain", borderRadius: "var(--radius-md)" }}
              />
            ) : null}

            <Group justify="flex-end" mt="xs">
              <Button variant="default" onClick={() => setEditingPost(null)} disabled={updatePost.isPending}>
                {t("cancel")}
              </Button>
              <Button
                {...STAFF_FEED_CHROME.primaryButton}
                loading={updatePost.isPending}
                onClick={() => {
                  const title = editTitle.trim() ? editTitle : null;
                  updatePost.mutate(
                    { postId: editingPost.id, title, body: editBody, file: editFile },
                    {
                      onSuccess: () => {
                        setEditingPost(null);
                      },
                    }
                  );
                }}
                disabled={!editBody.trim()}
              >
                {t("save")}
              </Button>
            </Group>
          </Stack>
        ) : null}
      </GlassModal>

      <style>{`
        @keyframes admin-emergency-blink {
          0%, 100% { opacity: 1; box-shadow: 0 0 0 0 var(--admin-emergency-blink-shadow-outer); }
          50% { opacity: 0.92; box-shadow: 0 0 0 6px var(--admin-emergency-blink-shadow-ring); }
        }
        .admin-emergency-blink {
          animation: admin-emergency-blink 1.2s ease-in-out infinite;
        }
      `}</style>
    </Stack>
  );
}
