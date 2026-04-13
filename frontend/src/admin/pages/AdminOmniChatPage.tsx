import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ActionIcon,
  Badge,
  Box,
  Button,
  Divider,
  Flex,
  Group,
  Loader,
  Menu,
  Modal,
  MultiSelect,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
  Tooltip,
  rem,
} from "@mantine/core";
import { useHotkeys } from "@mantine/hooks";
import {
  IconBrandTelegram,
  IconBrandWhatsapp,
  IconBrandVk,
  IconQuote,
  IconCornerUpLeft,
  IconMail,
  IconPaperclip,
  IconPhoto,
  IconSearch,
  IconSend,
  IconX,
} from "@tabler/icons-react";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  useAdminOmniChatDetail,
  useAdminOmniChatMessagesInfinite,
  useAdminOmniChats,
  getAdminClinicChatAttachmentBlob,
  getAdminOmniAttachmentBlob,
  useSendAdminOmniMessage,
  useSendAdminOmniMessageWithFile,
  useOmniChatAnalytics,
  useOmniQuickReplies,
  OMNI_CHAT_AI_MODES,
  useUpdateOmniChatAiMode,
  useResolveAdminOmniChat,
  useAdminOmniChatPresence,
  useClaimAdminOmniChat,
} from "@/hooks/useAdminOmniChat";
import { AppleEmojiOverlayTextarea } from "@/shared/ui";
import { EmojiMartPopoverPicker } from "@/shared/ui/EmojiMartPopoverPicker";
import { VoiceNoteRecorderButton } from "@/shared/ui/VoiceNoteRecorderButton";
import { OmniMessageRichBody } from "@/shared/OmniMessageRichBody";
import {
  ADMIN_CHAT_MESSAGES_REGION,
  adminChatOmniClientInboundBubbleStyle,
  adminChatOmniOutboundBubbleStyle,
} from "@/shared/adminChatChrome";
import { useQueryClient } from "@tanstack/react-query";
import { useAdminSession } from "@/hooks/useAdminSession";
import { getAdminId } from "@/api/client";

function ChannelIcon({ type }: { type: string }) {
  const t = (type || "").toUpperCase();
  if (t === "TELEGRAM_BOT") return <IconBrandTelegram size={14} />;
  if (t === "WHATSAPP_BUSINESS") return <IconBrandWhatsapp size={14} />;
  if (t === "VK_BOT") return <IconBrandVk size={14} />;
  if (t === "EMAIL_INBOX") return <IconMail size={14} />;
  return null;
}

function channelBrandColor(type: string): string {
  const t = (type || "").toUpperCase();
  if (t === "TELEGRAM_BOT") return "var(--mantine-color-blue-6)";
  if (t === "WHATSAPP_BUSINESS") return "var(--mantine-color-green-6)";
  if (t === "VK_BOT") return "var(--mantine-color-indigo-6)";
  if (t === "EMAIL_INBOX") return "var(--mantine-color-gray-6)";
  return "var(--mantine-color-gray-6)";
}

function ChannelTypeRow({ types }: { types: string[] }) {
  const uniq = Array.from(new Set(types.map((x) => String(x || "").toUpperCase()).filter(Boolean)));
  if (!uniq.length) return null;
  return (
    <Group gap={6} wrap="nowrap">
      {uniq.slice(0, 5).map((t) => (
        <Tooltip key={t} label={t}>
          <Box style={{ color: "var(--mantine-color-gray-6)", display: "flex", alignItems: "center" }}>
            <ChannelIcon type={t} />
          </Box>
        </Tooltip>
      ))}
    </Group>
  );
}

function toDayKey(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

const dateLabelFmt = new Intl.DateTimeFormat(undefined, { year: "numeric", month: "long", day: "numeric" });
const timeLabelFmt = new Intl.DateTimeFormat(undefined, { hour: "2-digit", minute: "2-digit" });

function formatDayLabel(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return dateLabelFmt.format(d);
}

function formatTimeLabel(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return timeLabelFmt.format(d);
}

function isClosedStatus(status: unknown): boolean {
  return String(status || "").toUpperCase() === "CLOSED";
}

function isContactActor(lastActorType: unknown): boolean {
  const t = String(lastActorType || "").toUpperCase();
  return t === "CONTACT" || t === "CLIENT" || t === "PATIENT";
}

function parseReplyLine(content: string): { messageId: string | null; rest: string } | null {
  const raw = String(content || "");
  const lines = raw.split(/\r?\n/);
  const first = (lines[0] || "").trim();
  if (!/^reply_to:\s+/i.test(first)) return null;
  const messageId = first.replace(/^reply_to:\s+/i, "").trim() || null;
  const rest = lines.slice(1).join("\n").trimStart();
  return { messageId, rest };
}

function OmniWorkPane({
  selectedChatId,
  onSelectChat,
  mineOpen,
  mineClosed,
}: {
  selectedChatId: string | null;
  onSelectChat: (chatId: string) => void;
  mineOpen: any[];
  mineClosed: any[];
}) {
  const [tab, setTab] = useState<"mine" | "closed">("mine");
  const items = tab === "mine" ? mineOpen : mineClosed;

  return (
    <Box
      w={320}
      miw={320}
      style={{
        borderLeft: "1px solid var(--mantine-color-gray-2)",
        backgroundColor: "white",
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
      }}
    >
      <Box p="sm" style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}>
        <Text size="xs" fw={700} tt="uppercase" c="dimmed" style={{ letterSpacing: rem(0.4) }}>
          Мои заявки
        </Text>
        <Tabs value={tab} onChange={(v) => v && setTab(v as any)} variant="pills" mt="xs">
          <Tabs.List grow>
            <Tabs.Tab value="mine">В работе</Tabs.Tab>
            <Tabs.Tab value="closed">Закрытые</Tabs.Tab>
          </Tabs.List>
        </Tabs>
      </Box>
      <ScrollArea style={{ flex: 1 }}>
        <Stack gap={4} p="sm">
          {items.length ? (
            items.map((c: any) => (
              <Paper
                key={c.chat_id}
                p="xs"
                withBorder
                radius="md"
                style={{
                  cursor: "pointer",
                  borderColor:
                    selectedChatId === c.chat_id ? "var(--mantine-color-indigo-4)" : "var(--divider)",
                }}
                onClick={() => onSelectChat(c.chat_id)}
              >
                <Group justify="space-between" align="flex-start" wrap="nowrap" gap="xs">
                  <Stack gap={2} style={{ minWidth: 0 }}>
                      <Group gap={6} wrap="nowrap">
                        <ChannelTypeRow
                          types={(c.channel_types ?? (c.channel_type ? [c.channel_type] : [])) as string[]}
                        />
                        <Text size="sm" fw={600} truncate="end" title={c.contact_name ?? "Без имени"} style={{ minWidth: 0 }}>
                          {c.contact_name ?? "Без имени"}
                        </Text>
                      </Group>
                    <Text size="xs" c="dimmed" truncate="end">
                      {c.contact_primary_phone ?? ""}
                    </Text>
                  </Stack>
                  <Badge size="xs" variant="light" color="gray">
                    {String(c.status || "").toUpperCase() === "CLOSED" ? "закрыто" : "в работе"}
                  </Badge>
                </Group>
              </Paper>
            ))
          ) : (
            <Text size="sm" c="dimmed">
              {tab === "mine" ? "Нет чатов в работе." : "Нет закрытых заявок."}
            </Text>
          )}
        </Stack>
      </ScrollArea>
    </Box>
  );
}

export default function AdminOmniChatPage() {
  const qc = useQueryClient();
  const { data: adminSession } = useAdminSession();
  const adminId = useMemo(() => getAdminId(), []);
  const isOwner = Boolean(adminSession?.roles?.includes("owner"));
  const canToggleAi = Boolean(adminSession?.permissions?.includes("omni.inbox.manage"));
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [deepLinkMessageId, setDeepLinkMessageId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [channelTypeFilters, setChannelTypeFilters] = useState<string[]>([]);
  const [leftMode, setLeftMode] = useState<"all" | "new">("all");

  const leftFilters = useMemo(
    () => ({
      search: search || undefined,
      channel_types: channelTypeFilters.length ? channelTypeFilters : undefined,
      page: 1,
      page_size: 200,
    }),
    [search, channelTypeFilters],
  );

  const { data: allChatsData } = useAdminOmniChats(leftFilters);
  const { data: newChatsData } = useAdminOmniChats({
    ...leftFilters,
    status: "WAITING_FOR_OPERATOR",
    assignee: "unassigned",
  });
  const { data: myChatsData } = useAdminOmniChats({ page: 1, page_size: 200, assignee: "me" });

  const leftChats = leftMode === "new" ? (newChatsData?.items ?? []) : (allChatsData?.items ?? []);
  const newCount = newChatsData?.total ?? 0;

  const availableChannelTypes = useMemo(() => {
    const set = new Set<string>();
    for (const c of allChatsData?.items ?? []) {
      for (const t of c.channel_types ?? (c.channel_type ? [c.channel_type] : [])) {
        if (t) set.add(String(t));
      }
    }
    return Array.from(set).sort();
  }, [allChatsData?.items]);

  const myOpenChats = useMemo(
    () => (myChatsData?.items ?? []).filter((c) => String(c.status).toUpperCase() !== "CLOSED"),
    [myChatsData?.items],
  );
  const myClosedChats = useMemo(
    () => (myChatsData?.items ?? []).filter((c) => String(c.status).toUpperCase() === "CLOSED"),
    [myChatsData?.items],
  );

  const { data: chatDetail } = useAdminOmniChatDetail(selectedChatId);
  const { mergedMessages } = useAdminOmniChatMessagesInfinite(selectedChatId, {
    limit: 100,
    include_hidden: false,
  });
  const sendMessage = useSendAdminOmniMessage();
  const sendWithFile = useSendAdminOmniMessageWithFile();
  const resolveChat = useResolveAdminOmniChat();
  const claimChat = useClaimAdminOmniChat();
  const presenceMut = useAdminOmniChatPresence();
  const updateAiMode = useUpdateOmniChatAiMode();
  const { data: quickRepliesData } = useOmniQuickReplies(true);

  const canViewAnalytics = Boolean(adminSession?.permissions?.includes("erp.owner_reports.read"));
  const [analyticsOpen, setAnalyticsOpen] = useState(false);
  const today = useMemo(() => new Date(), []);
  const defaultDateTo = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() + 1);
    return d.toISOString().slice(0, 10);
  }, [today]);
  const defaultDateFrom = useMemo(() => {
    const d = new Date(today);
    d.setDate(d.getDate() - 6);
    return d.toISOString().slice(0, 10);
  }, [today]);
  const [dateFrom, setDateFrom] = useState(defaultDateFrom);
  const [dateTo, setDateTo] = useState(defaultDateTo);
  const analyticsQuery = useOmniChatAnalytics(analyticsOpen && canViewAnalytics, {
    date_from: dateFrom,
    date_to: dateTo,
  });

  const [messageText, setMessageText] = useState("");
  const [replyingTo, setReplyingTo] = useState<{ messageId: string; preview: string } | null>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const centerPaneRef = useRef<HTMLDivElement>(null);
  const messagesViewportRef = useRef<HTMLDivElement | null>(null);
  const shouldStickToBottomRef = useRef(true);
  const scrollTopBeforeResizeRef = useRef<number | null>(null);
  const scrollRestoreRafRef = useRef<number | null>(null);
  const [composerMaxRows, setComposerMaxRows] = useState(12);
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [fileAccept, setFileAccept] = useState<string>("*");
  const [ctxMenu, setCtxMenu] = useState<{
    opened: boolean;
    x: number;
    y: number;
    messageId: string | null;
    messageText: string;
  }>({ opened: false, x: 0, y: 0, messageId: null, messageText: "" });
  const [resolveError, setResolveError] = useState<string | null>(null);

  // Deep-link support: /admin/omni-chat?chat_id=...&message_id=...
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    const cid = url.searchParams.get("chat_id");
    const mid = url.searchParams.get("message_id");
    if (cid && !selectedChatId) {
      setSelectedChatId(cid);
    }
    if (mid) {
      setDeepLinkMessageId(mid);
    }
  }, []);

  const tabId = useMemo(() => {
    try {
      if (typeof window === "undefined") return "tab";
      const key = "omni_chat_tab_id";
      const existing = window.sessionStorage.getItem(key);
      if (existing) return existing;
      const next = `tab_${Math.random().toString(16).slice(2)}_${Date.now().toString(16)}`.slice(0, 64);
      window.sessionStorage.setItem(key, next);
      return next;
    } catch {
      return "tab";
    }
  }, []);

  const draftRef = useRef(false);
  useEffect(() => {
    draftRef.current = Boolean(messageText.trim() || pendingFile);
  }, [messageText, pendingFile]);

  const mkPresenceEventId = useCallback(() => {
    try {
      return (crypto as any)?.randomUUID?.() ?? `${Date.now()}_${Math.random()}`;
    } catch {
      return `${Date.now()}_${Math.random()}`;
    }
  }, []);

  // При открытии диалога без исполнителя — сразу закрепляем за текущим администратором (бэкенд claim).
  useEffect(() => {
    if (!selectedChatId || !chatDetail) return;
    const closed = String(chatDetail.status || "").toUpperCase() === "CLOSED";
    if (closed || chatDetail.assignee_admin_id) return;
    void claimChat.mutate(
      { chatId: selectedChatId },
      {
        onError: () => {
          /* уже занят другим — оставляем как есть */
        },
      },
    );
    // claimChat (react-query) intentionally omitted from dependency list
  }, [selectedChatId, chatDetail?.chat_id, chatDetail?.assignee_admin_id, chatDetail?.status]);

  // Presence lease: OPEN on select + HEARTBEAT while active + CLOSE on unselect/unmount.
  useEffect(() => {
    if (!selectedChatId) return;
    presenceMut.mutate({
      chatId: selectedChatId,
      body: { client_event_id: mkPresenceEventId(), tab_id: tabId, event: "OPEN" },
    });
    const t = window.setInterval(() => {
      presenceMut.mutate({
        chatId: selectedChatId,
        body: { client_event_id: mkPresenceEventId(), tab_id: tabId, event: "HEARTBEAT" },
      });
    }, 30000);
    return () => {
      window.clearInterval(t);
      // UX safety: if there is a draft (text/file), avoid sending CLOSE immediately.
      // Lease will expire by TTL, preventing surprise auto-resolve while user is composing.
      if (!draftRef.current) {
        presenceMut.mutate({
          chatId: selectedChatId,
          body: { client_event_id: mkPresenceEventId(), tab_id: tabId, event: "CLOSE" },
        });
      }
    };
    // presenceMut (react-query) intentionally omitted; effect tracks dialog/tab only
  }, [selectedChatId, tabId, mkPresenceEventId]);

  // Best-effort scroll to deep-linked message when it becomes available in DOM.
  useEffect(() => {
    if (!selectedChatId || !deepLinkMessageId) return;
    // Only try when we have some messages loaded.
    if (!mergedMessages?.length) return;
    let tries = 0;
    let raf = 0;
    const tick = () => {
      tries += 1;
      const el =
        document.getElementById(`omni-msg-${deepLinkMessageId}`) ||
        document.querySelector(`[data-omni-message-id="${CSS.escape(deepLinkMessageId)}"]`);
      if (el && "scrollIntoView" in el) {
        try {
          (el as HTMLElement).scrollIntoView({ block: "center", behavior: "smooth" });
        } catch {
          (el as HTMLElement).scrollIntoView();
        }
        setDeepLinkMessageId(null);
        return;
      }
      if (tries < 16) raf = window.requestAnimationFrame(tick);
    };
    raf = window.requestAnimationFrame(tick);
    return () => {
      if (raf) window.cancelAnimationFrame(raf);
    };
  }, [deepLinkMessageId, mergedMessages?.length, selectedChatId]);

  useEffect(() => {
    setMessageText("");
    setPendingFile(null);
    setAttachError(null);
    setReplyingTo(null);
  }, [selectedChatId]);

  useEffect(() => {
    const recompute = () => {
      const h = centerPaneRef.current?.getBoundingClientRect().height ?? 0;
      if (!h) return;
      const maxPx = Math.max(180, Math.floor(h * 0.33));
      const approxRowPx = 22;
      const next = Math.max(6, Math.min(18, Math.floor(maxPx / approxRowPx)));
      setComposerMaxRows(next);
    };
    recompute();
    window.addEventListener("resize", recompute);
    return () => window.removeEventListener("resize", recompute);
  }, []);

  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const el = messagesViewportRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  const isAtBottom = useCallback(() => {
    const el = messagesViewportRef.current;
    if (!el) return true;
    const threshold = 24;
    const remaining = el.scrollHeight - el.scrollTop - el.clientHeight;
    return remaining <= threshold;
  }, []);

  // Track whether user is reading history (not at bottom).
  useEffect(() => {
    const el = messagesViewportRef.current;
    if (!el) return;
    const onScroll = () => {
      shouldStickToBottomRef.current = isAtBottom();
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => el.removeEventListener("scroll", onScroll as any);
  }, [isAtBottom]);

  // Keep scroll stable when composer / layout height changes.
  useEffect(() => {
    const el = messagesViewportRef.current;
    if (!el) return;
    const obs = new ResizeObserver(() => {
      const viewport = messagesViewportRef.current;
      if (!viewport) return;
      if (shouldStickToBottomRef.current) {
        scrollToBottom("auto");
        return;
      }
      if (scrollTopBeforeResizeRef.current == null) {
        scrollTopBeforeResizeRef.current = viewport.scrollTop;
      }
      if (scrollRestoreRafRef.current) {
        cancelAnimationFrame(scrollRestoreRafRef.current);
      }
      scrollRestoreRafRef.current = requestAnimationFrame(() => {
        const v = messagesViewportRef.current;
        if (v && scrollTopBeforeResizeRef.current != null) {
          v.scrollTop = scrollTopBeforeResizeRef.current;
        }
        scrollTopBeforeResizeRef.current = null;
        scrollRestoreRafRef.current = null;
      });
    });
    obs.observe(el);
    return () => {
      obs.disconnect();
      if (scrollRestoreRafRef.current) cancelAnimationFrame(scrollRestoreRafRef.current);
    };
  }, [scrollToBottom]);

  // When new messages arrive: stick to bottom only if user was at bottom.
  useEffect(() => {
    if (!selectedChatId) return;
    if (!mergedMessages?.length) return;
    if (!shouldStickToBottomRef.current) return;
    scrollToBottom("auto");
  }, [mergedMessages?.length, scrollToBottom, selectedChatId]);

  const canClaim =
    !!chatDetail &&
    !chatDetail.assignee_admin_id &&
    String(chatDetail.status || "").toUpperCase() !== "CLOSED";

  const handleSend = useCallback(() => {
    if (!selectedChatId) return;
    setAttachError(null);
    if (pendingFile) {
      const bodyRaw = messageText.trim();
      const body = replyingTo ? `reply_to: ${replyingTo.messageId}\n${bodyRaw}` : bodyRaw;
      sendWithFile.mutate(
        { chatId: selectedChatId, body, file: pendingFile },
        {
          onSuccess: () => {
            setMessageText("");
            setReplyingTo(null);
            setPendingFile(null);
            qc.invalidateQueries({ queryKey: ["admin-omni-chat-messages", selectedChatId] });
            qc.invalidateQueries({ queryKey: ["admin-omni-chat-detail", selectedChatId] });
            qc.invalidateQueries({ queryKey: ["admin-omni-chats"] });
            queueMicrotask(() => composerRef.current?.focus());
          },
          onError: () => setAttachError("Не удалось отправить файл"),
        },
      );
      return;
    }
    const content = messageText.trim();
    if (!content) return;
    const payload = replyingTo ? `reply_to: ${replyingTo.messageId}\n${content}` : content;
    sendMessage.mutate(
      { chatId: selectedChatId, content: payload },
      {
        onSuccess: () => {
          setMessageText("");
          setReplyingTo(null);
          qc.invalidateQueries({ queryKey: ["admin-omni-chat-messages", selectedChatId] });
          qc.invalidateQueries({ queryKey: ["admin-omni-chat-detail", selectedChatId] });
          qc.invalidateQueries({ queryKey: ["admin-omni-chats"] });
          queueMicrotask(() => composerRef.current?.focus());
        },
      },
    );
  }, [messageText, pendingFile, qc, replyingTo, selectedChatId, sendMessage, sendWithFile]);

  const canResolveSelected = Boolean(
    selectedChatId &&
      chatDetail &&
      String(chatDetail.status || "").toUpperCase() !== "CLOSED" &&
      (isOwner || (!!adminId && chatDetail.assignee_admin_id === adminId)),
  );

  const getClinicChatBlob = useCallback((conversationId: string, attachmentId: string) => {
    return getAdminClinicChatAttachmentBlob(conversationId, attachmentId);
  }, []);

  const getOmniBlobForMessage = useCallback(
    (messageId: string, attachmentId: string) => {
      if (!selectedChatId) return Promise.reject(new Error("no chat"));
      return getAdminOmniAttachmentBlob(selectedChatId, messageId, attachmentId);
    },
    [selectedChatId],
  );

  const pickFile = useCallback(
    (accept: string) => {
      setFileAccept(accept);
      queueMicrotask(() => fileInputRef.current?.click());
    },
    [],
  );

  const applyQuickReply = useCallback((body: string) => {
    if (!body) return;
    setMessageText((prev) => {
      const next = prev ? `${prev}${prev.endsWith("\n") ? "" : "\n"}${body}` : body;
      return next;
    });
    queueMicrotask(() => composerRef.current?.focus());
  }, []);

  const startReply = useCallback(
    (messageId: string) => {
      const msg = (mergedMessages as any[]).find((x) => String(x.id) === String(messageId));
      const raw = msg ? String(msg.content || "") : "";
      const meta = parseReplyLine(raw);
      const preview = String((meta ? meta.rest : raw) || "")
        .trim()
        .replace(/\s+/g, " ")
        .slice(0, 180) || "Сообщение";
      setReplyingTo({ messageId, preview });
      queueMicrotask(() => composerRef.current?.focus());
    },
    [mergedMessages],
  );

  useHotkeys([["mod+enter", () => handleSend()]]);

  const finishOmniTicket = useCallback(async () => {
    if (!selectedChatId) return;
    setResolveError(null);
    try {
      await presenceMut.mutateAsync({
        chatId: selectedChatId,
        body: { client_event_id: mkPresenceEventId(), tab_id: tabId, event: "CLOSE" },
      });
    } catch {
      setResolveError("Не удалось закрыть сессию присутствия. Уберите черновик в поле ввода и повторите.");
      return;
    }
    try {
      await resolveChat.mutateAsync({ chatId: selectedChatId });
    } catch (e) {
      if (isOwner) {
        try {
          await resolveChat.mutateAsync({ chatId: selectedChatId, force: true });
        } catch {
          setResolveError(e instanceof Error ? e.message : "Не удалось сохранить снимок в журнал лидов.");
          return;
        }
      } else {
        setResolveError(e instanceof Error ? e.message : "Не удалось завершить заявку.");
        return;
      }
    }
    setSelectedChatId(null);
  }, [selectedChatId, isOwner, presenceMut, resolveChat, mkPresenceEventId, tabId]);

  const closeOmniDialogOnly = useCallback(() => {
    setResolveError(null);
    setSelectedChatId(null);
  }, []);

  return (
    <Stack gap={0} style={{ height: "100%", minHeight: 0 }}>
      <Box px="md" pt="sm" style={{ flexShrink: 0 }}>
        <ContextBar
          title="Omni‑чат — только работа"
          actions={
            <Group gap="xs">
              {canViewAnalytics ? (
                <Button size="xs" variant="subtle" color="gray" onClick={() => setAnalyticsOpen(true)}>
                  Аналитика
                </Button>
              ) : null}
            </Group>
          }
        />
      </Box>

      <Flex style={{ flex: 1, minHeight: 0 }}>
        {/* Left inbox */}
        <Box
          w={300}
          miw={300}
          style={{
            borderRight: "1px solid var(--mantine-color-gray-2)",
            background: "white",
            display: "flex",
            flexDirection: "column",
            minHeight: 0,
            overflow: "hidden",
          }}
        >
          <Box p="sm" style={{ borderBottom: "1px solid var(--mantine-color-gray-2)" }}>
            <Group justify="space-between" wrap="nowrap" gap="xs">
              <Text size="xs" fw={700} tt="uppercase" c="dimmed" style={{ letterSpacing: rem(0.4) }}>
                Входящие
              </Text>
            </Group>

            <Stack gap="xs" mt="xs">
              <Tabs value={leftMode} onChange={(v) => v && setLeftMode(v as any)} variant="pills">
                <Tabs.List grow>
                  <Tabs.Tab value="all">Все чаты</Tabs.Tab>
                  <Tabs.Tab value="new">Новые ({newCount})</Tabs.Tab>
                </Tabs.List>
              </Tabs>

              <TextInput
                size="xs"
                placeholder="Поиск по контакту"
                leftSection={<IconSearch size={14} />}
                value={search}
                onChange={(e) => setSearch(e.currentTarget.value)}
              />

              <MultiSelect
                size="xs"
                placeholder="Каналы: все"
                value={channelTypeFilters}
                onChange={setChannelTypeFilters}
                data={availableChannelTypes.map((t) => ({ value: t, label: t }))}
                clearable
                searchable
                nothingFoundMessage="Нет каналов"
              />
            </Stack>
          </Box>

          <ScrollArea style={{ flex: 1 }}>
            <Stack gap={4} p="sm">
              {leftChats.length ? (
                leftChats.map((c: any) => (
                  (() => {
                    const closed = isClosedStatus(c.status);
                    const unassignedWaiting = !closed && !c.assignee_admin_id;
                    const myNeedsReply =
                      !closed &&
                      !!adminId &&
                      c.assignee_admin_id === adminId &&
                      isContactActor(c.last_actor_type);

                    const needsAttention = Boolean(c.needs_attention) || unassignedWaiting || myNeedsReply;
                    const tone: "waiting" | "needs_reply" | "none" =
                      unassignedWaiting ? "waiting" : myNeedsReply ? "needs_reply" : "none";

                    const bg =
                      tone === "waiting"
                        ? "var(--mantine-color-yellow-0)"
                        : tone === "needs_reply"
                          ? "var(--mantine-color-indigo-0)"
                          : "white";
                    const border =
                      selectedChatId === c.chat_id
                        ? "var(--mantine-color-indigo-4)"
                        : tone === "waiting"
                          ? "var(--mantine-color-yellow-4)"
                          : tone === "needs_reply"
                            ? "var(--mantine-color-indigo-3)"
                            : "var(--divider)";

                    const dotColor =
                      tone === "waiting"
                        ? "var(--mantine-color-yellow-7)"
                        : tone === "needs_reply"
                          ? "var(--mantine-color-indigo-7)"
                          : "transparent";

                    return (
                  <Paper
                    key={c.chat_id}
                    p="xs"
                    withBorder
                    radius="md"
                    style={{
                      cursor: "pointer",
                      background: bg,
                      borderColor: border,
                    }}
                    onClick={() => setSelectedChatId(c.chat_id)}
                  >
                    <Group justify="space-between" align="flex-start" wrap="nowrap" gap="xs">
                      <Stack gap={2} style={{ minWidth: 0 }}>
                        <Group gap={6} wrap="nowrap" align="center">
                          <ChannelTypeRow
                            types={(c.channel_types ?? (c.channel_type ? [c.channel_type] : [])) as string[]}
                          />
                          <Text size="sm" fw={600} truncate="end" title={c.contact_name ?? "Без имени"} style={{ minWidth: 0 }}>
                            {c.contact_name ?? "Без имени"}
                          </Text>
                        </Group>
                        <Group gap={6} wrap="nowrap" align="center">
                          {c.last_message_at ? (
                            <Text size="xs" c="dimmed">
                              {formatTimeLabel(c.last_message_at)}
                            </Text>
                          ) : null}
                          {c.contact_primary_phone ? (
                            <Text size="xs" c="dimmed" truncate="end" style={{ minWidth: 0 }}>
                              {c.contact_primary_phone}
                            </Text>
                          ) : null}
                        </Group>
                        {leftMode === "all" && c.assignee_name ? (
                          <Text size="xs" c="dimmed" truncate="end">
                            В работе: {c.assignee_name}
                          </Text>
                        ) : null}
                      </Stack>
                      <Stack gap={4} align="flex-end">
                        <Group gap={6} wrap="nowrap" align="center">
                          {needsAttention ? (
                            <Box
                              aria-label="needs-attention"
                              style={{
                                width: 8,
                                height: 8,
                                borderRadius: 999,
                                background: dotColor,
                                flexShrink: 0,
                              }}
                            />
                          ) : null}
                          <Badge size="xs" variant="light" color={closed ? "gray" : "blue"}>
                            {closed ? "закрыто" : "открыто"}
                          </Badge>
                        </Group>
                        {tone === "waiting" ? (
                          <Badge size="xs" variant="light" color="yellow">
                            Ожидает
                          </Badge>
                        ) : null}
                      </Stack>
                    </Group>
                  </Paper>
                    );
                  })()
                ))
              ) : (
                <Text size="sm" c="dimmed">
                  Нет чатов.
                </Text>
              )}
            </Stack>
          </ScrollArea>
        </Box>

        {/* Center conversation */}
        <Flex ref={centerPaneRef} direction="column" style={{ flex: 1, minWidth: 0, minHeight: 0, background: "var(--bg-main)" }}>
          {!selectedChatId ? (
            <Stack h="100%" align="center" justify="center">
              <EmptyStateHint title="Выберите диалог" subtitle="Слева — все/новые, справа — ваши в работе." />
            </Stack>
          ) : (
            <>
              <Box px="sm" py={8} style={{ borderBottom: "1px solid var(--mantine-color-gray-2)", background: "white" }}>
                <Group justify="space-between" wrap="nowrap" gap={8} align="center">
                  <Stack gap={1} style={{ minWidth: 0 }}>
                    <Text fw={700} size="sm" truncate="end" style={{ lineHeight: 1.15 }}>
                      {chatDetail?.contact_name ?? "Диалог"}
                    </Text>
                    <Group gap={6} wrap="nowrap" style={{ minWidth: 0 }}>
                      <ChannelTypeRow
                        types={
                          (chatDetail?.channel_type
                            ? [chatDetail.channel_type]
                            : []) as string[]
                        }
                      />
                      {chatDetail?.assignee_name ? (
                        <Badge size="xs" variant="light" color="indigo">
                          В работе: {chatDetail.assignee_name}
                        </Badge>
                      ) : null}
                      {chatDetail?.status ? (
                        <Badge size="xs" variant="light" color="gray">
                          {String(chatDetail.status).toLowerCase()}
                        </Badge>
                      ) : null}
                    </Group>
                  </Stack>
                  <Group gap={8} wrap="nowrap" align="center">
                    <Tooltip label="Режим ассистента" withArrow>
                      <Box>
                        <Select
                          size="xs"
                          w={160}
                          aria-label="Режим ассистента"
                          label="Ассистент"
                          placeholder="Режим"
                          value={(chatDetail?.ai_mode || "DISABLED").toUpperCase()}
                      data={[
                        { value: "DISABLED", label: "Выкл" },
                        { value: "SUGGEST_ONLY", label: "Подсказка" },
                        { value: "AUTO_REPLY", label: "Автоответчик" },
                      ].filter((o) => (OMNI_CHAT_AI_MODES as readonly string[]).includes(o.value))}
                      onChange={(v) => {
                        if (!selectedChatId || !v || !canToggleAi) return;
                        updateAiMode.mutate({ chatId: selectedChatId, ai_mode: v });
                      }}
                      disabled={!selectedChatId || !canToggleAi}
                      rightSection={updateAiMode.isPending ? <Loader size="xs" /> : undefined}
                        />
                      </Box>
                    </Tooltip>
                    {canResolveSelected ? (
                      <Button
                        size="xs"
                        variant="filled"
                        color="slate"
                        loading={resolveChat.isPending}
                        onClick={() => void finishOmniTicket()}
                      >
                        Завершить заявку
                      </Button>
                    ) : null}
                    {!canClaim && !canResolveSelected && chatDetail?.assignee_name ? (
                      <Button size="xs" variant="light" color="gray" disabled>
                        В работе у {chatDetail.assignee_name}
                      </Button>
                    ) : null}
                    <Tooltip label="Закрыть диалог (не завершать заявку)" withArrow>
                      <ActionIcon
                        variant="subtle"
                        color="gray"
                        aria-label="Закрыть диалог"
                        onClick={closeOmniDialogOnly}
                      >
                        <IconX size={18} />
                      </ActionIcon>
                    </Tooltip>
                  </Group>
                </Group>
              </Box>

              <ScrollArea
                style={{ flex: 1, minHeight: 0 }}
                scrollHideDelay={250}
                viewportRef={messagesViewportRef as any}
              >
                <Stack gap="xs" p="md" {...ADMIN_CHAT_MESSAGES_REGION}>
                  {mergedMessages.length ? (
                    mergedMessages.map((m: any, idx: number) => {
                      const dayKey = toDayKey(m.created_at);
                      const prevDayKey = idx > 0 ? toDayKey(mergedMessages[idx - 1]?.created_at) : null;
                      const showDaySeparator = !!dayKey && dayKey !== prevDayKey;
                      const timeLabel = formatTimeLabel(m.created_at);
                      const outbound = String(m.direction || "").toUpperCase() === "OUTBOUND";
                      const replyMeta = parseReplyLine(String(m.content || ""));
                      const displayContent = replyMeta ? replyMeta.rest : String(m.content || "");
                      const targetMsg = replyMeta?.messageId
                        ? (mergedMessages as any[]).find((x) => String(x.id) === String(replyMeta.messageId))
                        : null;
                      const quotedText =
                        targetMsg && String(targetMsg.content || "").trim()
                          ? String(parseReplyLine(String(targetMsg.content || ""))?.rest ?? String(targetMsg.content || "")).trim()
                          : replyMeta?.messageId
                            ? "Сообщение"
                            : "";
                      return (
                        <Stack key={m.id} gap={6}>
                          {showDaySeparator ? (
                            <Group justify="center">
                              <Badge size="xs" variant="light" color="gray">
                                {formatDayLabel(m.created_at)}
                              </Badge>
                            </Group>
                          ) : null}
                          <Group justify={outbound ? "flex-end" : "flex-start"} align="flex-start" wrap="nowrap">
                            {!outbound ? <Box style={{ width: 28, flexShrink: 0 }} /> : null}
                            <Group gap={8} wrap="nowrap" align="flex-start" style={{ maxWidth: "92%" }}>
                              <Paper
                                p={6}
                                radius="lg"
                                withBorder
                                id={`omni-msg-${String(m.id)}`}
                                data-omni-message-id={String(m.id)}
                                onContextMenu={(e) => {
                                  e.preventDefault();
                                  setCtxMenu({
                                    opened: true,
                                    x: e.clientX,
                                    y: e.clientY,
                                    messageId: String(m.id),
                                    messageText: String(m.content || ""),
                                  });
                                }}
                                style={{
                                  display: "flex",
                                  gap: 8,
                                  alignItems: "stretch",
                                  flex: 1,
                                  minWidth: 0,
                                  borderColor: "var(--mantine-color-gray-2)",
                                  background: "transparent",
                                }}
                              >
                                <Paper
                                  p="sm"
                                  radius="lg"
                                  style={{
                                    flex: 1,
                                    minWidth: 0,
                                    border: "none",
                                    ...(outbound ? adminChatOmniOutboundBubbleStyle : adminChatOmniClientInboundBubbleStyle),
                                  }}
                                >
                                  {replyMeta ? (
                                    <Paper
                                      p="xs"
                                      radius="md"
                                      withBorder
                                      style={{
                                        cursor: replyMeta.messageId ? "pointer" : "default",
                                        marginBottom: 8,
                                        background: "var(--mantine-color-gray-0)",
                                        borderColor: "var(--mantine-color-gray-2)",
                                        borderLeft: `3px solid ${outbound ? "var(--mantine-color-indigo-6)" : "var(--mantine-color-teal-6)"}`,
                                      }}
                                      onClick={() => {
                                        const mid = replyMeta.messageId;
                                        if (!mid) return;
                                        const el = document.getElementById(`omni-msg-${mid}`);
                                        if (!el) return;
                                        try {
                                          (el as HTMLElement).scrollIntoView({ block: "center", behavior: "smooth" });
                                        } catch {
                                          (el as HTMLElement).scrollIntoView();
                                        }
                                      }}
                                    >
                                      <Group gap={6} wrap="nowrap" align="center">
                                        <IconQuote size={16} />
                                        <Text size="xs" c="dimmed" truncate="end" style={{ flex: 1, minWidth: 0 }}>
                                          {quotedText}
                                        </Text>
                                      </Group>
                                    </Paper>
                                  ) : null}
                                  <Box style={{ fontSize: 13, lineHeight: 1.35 }}>
                                    <OmniMessageRichBody
                                      content={displayContent}
                                      attachments={(m.attachments ?? []).map((a: any) => ({
                                        id: String(a.id),
                                        file_name: String(a.file_name || ""),
                                        content_type: String(a.content_type || "application/octet-stream"),
                                        size_bytes: Number(a.size_bytes || 0),
                                        source: a.source === "clinic_chat" ? "clinic_chat" : "omni",
                                        conversation_id: a.conversation_id ?? null,
                                      }))}
                                      getClinicChatBlob={getClinicChatBlob}
                                      getOmniBlob={(attachmentId) => getOmniBlobForMessage(String(m.id), attachmentId)}
                                      allowAudioAttachmentDownload={false}
                                    />
                                  </Box>
                                </Paper>

                                <Paper
                                  p={6}
                                  radius="md"
                                  withBorder
                                  style={{
                                    width: 56,
                                    flexShrink: 0,
                                    background: "var(--mantine-color-gray-0)",
                                    borderColor: "var(--mantine-color-gray-2)",
                                    display: "flex",
                                    flexDirection: "column",
                                    alignItems: "center",
                                    justifyContent: "flex-start",
                                    gap: 6,
                                  }}
                                >
                                  <Text size="xs" c="dimmed" style={{ lineHeight: 1 }}>
                                    {timeLabel}
                                  </Text>
                                  {m.channel_type ? (
                                    <Box style={{ color: channelBrandColor(String(m.channel_type)), display: "flex" }}>
                                      <ChannelIcon type={String(m.channel_type)} />
                                    </Box>
                                  ) : null}
                                  <Tooltip label="Ответить" withArrow>
                                    <ActionIcon
                                      variant="subtle"
                                      color="gray"
                                      size="sm"
                                      aria-label="Ответить"
                                      onClick={() => startReply(String(m.id))}
                                    >
                                      <IconCornerUpLeft size={16} />
                                    </ActionIcon>
                                  </Tooltip>
                                  {/* actions: right-click context menu */}
                                </Paper>
                              </Paper>
                            </Group>
                            {outbound ? <Box style={{ width: 28, flexShrink: 0 }} /> : null}
                          </Group>
                        </Stack>
                      );
                    })
                  ) : (
                    <Text size="sm" c="dimmed">
                      Нет сообщений.
                    </Text>
                  )}
                </Stack>
              </ScrollArea>

              {ctxMenu.opened && ctxMenu.messageId ? (
                <Box
                  style={{
                    position: "fixed",
                    left: ctxMenu.x,
                    top: ctxMenu.y,
                    width: 1,
                    height: 1,
                    zIndex: 9999,
                  }}
                  onClick={() => setCtxMenu((s) => ({ ...s, opened: false }))}
                >
                  <Menu opened withinPortal shadow="md" position="bottom-start">
                    <Menu.Target>
                      <Box style={{ width: 1, height: 1 }} />
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item
                        onClick={() => {
                          startReply(ctxMenu.messageId as string);
                          setCtxMenu((s) => ({ ...s, opened: false }));
                        }}
                      >
                        Ответить
                      </Menu.Item>
                      <Menu.Item
                        onClick={async () => {
                          try {
                            await navigator.clipboard?.writeText(ctxMenu.messageText || "");
                          } catch {
                            /* ignore */
                          }
                          setCtxMenu((s) => ({ ...s, opened: false }));
                        }}
                      >
                        Копировать текст
                      </Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Box>
              ) : null}

              <Box p="md" style={{ borderTop: "1px solid var(--mantine-color-gray-2)", background: "white" }}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={fileAccept}
                  style={{ display: "none" }}
                  onChange={(e) => {
                    const f = e.currentTarget.files?.[0] ?? null;
                    e.currentTarget.value = "";
                    if (!f) return;
                    setPendingFile(f);
                    queueMicrotask(() => composerRef.current?.focus());
                  }}
                />
                <Stack gap={8}>
                  {replyingTo ? (
                    <Paper
                      p="xs"
                      radius="md"
                      withBorder
                      style={{
                        background: "var(--mantine-color-gray-0)",
                        borderColor: "var(--mantine-color-gray-2)",
                        borderLeft: "3px solid var(--mantine-color-indigo-6)",
                      }}
                    >
                      <Group justify="space-between" gap="xs" wrap="nowrap" align="center">
                        <Group gap={6} wrap="nowrap" align="center" style={{ minWidth: 0 }}>
                          <IconQuote size={16} />
                          <Text size="xs" c="dimmed" truncate="end" style={{ minWidth: 0 }}>
                            {replyingTo.preview}
                          </Text>
                        </Group>
                        <ActionIcon
                          size="sm"
                          variant="subtle"
                          color="gray"
                          aria-label="Убрать ответ"
                          onClick={() => setReplyingTo(null)}
                        >
                          ×
                        </ActionIcon>
                      </Group>
                    </Paper>
                  ) : null}
                  {pendingFile ? (
                    <Group justify="space-between" gap="xs">
                      <Text size="xs" c="dimmed" truncate="end" style={{ maxWidth: 520 }}>
                        Файл: {pendingFile.name} ({Math.ceil(pendingFile.size / 1024)} КБ)
                      </Text>
                      <Button size="xs" variant="subtle" color="gray" onClick={() => setPendingFile(null)}>
                        Убрать
                      </Button>
                    </Group>
                  ) : null}
                  {attachError ? (
                    <Text size="xs" c="red">
                      {attachError}
                    </Text>
                  ) : null}
                  {resolveError ? (
                    <Text size="xs" c="red">
                      {resolveError}
                    </Text>
                  ) : null}
                  {selectedChatId && String(chatDetail?.status || "").toUpperCase() !== "CLOSED" ? (
                    <Text size="xs" c="dimmed">
                      «Завершить заявку» — снимок переписки и статус попадают в раздел лидов. Крестик только убирает
                      диалог с экрана. Автозакрытие по тишине возможно после снятия присутствия (lease); при черновике в
                      поле ввода CLOSE не отправляется сразу.
                    </Text>
                  ) : null}
                  <Group align="flex-end" wrap="nowrap" gap="sm">
                    <Box style={{ flex: 1, minWidth: 260 }}>
                      <AppleEmojiOverlayTextarea
                        ref={composerRef}
                        value={messageText}
                        onChange={(e: any) => setMessageText(String(e?.target?.value ?? ""))}
                        autosize
                        minRows={4}
                        maxRows={composerMaxRows}
                        placeholder="Написать ответ… (Ctrl+Enter)"
                        styles={{
                          input: {
                            fontSize: 14,
                          },
                        }}
                      />
                    </Box>
                    <ActionIcon
                      size={44}
                      variant="filled"
                      color="indigo"
                      onClick={handleSend}
                      loading={sendMessage.isPending || sendWithFile.isPending}
                      aria-label="Отправить"
                    >
                      <IconSend size={18} />
                    </ActionIcon>
                  </Group>

                  <Group justify="space-between" align="flex-end" wrap="wrap" gap="sm">
                    <Group gap={6} wrap="nowrap" align="flex-end">
                      <EmojiMartPopoverPicker
                        onPick={(native) => setMessageText((prev) => `${prev}${native}`)}
                        onInserted={() => composerRef.current?.focus()}
                        ariaLabel="Эмодзи"
                      />
                      <ActionIcon size="lg" variant="light" color="gray" onClick={() => pickFile("*")} aria-label="Файл">
                        <IconPaperclip size={20} />
                      </ActionIcon>
                      <ActionIcon
                        size="lg"
                        variant="light"
                        color="gray"
                        onClick={() => pickFile("image/*")}
                        aria-label="Фото"
                      >
                        <IconPhoto size={20} />
                      </ActionIcon>
                      <VoiceNoteRecorderButton
                        onRecorded={(file) => {
                          setPendingFile(file);
                          queueMicrotask(() => composerRef.current?.focus());
                        }}
                        onError={(msg) => setAttachError(msg)}
                      />
                    </Group>

                    <Box style={{ flex: 1, minWidth: 320, maxWidth: 520 }}>
                      <Select
                        label="Быстрые ответы"
                        placeholder="Выберите…"
                        disabled={!quickRepliesData?.items?.length}
                        data={(quickRepliesData?.items ?? []).map((qr: any) => ({
                          value: String(qr.id),
                          label: String(qr.title || qr.body || "Ответ"),
                        }))}
                        searchable
                        clearable
                        nothingFoundMessage="Нет быстрых ответов"
                        onChange={(v) => {
                          const id = v ? String(v) : null;
                          const qr = id ? (quickRepliesData?.items ?? []).find((x: any) => String(x.id) === id) : null;
                          if (qr?.body) applyQuickReply(String(qr.body));
                        }}
                      />
                    </Box>
                  </Group>
                </Stack>
              </Box>
            </>
          )}
        </Flex>

        {/* Right work list */}
        <OmniWorkPane
          selectedChatId={selectedChatId}
          onSelectChat={setSelectedChatId}
          mineOpen={myOpenChats}
          mineClosed={myClosedChats}
        />
      </Flex>

      <Modal
        opened={analyticsOpen}
        onClose={() => setAnalyticsOpen(false)}
        title="Аналитика omni‑чата"
        size="lg"
        centered
      >
        <Stack gap="sm">
          <Group grow>
            <TextInput label="Дата от" type="date" value={dateFrom} onChange={(e) => setDateFrom(e.currentTarget.value)} />
            <TextInput label="Дата до" type="date" value={dateTo} onChange={(e) => setDateTo(e.currentTarget.value)} />
          </Group>
          {analyticsQuery.isLoading ? (
            <Text size="sm" c="dimmed">
              Загрузка…
            </Text>
          ) : analyticsQuery.isError ? (
            <Text size="sm" c="red">
              Не удалось загрузить аналитику.
            </Text>
          ) : analyticsQuery.data ? (
            <>
              <Group grow>
                <Paper withBorder p="sm" radius="md">
                  <Text size="xs" c="dimmed">
                    Создано чатов
                  </Text>
                  <Text fw={700}>{analyticsQuery.data.total_chats_created}</Text>
                </Paper>
                <Paper withBorder p="sm" radius="md">
                  <Text size="xs" c="dimmed">
                    Взято в работу
                  </Text>
                  <Text fw={700}>{analyticsQuery.data.total_claimed}</Text>
                </Paper>
                <Paper withBorder p="sm" radius="md">
                  <Text size="xs" c="dimmed">
                    Закрыто
                  </Text>
                  <Text fw={700}>{analyticsQuery.data.total_closed}</Text>
                </Paper>
              </Group>

              <Group grow>
                <Paper withBorder p="sm" radius="md">
                  <Text size="xs" c="dimmed">
                    Среднее время до взятия
                  </Text>
                  <Text fw={700}>
                    {analyticsQuery.data.avg_time_to_claim_seconds != null
                      ? `${Math.round(analyticsQuery.data.avg_time_to_claim_seconds / 60)} мин`
                      : "—"}
                  </Text>
                </Paper>
                <Paper withBorder p="sm" radius="md">
                  <Text size="xs" c="dimmed">
                    Среднее время до закрытия
                  </Text>
                  <Text fw={700}>
                    {analyticsQuery.data.avg_time_to_close_seconds != null
                      ? `${Math.round(analyticsQuery.data.avg_time_to_close_seconds / 60)} мин`
                      : "—"}
                  </Text>
                </Paper>
              </Group>

              <Divider />

              <Stack gap="xs">
                <Text fw={600}>Исходы</Text>
                {(analyticsQuery.data.outcomes ?? []).length ? (
                  (analyticsQuery.data.outcomes ?? []).map((o) => (
                    <Group key={o.outcome} justify="space-between">
                      <Text size="sm">{o.outcome}</Text>
                      <Badge variant="light" color="gray">
                        {o.count}
                      </Badge>
                    </Group>
                  ))
                ) : (
                  <Text size="sm" c="dimmed">
                    Нет закрытий за период.
                  </Text>
                )}
              </Stack>

              <Divider />

              <Stack gap="xs">
                <Text fw={600}>По администраторам</Text>
                {(analyticsQuery.data.by_admin ?? []).length ? (
                  (analyticsQuery.data.by_admin ?? []).map((a) => (
                    <Paper key={a.admin_id} withBorder p="xs" radius="md">
                      <Group justify="space-between" wrap="nowrap">
                        <Text size="sm" truncate="end">
                          {a.admin_name ?? a.admin_id}
                        </Text>
                        <Group gap="xs">
                          <Badge size="sm" variant="light" color="blue">
                            взял: {a.claimed_count}
                          </Badge>
                          <Badge size="sm" variant="light" color="gray">
                            закрыл: {a.closed_count}
                          </Badge>
                        </Group>
                      </Group>
                    </Paper>
                  ))
                ) : (
                  <Text size="sm" c="dimmed">
                    Нет данных.
                  </Text>
                )}
              </Stack>
            </>
          ) : null}
        </Stack>
      </Modal>
    </Stack>
  );
}

