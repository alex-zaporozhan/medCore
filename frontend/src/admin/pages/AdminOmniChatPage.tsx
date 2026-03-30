import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { useAdminTasksOpen, useCreateAdminTaskMutation, useCreateAdminBooking } from "@/hooks";
import { useQueryClient } from "@tanstack/react-query";
import {
  useAdminOmniChats,
  useAdminOmniChatDetail,
  useAdminOmniChatMessagesInfinite,
  useOmniChatSse,
  useOmniQuickReplies,
  usePatchOmniChat,
  useSendAdminOmniMessage,
  useSendAdminOmniMessageWithFile,
  useUpdateOmniChatAiMode,
  useHideAdminOmniMessage,
  OMNI_CHAT_AI_MODES,
} from "@/hooks/useAdminOmniChat";
import { useAdminLoyaltySummaryByContact, useAdminFormSubmissions, useAdminFormTemplates, useSendFormLink } from "@/hooks";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import {
  AdminDrawer,
  DataSkeleton,
  AiFeatureBadge,
  QueryErrorAlert,
  OmniInspectorTabShell,
  OmniInspectorSection,
} from "@/shared/ui";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAiCreateTaskForLead,
  useAiIgnoreLeadRecommendation,
  useAiLeadSummary,
  useAiSuggestNextStage,
  useAiUpdateLeadStage,
} from "@/hooks/useCrmLeads";
import { useDoctors } from "@/hooks/useDoctors";
import { useServices } from "@/hooks/useServices";
import {
  Box,
  Flex,
  Stack,
  Paper,
  Text,
  TextInput,
  Button,
  Badge,
  Select,
  Checkbox,
  Tabs,
  Group,
  Menu,
  Divider,
  Tooltip,
  SegmentedControl,
  ActionIcon,
  rem,
  ScrollArea,
} from "@mantine/core";
import {
  IconBriefcase,
  IconBrandTelegram,
  IconBrandWhatsapp,
  IconCalendarEvent,
  IconCalendarPlus,
  IconCopy,
  IconDeviceMobile,
  IconChevronLeft,
  IconChevronRight,
  IconEyeOff,
  IconFileDescription,
  IconHistory,
  IconListCheck,
  IconMessageReply,
  IconRefresh,
  IconSend,
  IconRobot,
  IconUser,
  IconDotsVertical,
  IconPaperclip,
  IconPhoto,
} from "@tabler/icons-react";
import { useHotkeys } from "@mantine/hooks";
import { GlassModal } from "@/shared/ui/GlassModal";
import { Textarea } from "@mantine/core";
import { AppleEmojiOverlayTextarea } from "@/shared/ui";
import { api, getAdminId } from "@/api/client";
import { useAiFeatures, getAiFeatureTooltip } from "@/shared/aiFeatures";
import { useEffectiveAiFeatureGate } from "@/hooks/useEffectiveAiFeatureGate";
import { logUiEvent } from "@/shared/uiEvents";
import { useAvailableAiTools } from "@/hooks/useAvailableAiTools";
import {
  ADMIN_CHAT_MESSAGES_REGION,
  adminChatOmniClientInboundBubbleStyle,
  adminChatOmniHiddenBubbleStyle,
  adminChatOmniOutboundBubbleStyle,
} from "@/shared/adminChatChrome";
import { SEMANTIC } from "@/shared/semanticUi";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { OmniMessageRichBody } from "@/shared/OmniMessageRichBody";
import { useAdminSession } from "@/hooks/useAdminSession";
import { EmojiMartPopoverPicker } from "@/shared/ui/EmojiMartPopoverPicker";
import { VoiceNoteRecorderButton } from "@/shared/ui/VoiceNoteRecorderButton";

function omniChatListStatusColor(status: string): string {
  const s = String(status).toUpperCase();
  if (s === "OPEN") return "var(--mantine-color-green-6)";
  if (s === "CLOSED") return "var(--mantine-color-gray-5)";
  return "var(--mantine-color-blue-6)";
}

function omniChatListAiShort(ai_mode: string | null | undefined): string | null {
  if (!ai_mode || ai_mode === "DISABLED") return null;
  if (ai_mode === "AUTO_REPLY") return "AI авто";
  return "AI подск.";
}

function omniMessageDeliveryLabel(
  deliveryStatus: string | null | undefined,
  readStatus: string | null | undefined
): { label: string; color: string; tooltip: string } | null {
  const read = String(readStatus || "").toUpperCase();
  const delivery = String(deliveryStatus || "").toUpperCase();
  if (read === "READ") {
    return { label: "Прочитано", color: "var(--mantine-color-teal-7)", tooltip: "Клиент открыл сообщение." };
  }
  if (delivery === "DELIVERED") {
    return { label: "Доставлено", color: "var(--mantine-color-green-7)", tooltip: "Канал подтвердил доставку." };
  }
  if (delivery) {
    return { label: delivery, color: "var(--mantine-color-gray-6)", tooltip: "Технический статус доставки." };
  }
  return null;
}

function omniOutboundChannelLabel(t: string | null | undefined): string {
  const u = String(t || "").toUpperCase();
  if (u === "TELEGRAM_BOT") return "Telegram";
  if (u === "WHATSAPP") return "WhatsApp";
  if (u === "WEB_WIDGET") return "Виджет сайта";
  if (u === "WEB_APP") return "Приложение";
  return t ? String(t) : "Канал";
}

function OmniChannelMetaIcon({ channelType, size = 12 }: { channelType: string | null | undefined; size?: number }) {
  const u = String(channelType || "").toUpperCase();
  if (u === "TELEGRAM_BOT") return <IconBrandTelegram size={size} stroke={1.6} />;
  if (u === "WHATSAPP") return <IconBrandWhatsapp size={size} stroke={1.6} />;
  return <IconDeviceMobile size={size} stroke={1.6} />;
}

/** Подсказка к сырому статусу диалога из API (список слева). */
function omniChatStatusTooltip(status: string): string {
  const s = String(status).toUpperCase();
  if (s === "OPEN") {
    return "Диалог открыт: переписка активна, можно отправлять и получать сообщения.";
  }
  if (s === "CLOSED") {
    return "Диалог закрыт: переписка завершена, новые сообщения обычно не ожидаются.";
  }
  if (s === "WAITING_FOR_OPERATOR") {
    return "Ожидает оператора: нужен ответ сотрудника.";
  }
  if (s === "IN_PROGRESS") {
    return "В работе у оператора.";
  }
  return `Статус диалога в системе: ${status}`;
}

type OmniInspectorTab = "client" | "forms" | "timeline" | "ai";

const OMNI_INSPECTOR_COLLAPSED_KEY = "admin_omni_inspector_collapsed";
const MAX_OMNI_UPLOAD_BYTES = 5 * 1024 * 1024;

export default function AdminOmniChatPage() {
  const { data: adminSession } = useAdminSession();
  const allowAudioAttachmentDownload = adminSession?.roles?.includes("owner") ?? false;

  const { currentClinicId } = useAdminClinic();
  const aiFeatures = useAiFeatures(currentClinicId ?? null);
  const crmStageFeature = aiFeatures.get("omni.tools.crm_suggest_next_stage");
  const createTaskFeature = aiFeatures.get("omni.tools.create_task");
  const spotlightGate = useEffectiveAiFeatureGate(currentClinicId ?? null, "omni.spotlight.agent", [], {
    gateByTools: false,
  });
  const availableTools = useAvailableAiTools(currentClinicId ?? null);
  const canCrmAi = availableTools.hasAll(["summarize_lead_context", "suggest_next_stage_for_lead"]);
  const canApplyStage = availableTools.hasAll(["update_lead_stage"]);
  const canCreateAiTask = availableTools.hasAll(["create_task_for_lead"]);
  const createTaskMutation = useCreateAdminTaskMutation();
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [messageText, setMessageText] = useState("");
  const [pendingOmniFile, setPendingOmniFile] = useState<File | null>(null);
  const [omniAttachError, setOmniAttachError] = useState<string | null>(null);
  const omniFileInputRef = useRef<HTMLInputElement>(null);
  const [omniFileAccept, setOmniFileAccept] = useState("*");
  const messageComposerRef = useRef<HTMLTextAreaElement>(null);
  /** Явный выбор канала при нескольких каналах в треде (сбрасывается при смене чата). */
  const [replyChannelPick, setReplyChannelPick] = useState<string | null>(null);
  const [showOnlyWaiting, setShowOnlyWaiting] = useState(false);
  const [showHiddenMessages, setShowHiddenMessages] = useState(false);
  const [replyToMessage, setReplyToMessage] = useState<{
    id: string;
    content: string;
    actorType: string;
  } | null>(null);
  const [messageContextMenu, setMessageContextMenu] = useState<{
    id: string;
    content: string;
    actorType: string;
    x: number;
    y: number;
  } | null>(null);
  const [aiFilter, setAiFilter] = useState<string>("ALL");
  const [hideModalOpen, setHideModalOpen] = useState(false);
  const [hideMessageId, setHideMessageId] = useState<string | null>(null);
  const [hideReason, setHideReason] = useState("");
  const [formDrawerOpen, setFormDrawerOpen] = useState(false);
  const [formTemplateId, setFormTemplateId] = useState<string | null>(null);
  const [formSendVia, setFormSendVia] = useState<"whatsapp" | "sms" | "copy_only">("copy_only");
  const [taskDrawerOpen, setTaskDrawerOpen] = useState(false);
  const [taskTitle, setTaskTitle] = useState("");
  const [taskDescription, setTaskDescription] = useState("");
  const [taskPriority, setTaskPriority] = useState<string | null>("medium");
  const [taskDueAt, setTaskDueAt] = useState("");
  const [taskAssignMe, setTaskAssignMe] = useState(true);
  const [bookingModalOpen, setBookingModalOpen] = useState(false);
  const [bookingDoctorId, setBookingDoctorId] = useState<string | null>(null);
  const [bookingServiceId, setBookingServiceId] = useState<string | null>(null);
  const [bookingDate, setBookingDate] = useState("");
  const [bookingTime, setBookingTime] = useState("");
  const [bookingNotes, setBookingNotes] = useState("");
  const [inspectorCollapsed, setInspectorCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(OMNI_INSPECTOR_COLLAPSED_KEY) === "true";
  });
  const [inspectorTab, setInspectorTab] = useState<OmniInspectorTab>("client");
  /** P1-B: фильтр «мои диалоги» (assignee=me). */
  const [assigneeMineOnly, setAssigneeMineOnly] = useState(false);

  const queryClient = useQueryClient();
  const { data: chatsData, isLoading: chatsLoading, isError: chatsError, error: chatsErr } = useAdminOmniChats({
    status: showOnlyWaiting ? "WAITING_FOR_OPERATOR" : statusFilter,
    search: search || undefined,
    page: 1,
    page_size: 100,
    assignee: assigneeMineOnly ? "me" : undefined,
  });

  const { sseBroken } = useOmniChatSse(true, selectedChatId);
  const { data: quickRepliesData } = useOmniQuickReplies(true);
  const patchOmniChat = usePatchOmniChat();

  const handleRefreshOmniThread = useCallback(() => {
    if (!selectedChatId) return;
    void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-messages", selectedChatId] });
    void queryClient.invalidateQueries({ queryKey: ["admin-omni-chat-detail", selectedChatId] });
    void queryClient.invalidateQueries({ queryKey: ["admin-omni-chats"] });
  }, [queryClient, selectedChatId]);

  const handleAssignOmniToMe = useCallback(() => {
    const adminId = getAdminId();
    if (!selectedChatId || !adminId) return;
    patchOmniChat.mutate({ chatId: selectedChatId, assignee_admin_id: adminId });
  }, [selectedChatId, patchOmniChat]);

  const visibleChats = useMemo(() => {
    let items = chatsData?.items ?? [];
    if (aiFilter === "AI_ONLY") {
      items = items.filter(
        (c) => c.ai_mode && c.ai_mode !== "DISABLED"
      );
    }
    return items;
  }, [aiFilter, chatsData?.items]);

  const { data: chatDetail, isLoading: detailLoading } = useAdminOmniChatDetail(selectedChatId);
  const {
    mergedMessages,
    isPending: messagesInitialLoading,
    isFetchingNextPage,
    hasNextPage,
    fetchNextPage,
  } = useAdminOmniChatMessagesInfinite(selectedChatId, {
    limit: 100,
    include_hidden: showHiddenMessages,
  });

  const omniMessagesViewportRef = useRef<HTMLDivElement>(null);

  const handleLoadOlderMessages = useCallback(async () => {
    const el = omniMessagesViewportRef.current;
    const prevH = el?.scrollHeight ?? 0;
    const prevTop = el?.scrollTop ?? 0;
    await fetchNextPage();
    requestAnimationFrame(() => {
      const node = omniMessagesViewportRef.current;
      if (!node) return;
      node.scrollTop = prevTop + (node.scrollHeight - prevH);
    });
  }, [fetchNextPage]);

  const replyChannelOptions = useMemo(() => {
    const items = mergedMessages;
    const seen = new Set<string>();
    const out: { value: string; label: string }[] = [];
    for (const m of items) {
      if (m.direction !== "INBOUND" || m.actor_type !== "CLIENT" || !m.channel_id) continue;
      if (seen.has(m.channel_id)) continue;
      seen.add(m.channel_id);
      out.push({ value: m.channel_id, label: omniOutboundChannelLabel(m.channel_type) });
    }
    if (out.length === 0 && chatDetail?.channel_id) {
      out.push({
        value: chatDetail.channel_id,
        label: omniOutboundChannelLabel(chatDetail.channel_type),
      });
    }
    return out;
  }, [mergedMessages, chatDetail?.channel_id, chatDetail?.channel_type]);

  const defaultReplyChannelId = useMemo(() => {
    const items = mergedMessages;
    for (let i = items.length - 1; i >= 0; i--) {
      const m = items[i];
      if (m.direction === "INBOUND" && m.actor_type === "CLIENT" && m.channel_id) {
        return m.channel_id;
      }
    }
    return chatDetail?.channel_id ?? null;
  }, [mergedMessages, chatDetail?.channel_id]);

  const effectiveReplyChannelId = replyChannelPick ?? defaultReplyChannelId;
  const effectiveReplyLabel =
    replyChannelOptions.find((o) => o.value === effectiveReplyChannelId)?.label ??
    omniOutboundChannelLabel(
      mergedMessages.find((m) => m.channel_id === effectiveReplyChannelId)?.channel_type
    );

  const sendMessage = useSendAdminOmniMessage();
  const sendOmniWithFile = useSendAdminOmniMessageWithFile();
  const updateAiMode = useUpdateOmniChatAiMode();
  const hideMessage = useHideAdminOmniMessage();

  useEffect(() => {
    setReplyChannelPick(null);
    setReplyToMessage(null);
    setMessageContextMenu(null);
    setPendingOmniFile(null);
    setOmniAttachError(null);
  }, [selectedChatId]);

  const getClinicChatBlob = useCallback(
    (conversationId: string, attachmentId: string) =>
      api.getBlob(`/v1/admin/chat/conversations/${conversationId}/attachments/${attachmentId}/file`),
    []
  );

  const getOmniBlobForMessage = useCallback(
    (messageId: string, attachmentId: string) => {
      if (!selectedChatId) return Promise.reject(new Error("no chat"));
      return api.getBlob(
        `/v1/admin/omni-chats/${selectedChatId}/messages/${messageId}/attachments/${attachmentId}/file`
      );
    },
    [selectedChatId]
  );

  const handleSend = () => {
    if (!selectedChatId) return;
    if (!messageText.trim() && !pendingOmniFile) return;
    const reply_channel_id =
      replyChannelOptions.length > 1 && effectiveReplyChannelId ? effectiveReplyChannelId : undefined;

    if (pendingOmniFile) {
      if (pendingOmniFile.size > MAX_OMNI_UPLOAD_BYTES) {
        setOmniAttachError("Файл больше 5 МБ");
        return;
      }
      setOmniAttachError(null);
      sendOmniWithFile.mutate(
        {
          chatId: selectedChatId,
          body: messageText.trim(),
          file: pendingOmniFile,
          reply_channel_id,
        },
        {
          onSuccess: () => {
            setMessageText("");
            setPendingOmniFile(null);
            setReplyToMessage(null);
          },
        }
      );
      return;
    }

    const payload: {
      chatId: string;
      content: string;
      reply_channel_id?: string | null;
    } = {
      chatId: selectedChatId,
      content: messageText.trim(),
    };
    if (reply_channel_id) {
      payload.reply_channel_id = reply_channel_id;
    }
    sendMessage.mutate(payload, {
      onSuccess: () => {
        setMessageText("");
        setReplyToMessage(null);
      },
    });
  };

  const selectedItem = chatsData?.items?.find((c) => c.chat_id === selectedChatId) ?? null;
  const contactId = selectedItem?.contact_id ?? chatDetail?.contact_id ?? null;
  const { data: loyaltySummary } = useAdminLoyaltySummaryByContact(contactId);
  const patientId = loyaltySummary?.patient_id ?? null;
  const { data: formSubmissions } = useAdminFormSubmissions({
    patient_id: patientId ?? undefined,
  });

  const { data: openTasks } = useAdminTasksOpen();
  const openTasksCount = openTasks?.length ?? 0;

  const leadId = chatDetail?.lead_id ?? null;
  const aiSummary = useAiLeadSummary(leadId);
  const aiSuggestStage = useAiSuggestNextStage(leadId);
  const aiApplyStage = useAiUpdateLeadStage(leadId);
  const aiCreateTask = useAiCreateTaskForLead(leadId);
  const aiIgnore = useAiIgnoreLeadRecommendation(leadId);

  const { data: formTemplates } = useAdminFormTemplates();
  const sendFormLink = useSendFormLink();
  const createBooking = useCreateAdminBooking();
  const { data: doctors } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
    is_active: true,
    enabled: Boolean(currentClinicId),
  });
  const { data: services } = useServices({
    clinic_id: currentClinicId ?? undefined,
  });

  const handleSendFormLink = useCallback(() => {
    if (!patientId || !formTemplateId) return;
    sendFormLink.mutate(
      { patient_id: patientId, template_id: formTemplateId, send_via: formSendVia },
      {
        onSuccess: (res) => {
          if (res.sent) setFormDrawerOpen(false);
          if (res.sent && formSendVia === "copy_only" && res.url) {
            try {
              navigator.clipboard.writeText(res.url);
            } catch {
              // ignore
            }
          }
        },
      }
    );
  }, [patientId, formTemplateId, formSendVia, sendFormLink]);

  const searchInputRef = useRef<HTMLInputElement>(null);
  useHotkeys([
    ["mod+J", () => { searchInputRef.current?.focus(); }],
    ["mod+Enter", () => { if (selectedChatId && (messageText.trim() || pendingOmniFile)) handleSend(); }],
    ["Escape", () => { setFormDrawerOpen(false); setTaskDrawerOpen(false); }],
    ["mod+b", () => { if (selectedChatId && patientId && currentClinicId) handleOpenBookingModal(); }],
    /** Правая панель «Рабочий центр»: свернуть/развернуть (как левое меню). Не срабатывает в полях ввода. */
    ["mod+shift+l", () => { setInspectorCollapsed((c) => !c); }],
  ]);

  useEffect(() => {
    // Prefill task template when context changes.
    if (!taskDrawerOpen) return;
    const base = leadId ? "Follow‑up по лиду из чата" : patientId ? "Follow‑up по пациенту из чата" : "Follow‑up по чату";
    setTaskTitle((prev) => prev || base);
  }, [taskDrawerOpen, leadId, patientId]);

  useEffect(() => {
    localStorage.setItem(OMNI_INSPECTOR_COLLAPSED_KEY, String(inspectorCollapsed));
  }, [inspectorCollapsed]);

  const handleOpenTaskDrawer = () => {
    setTaskDrawerOpen(true);
    void logUiEvent({
      event_name: "task_create_open",
      clinic_id: currentClinicId,
      feature_id: createTaskFeature.id,
      feature_status: createTaskFeature.status,
      meta: { lead_id: leadId, patient_id: patientId, contact_id: contactId },
    });
  };

  const handleOpenBookingModal = useCallback(() => {
    setBookingModalOpen(true);
    setBookingDoctorId(null);
    setBookingServiceId(null);
    setBookingDate("");
    setBookingTime("");
    setBookingNotes("");
  }, []);

  const handleCreateBooking = useCallback(() => {
    if (!currentClinicId || !patientId || !bookingDoctorId || !bookingServiceId || !bookingDate || !bookingTime) {
      return;
    }
    createBooking.mutate(
      {
        clinic_id: currentClinicId,
        patient_id: patientId,
        doctor_id: bookingDoctorId,
        service_id: bookingServiceId,
        appointment_date: bookingDate,
        appointment_time: bookingTime.length === 5 ? `${bookingTime}:00` : bookingTime,
        notes: bookingNotes.trim() ? bookingNotes.trim() : undefined,
      },
      {
        onSuccess: () => {
          setBookingModalOpen(false);
          setBookingDoctorId(null);
          setBookingServiceId(null);
          setBookingDate("");
          setBookingTime("");
          setBookingNotes("");
        },
      }
    );
  }, [
    bookingDate,
    bookingDoctorId,
    bookingNotes,
    bookingServiceId,
    bookingTime,
    createBooking,
    currentClinicId,
    patientId,
  ]);

  const handleCreateTask = () => {
    if (createTaskFeature.status === "stub") return;
    if (!canCreateAiTask) return;
    if (!taskTitle.trim()) return;
    const adminId = getAdminId();
    const dueIso = taskDueAt ? new Date(taskDueAt).toISOString() : null;
    void logUiEvent({
      event_name: "task_create_submit",
      clinic_id: currentClinicId,
      feature_id: createTaskFeature.id,
      feature_status: createTaskFeature.status,
      meta: { lead_id: leadId, patient_id: patientId, contact_id: contactId },
    });
    createTaskMutation.mutate(
      {
        title: taskTitle.trim(),
        description: taskDescription.trim() ? taskDescription.trim() : null,
        priority: taskPriority ?? "medium",
        due_at: dueIso,
        assignee_id: taskAssignMe ? adminId : null,
        patient_id: patientId ?? undefined,
        lead_id: leadId ?? undefined,
      },
      {
        onSuccess: () => {
          setTaskDrawerOpen(false);
          setTaskTitle("");
          setTaskDescription("");
          setTaskPriority("medium");
          setTaskDueAt("");
          setTaskAssignMe(true);
        },
      }
    );
  };

  useEffect(() => {
    if (!selectedChatId && visibleChats.length > 0) {
      setSelectedChatId(visibleChats[0].chat_id);
      return;
    }
    if (selectedChatId && !visibleChats.some((c) => c.chat_id === selectedChatId)) {
      setSelectedChatId(visibleChats[0]?.chat_id ?? null);
    }
  }, [selectedChatId, visibleChats]);

  const handleOpenHideModal = (messageId: string) => {
    setHideMessageId(messageId);
    setHideReason("");
    setHideModalOpen(true);
  };

  const handleConfirmHide = () => {
    if (!selectedChatId || !hideMessageId || !hideReason.trim()) return;
    hideMessage.mutate(
      {
        chatId: selectedChatId,
        messageId: hideMessageId,
        reason: hideReason.trim(),
      },
      {
        onSuccess: () => {
          setHideModalOpen(false);
          setHideMessageId(null);
          setHideReason("");
        },
      }
    );
  };

  const handleReplyToMessage = useCallback((message: { id: string; content: string; actorType: string }) => {
    setReplyToMessage(message);
  }, []);

  const handleCopyMessage = useCallback((content: string) => {
    if (typeof navigator === "undefined" || !navigator.clipboard) return;
    void navigator.clipboard.writeText(content);
  }, []);

  useEffect(() => {
    if (!messageContextMenu) return;
    const closeMenu = () => setMessageContextMenu(null);
    window.addEventListener("click", closeMenu);
    window.addEventListener("scroll", closeMenu, true);
    return () => {
      window.removeEventListener("click", closeMenu);
      window.removeEventListener("scroll", closeMenu, true);
    };
  }, [messageContextMenu]);

  return (
    <Stack gap={0} style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", height: "100%" }}>
      <Box px="md" pt="sm" style={{ flexShrink: 0 }}>
        <ContextBar
          title="Chat & AI — единый чат с пациентами"
          breadcrumbs={
            sseBroken ? (
              <Tooltip label="Realtime недоступен: работает fallback polling (12с) и авто-переподключение SSE.">
                <Badge size="xs" color="red" variant="dot">
                  offline
                </Badge>
              </Tooltip>
            ) : null
          }
        />
      </Box>
      <Box
        px="md"
        pb="sm"
        style={{
          flex: 1,
          minHeight: 0,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        <Stack gap="md" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
          <Flex gap="sm" wrap="wrap" align="center">
            <TextInput
              ref={searchInputRef}
              placeholder="Поиск по контакту (⌘J)"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              style={{ flex: 1, minWidth: 200 }}
            />
            <Group gap="xs" wrap="wrap">
              <SegmentedControl
                size="xs"
                value={showOnlyWaiting ? "waiting" : "all"}
                onChange={(v) => {
                  if (v === "waiting") {
                    setShowOnlyWaiting(true);
                    setStatusFilter(undefined);
                  } else {
                    setShowOnlyWaiting(false);
                    setStatusFilter(undefined);
                  }
                }}
                data={[
                  { label: "Все", value: "all" },
                  { label: "Неотвеченные", value: "waiting" },
                ]}
                styles={(theme) => ({
                  root: {
                    backgroundColor: theme.colors.dark[0],
                    padding: "var(--space-2)",
                    borderRadius: theme.radius.sm,
                  },
                  label: { fontWeight: 600, fontSize: theme.fontSizes.xs },
                })}
              />
              <Button variant="subtle" size="xs" disabled title="Фильтр по VIP (при наличии API)">
                От VIP
              </Button>
              <Button variant="subtle" size="xs" disabled title="С ошибкой оплаты (при наличии API)">
                С ошибкой оплаты
              </Button>
            </Group>
            <Select
              placeholder="Статус диалога"
              value={statusFilter}
              onChange={(value) => {
                setStatusFilter(value || undefined);
                setShowOnlyWaiting(false);
              }}
              data={[
                { value: "", label: "Все" },
                { value: "OPEN", label: "Открыт" },
                { value: "WAITING_FOR_OPERATOR", label: "Ждёт оператора" },
                { value: "IN_PROGRESS", label: "В работе" },
                { value: "CLOSED", label: "Закрыт" },
              ]}
              allowDeselect
              style={{ width: 220 }}
            />
            <Select
              placeholder="Фильтр по AI‑режиму"
              value={aiFilter}
              onChange={(value) => setAiFilter(value || "ALL")}
              data={[
                { value: "ALL", label: "Все режимы" },
                { value: "AI_ONLY", label: "Только AI (автоответ/подсказки)" },
              ]}
              style={{ width: 220 }}
            />
            <Tooltip label="Показать только диалоги, назначенные на вас">
              <Checkbox
                size="xs"
                label="Только мои"
                checked={assigneeMineOnly}
                onChange={(e) => setAssigneeMineOnly(e.currentTarget.checked)}
                styles={{ label: { whiteSpace: "nowrap" } }}
              />
            </Tooltip>
          </Flex>

          {chatsLoading ? (
            <DataSkeleton lines={6} />
          ) : chatsError ? (
            <QueryErrorAlert error={chatsErr} title="Не удалось загрузить диалоги" />
          ) : (
            <Box style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
            <Flex
              direction="row"
              gap={0}
              w="100%"
              style={{
                flex: 1,
                minHeight: 0,
                overflow: "hidden",
              }}
            >
              <Box
                w={320}
                style={{
                  borderRight: "1px solid var(--mantine-color-gray-2)",
                  backgroundColor: "white",
                  minHeight: 0,
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <ScrollArea type="scroll" scrollbarSize={6} style={{ flex: 1, minHeight: 0 }}>
                <Stack gap={4} p="xs" miw={0}>
                  {!chatsData?.items?.length ? (
                    <EmptyStateHint
                      title="Нет диалогов"
                      subtitle="Сообщения появятся из Telegram, веб‑чата и других каналов."
                    />
                  ) : (
                    visibleChats.map((c) => {
                      const aiShort = omniChatListAiShort(c.ai_mode);
                      return (
                      <Box
                        key={c.chat_id}
                        p={6}
                        style={{
                          cursor: "pointer",
                          borderRadius: "var(--radius-sm)",
                          minWidth: 0,
                          width: "100%",
                          backgroundColor:
                            selectedChatId === c.chat_id ? "var(--dark-alpha-06)" : "transparent",
                          border:
                            selectedChatId === c.chat_id
                              ? "1px solid var(--divider)"
                              : "1px solid transparent",
                          boxShadow:
                            selectedChatId === c.chat_id
                              ? "inset 3px 0 0 var(--mantine-color-gray-5)"
                              : undefined,
                        }}
                        onClick={() => setSelectedChatId(c.chat_id)}
                      >
                        <Text
                          fw={600}
                          size="sm"
                          truncate="end"
                          title={
                            (c.contact_name || c.contact_primary_phone || "Без имени") as string
                          }
                          style={{ minWidth: 0 }}
                        >
                          {c.contact_name || c.contact_primary_phone || "Без имени"}
                        </Text>
                        <Text size="xs" c="dimmed" truncate="end" lineClamp={1} style={{ minWidth: 0 }}>
                          {c.contact_primary_phone || "—"}
                        </Text>
                        {c.assignee_name ? (
                          <Badge size="xs" variant="light" color="blue" radius="xs" mt={2} style={{ alignSelf: "flex-start" }}>
                            {c.assignee_name}
                          </Badge>
                        ) : null}
                        <Text
                          component="div"
                          fz={9}
                          lh={1.35}
                          mt={4}
                          lineClamp={1}
                          style={{
                            minWidth: 0,
                            letterSpacing: rem(0.2),
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          <Text
                            component="span"
                            fz={9}
                            fw={500}
                            tt="uppercase"
                            style={{ color: omniChatListStatusColor(c.status) }}
                            title={omniChatStatusTooltip(c.status)}
                          >
                            {c.status}
                          </Text>
                          {c.last_actor_type ? (
                            <>
                              <Text component="span" c="dimmed" mx={3} fz={9}>
                                ·
                              </Text>
                              <Text component="span" c="dimmed" fw={400} fz={9}>
                                {c.last_actor_type}
                              </Text>
                            </>
                          ) : null}
                          {aiShort ? (
                            <>
                              <Text component="span" c="dimmed" mx={3} fz={9}>
                                ·
                              </Text>
                              <Text
                                component="span"
                                fw={500}
                                tt="uppercase"
                                fz={9}
                                style={{ color: "var(--mantine-color-ai-6)" }}
                              >
                                {aiShort}
                              </Text>
                            </>
                          ) : null}
                        </Text>
                      </Box>
                    );
                    })
                  )}
                </Stack>
                </ScrollArea>
              </Box>
              <Flex
                direction="column"
                flex={1}
                bg="gray.0"
                style={{
                  minWidth: 0,
                  position: "relative",
                  minHeight: 0,
                  overflow: "hidden",
                }}
              >
                {!selectedChatId ? (
                  <Stack h="100%" align="center" justify="center">
                    <EmptyStateHint
                      title="Выберите диалог"
                      subtitle="Клик по строке слева, чтобы открыть переписку."
                    />
                  </Stack>
                ) : (
                  <Box
                    p={0}
                    style={{
                      height: "100%",
                      minHeight: 0,
                      display: "flex",
                      flexDirection: "column",
                      overflow: "hidden",
                    }}
                  >
                    <Box
                      px="md"
                      pt="sm"
                      pb="sm"
                      style={{
                        flexShrink: 0,
                        borderBottom: "1px solid var(--mantine-color-gray-2)",
                        backgroundColor: "var(--mantine-color-gray-0)",
                      }}
                    >
                      {detailLoading ? (
                        <DataSkeleton lines={2} />
                      ) : (
                        <Group justify="space-between" py="sm" px="md" wrap="nowrap" gap="md">
                          <Stack gap={2} miw={180}>
                            <Text fw={700} size="md" lh={1.25}>
                              {chatDetail?.contact_name ||
                                chatDetail?.contact_primary_phone ||
                                selectedItem?.contact_name ||
                                selectedItem?.contact_primary_phone ||
                                "Контакт"}
                            </Text>
                            {chatDetail && (
                              <Group gap={6} wrap="nowrap">
                                <Badge
                                  size="xs"
                                  variant="dot"
                                  color={
                                    String(chatDetail.status).toUpperCase() === "OPEN"
                                      ? SEMANTIC.status.success
                                      : String(chatDetail.status).toUpperCase() === "CLOSED"
                                        ? "gray"
                                        : SEMANTIC.opsSeverity.warning
                                  }
                                  radius="xs"
                                >
                                  {chatDetail.status}
                                </Badge>
                                {chatDetail.channel_type ? (
                                  <Text size="xs" c="dimmed" fw={600} tt="uppercase" style={{ letterSpacing: rem(0.5) }}>
                                    {String(chatDetail.channel_type).replace(/_/g, " ")}
                                  </Text>
                                ) : null}
                                {chatDetail.assignee_name ? (
                                  <Badge size="xs" variant="light" color="brand" radius="xs">
                                    {chatDetail.assignee_name}
                                  </Badge>
                                ) : (
                                  <Text size="xs" c="dimmed">
                                    Без ответственного
                                  </Text>
                                )}
                              </Group>
                            )}
                          </Stack>
                          {chatDetail ? (
                            <Group gap={8} align="center" wrap="nowrap">
                              <Select
                                size="xs"
                                w={160}
                                label={
                                  <Text component="span" size="xs" fw={600} c="dimmed" tt="uppercase" style={{ letterSpacing: rem(0.5) }}>
                                    Режим AI
                                  </Text>
                                }
                                leftSection={<IconRobot size={14} color="var(--mantine-color-ai-6)" />}
                                data={OMNI_CHAT_AI_MODES.map((v) => ({
                                  value: v,
                                  label:
                                    v === "DISABLED"
                                      ? "Выкл"
                                      : v === "AUTO_REPLY"
                                        ? "Автоответ"
                                        : "Подсказки",
                                }))}
                                value={chatDetail.ai_mode || "DISABLED"}
                                onChange={(v) => {
                                  if (v && selectedChatId)
                                    updateAiMode.mutate({
                                      chatId: selectedChatId,
                                      ai_mode: v,
                                    });
                                }}
                                disabled={updateAiMode.isPending}
                                styles={{
                                  input: { fontWeight: 600 },
                                }}
                              />
                            </Group>
                          ) : null}
                        </Group>
                      )}
                    </Box>
                    <ScrollArea
                      type="scroll"
                      scrollbarSize={6}
                      offsetScrollbars
                      viewportRef={omniMessagesViewportRef}
                      style={{ flex: 1, minHeight: 0, padding: "var(--space-20)" }}
                    >
                      <Stack gap={0} pb={0}>
                        {hasNextPage ? (
                          <Button
                            size="xs"
                            variant="light"
                            fullWidth
                            leftSection={<IconHistory size={14} stroke={1.5} />}
                            onClick={() => void handleLoadOlderMessages()}
                            loading={isFetchingNextPage}
                            disabled={messagesInitialLoading}
                          >
                            Ранее
                          </Button>
                        ) : null}
                        {chatDetail?.lead_id ? (
                          <Stack gap={6} align="flex-end">
                                <Text size="xs" c="dimmed">
                                  CRM‑лид:
                                </Text>
                                <Flex gap="xs" align="center" wrap="wrap" justify="flex-end">
                                  {chatDetail.lead_stage_name && (
                                    <Badge size="xs" variant="light" color="blue">
                                      {chatDetail.lead_stage_name}
                                    </Badge>
                                  )}
                                  <Tooltip label="Прогноз CRM (не проводка ERP)">
                                    <Badge size="xs" variant="outline">
                                      Оценка: {chatDetail.lead_estimated_value ?? "0"} ₽
                                    </Badge>
                                  </Tooltip>
                                  <Tooltip label="Сумма доходов ERP по лиду (0 — пока нет проводок)">
                                    <Badge size="xs" variant="outline" color="green">
                                      Факт (ERP): {chatDetail.lead_actual_value ?? "0"} ₽
                                    </Badge>
                                  </Tooltip>
                                </Flex>
                                <Button
                                  component={Link}
                                  to={`/admin/sales?lead_id=${encodeURIComponent(
                                    chatDetail.lead_id,
                                  )}`}
                                  size="xs"
                                  variant="light"
                                >
                                  Открыть лид
                                </Button>

                                <Divider my={6} />
                                <Stack gap={6} align="flex-end">
                                  <Group gap="xs" justify="flex-end">
                                    <Text size="xs" c="dimmed">
                                      AI‑рекомендации
                                    </Text>
                                    <AiFeatureBadge status={crmStageFeature.status} />
                                  </Group>
                                  <Group gap="xs" justify="flex-end">
                                    <Button
                                      size="xs"
                                      variant="light"
                                      onClick={() => {
                                        if (crmStageFeature.status === "stub") return;
                                        if (!canCrmAi) return;
                                        void logUiEvent({
                                          event_name: "ai_click_summary",
                                          clinic_id: currentClinicId,
                                          feature_id: crmStageFeature.id,
                                          feature_status: crmStageFeature.status,
                                          meta: { lead_id: leadId, chat_id: selectedChatId },
                                        });
                                        aiSummary.refetch();
                                      }}
                                      loading={aiSummary.isFetching}
                                      disabled={crmStageFeature.status === "stub" || !canCrmAi}
                                      title={
                                        crmStageFeature.status === "stub"
                                          ? getAiFeatureTooltip(crmStageFeature.status)
                                          : !canCrmAi
                                            ? "Недостаточно прав или backend‑tool недоступен."
                                            : undefined
                                      }
                                    >
                                      Резюме
                                    </Button>
                                    <Button
                                      size="xs"
                                      variant="light"
                                      onClick={() => {
                                        if (crmStageFeature.status === "stub") return;
                                        if (!canCrmAi) return;
                                        void logUiEvent({
                                          event_name: "ai_click_suggest_stage",
                                          clinic_id: currentClinicId,
                                          feature_id: crmStageFeature.id,
                                          feature_status: crmStageFeature.status,
                                          meta: { lead_id: leadId, chat_id: selectedChatId },
                                        });
                                        aiSuggestStage.refetch();
                                      }}
                                      loading={aiSuggestStage.isFetching}
                                      disabled={crmStageFeature.status === "stub" || !canCrmAi}
                                      title={
                                        crmStageFeature.status === "stub"
                                          ? getAiFeatureTooltip(crmStageFeature.status)
                                          : !canCrmAi
                                            ? "Недостаточно прав или backend‑tool недоступен."
                                            : undefined
                                      }
                                    >
                                      Стадия
                                    </Button>
                                  </Group>

                                  {crmStageFeature.status === "stub" && (
                                    <Text size="xs" c="dimmed" style={{ maxWidth: 360, textAlign: "right" }}>
                                      {getAiFeatureTooltip(crmStageFeature.status)}
                                    </Text>
                                  )}

                                  {aiSummary.data?.summary && (
                                    <Box
                                      p="xs"
                                      style={{
                                        borderRadius: "var(--radius-md)",
                                        background: "var(--primary-alpha-06)",
                                        border: "1px solid var(--primary-alpha-25)",
                                        maxWidth: 360,
                                      }}
                                    >
                                      <Text size="xs" c="dimmed" mb={4}>
                                        {aiSummary.data.ai_status ? `mode: ${aiSummary.data.ai_status}` : "mode: —"}
                                      </Text>
                                      <Text size="sm">{aiSummary.data.summary}</Text>
                                    </Box>
                                  )}

                                  {aiSuggestStage.data && (
                                    <Box
                                      p="xs"
                                      style={{
                                        borderRadius: "var(--radius-md)",
                                        background: "var(--dark-alpha-02)",
                                        border: "1px solid var(--muted-alpha-40)",
                                        maxWidth: 360,
                                      }}
                                    >
                                      <Text size="xs" c="dimmed">
                                        confidence: {Math.round((aiSuggestStage.data.confidence || 0) * 100)}%
                                      </Text>
                                      <Text size="sm">
                                        Рекомендованная стадия:{" "}
                                        {aiSuggestStage.data.suggested_stage_id ?? "—"}
                                      </Text>
                                      {aiSuggestStage.data.rationale && (
                                        <Text size="xs" c="dimmed" mt={4}>
                                          {aiSuggestStage.data.rationale}
                                        </Text>
                                      )}
                                      <Group mt="xs" gap="xs" justify="flex-end">
                                        <Button
                                          size="xs"
                                          variant="outline"
                                          disabled={
                                            crmStageFeature.status === "stub" ||
                                            !canApplyStage ||
                                            !currentClinicId ||
                                            !aiSuggestStage.data.suggested_stage_id ||
                                            aiApplyStage.isPending
                                          }
                                          loading={aiApplyStage.isPending}
                                          onClick={() => {
                                            if (crmStageFeature.status === "stub") return;
                                            if (!canApplyStage) return;
                                            if (!currentClinicId || !aiSuggestStage.data?.suggested_stage_id) return;
                                            void logUiEvent({
                                              event_name: "ai_click_apply_stage",
                                              clinic_id: currentClinicId,
                                              feature_id: crmStageFeature.id,
                                              feature_status: crmStageFeature.status,
                                              meta: {
                                                lead_id: leadId,
                                                chat_id: selectedChatId,
                                                target_stage_id: aiSuggestStage.data.suggested_stage_id,
                                              },
                                            });
                                            aiApplyStage.mutate({
                                              clinic_id: currentClinicId,
                                              target_stage_id: aiSuggestStage.data.suggested_stage_id,
                                              reason: "apply_ai_suggested_stage",
                                              initiated_by_ai: true,
                                            });
                                          }}
                                        >
                                          Применить
                                        </Button>
                                        <Button
                                          size="xs"
                                          variant="subtle"
                                          color="gray"
                                          disabled={crmStageFeature.status === "stub" || !currentClinicId || aiIgnore.isPending}
                                          loading={aiIgnore.isPending}
                                          onClick={() => {
                                            if (crmStageFeature.status === "stub") return;
                                            if (!currentClinicId) return;
                                            void logUiEvent({
                                              event_name: "ai_click_ignore_reco",
                                              clinic_id: currentClinicId,
                                              feature_id: crmStageFeature.id,
                                              feature_status: crmStageFeature.status,
                                              meta: { lead_id: leadId, chat_id: selectedChatId, kind: "stage" },
                                            });
                                            aiIgnore.mutate({
                                              clinic_id: currentClinicId,
                                              kind: "stage",
                                              reason: "operator_ignored",
                                            });
                                          }}
                                        >
                                          Игнорировать
                                        </Button>
                                        <Button
                                          size="xs"
                                          variant="outline"
                                          disabled={
                                            createTaskFeature.status === "stub" ||
                                            !canCreateAiTask ||
                                            !currentClinicId ||
                                            aiCreateTask.isPending
                                          }
                                          loading={aiCreateTask.isPending}
                                          title={
                                            createTaskFeature.status === "stub"
                                              ? getAiFeatureTooltip(createTaskFeature.status)
                                              : !canCreateAiTask
                                                ? "Недостаточно прав или backend‑tool недоступен."
                                                : undefined
                                          }
                                          onClick={() => {
                                            if (createTaskFeature.status === "stub") return;
                                            if (!canCreateAiTask) return;
                                            if (!currentClinicId) return;
                                            void logUiEvent({
                                              event_name: "ai_click_create_task",
                                              clinic_id: currentClinicId,
                                              feature_id: createTaskFeature.id,
                                              feature_status: createTaskFeature.status,
                                              meta: { lead_id: leadId, chat_id: selectedChatId },
                                            });
                                            aiCreateTask.mutate({
                                              clinic_id: currentClinicId,
                                              title: "Follow-up по лиду из чата",
                                              description: aiSuggestStage.data?.rationale ?? undefined,
                                              priority: "medium",
                                              initiated_by_ai: true,
                                              reason: "ai_recommendation_followup",
                                            });
                                          }}
                                        >
                                          Задача
                                        </Button>
                                      </Group>
                                    </Box>
                                  )}
                                </Stack>
                          </Stack>
                        ) : null}
                      {messagesInitialLoading ? (
                        <DataSkeleton lines={3} />
                      ) : (
                        <Stack gap={0} align="stretch" {...ADMIN_CHAT_MESSAGES_REGION}>
                          {mergedMessages.map((m, index) => {
                            const prev = index > 0 ? mergedMessages[index - 1] : null;
                            const metaChannel =
                              m.channel_type ||
                              chatDetail?.channel_type ||
                              "";
                            const outbound =
                              m.direction === "OUTBOUND" && m.actor_type !== "CLIENT";
                            const deliveryInfo = omniMessageDeliveryLabel(m.delivery_status, m.read_status);
                            const timeLabel = m.created_at
                              ? new Date(m.created_at).toLocaleString()
                              : "";
                            const bubbleFg = m.ui_hidden || !outbound ? "var(--mantine-color-dark-8)" : "var(--text-on-primary)";
                            const sameAuthorAsPrev =
                              !!prev &&
                              prev.direction === m.direction &&
                              prev.actor_type === m.actor_type;
                            const hasAudioAttachment = (m.attachments ?? []).some((a) =>
                              (a.content_type || "").toLowerCase().startsWith("audio/")
                            );
                            return (
                              <Stack
                                key={m.id}
                                gap={4}
                                align={outbound ? "flex-end" : "flex-start"}
                                style={{
                                  alignSelf: outbound ? "flex-end" : "flex-start",
                                  maxWidth: "100%",
                                  marginTop: index === 0 ? 0 : sameAuthorAsPrev ? 4 : 16,
                                }}
                                aria-label={timeLabel ? `Сообщение, время: ${timeLabel}` : undefined}
                              >
                                <Box
                                  p={0}
                                  onContextMenu={(e) => {
                                    e.preventDefault();
                                    setMessageContextMenu({
                                      id: m.id,
                                      content: m.content || "",
                                      actorType: m.actor_type,
                                      x: e.clientX,
                                      y: e.clientY,
                                    });
                                  }}
                                  style={{
                                    position: "relative",
                                    maxWidth: "min(85%, 520px)",
                                    minWidth: hasAudioAttachment ? 280 : undefined,
                                    ...(m.ui_hidden
                                      ? adminChatOmniHiddenBubbleStyle()
                                      : outbound
                                        ? adminChatOmniOutboundBubbleStyle()
                                        : adminChatOmniClientInboundBubbleStyle()),
                                    opacity: m.ui_hidden ? 0.9 : 1,
                                  }}
                                >
                                  {m.ui_hidden ? (
                                    <Text size="xs" c="dimmed" p="10px 14px">
                                      Сообщение скрыто: {m.hidden_reason || "без указания причины"}
                                    </Text>
                                  ) : (
                                    <Text
                                      size="sm"
                                      lh={1.55}
                                      p="10px 14px"
                                      component="div"
                                      style={{ wordBreak: "break-word", color: bubbleFg }}
                                    >
                                      <OmniMessageRichBody
                                        content={m.content || ""}
                                        attachments={m.attachments ?? []}
                                        getClinicChatBlob={getClinicChatBlob}
                                        getOmniBlob={(aid) => getOmniBlobForMessage(m.id, aid)}
                                        allowAudioAttachmentDownload={allowAudioAttachmentDownload}
                                      />
                                    </Text>
                                  )}
                                </Box>
                                {timeLabel ? (
                                  <Group gap={4} px={4}>
                                    {!outbound ? (
                                      <OmniChannelMetaIcon channelType={metaChannel} size={10} />
                                    ) : m.actor_type === "AI" ? (
                                      <IconRobot size={12} stroke={1.7} />
                                    ) : (
                                      <IconUser size={12} stroke={1.7} />
                                    )}
                                    <Text size="xs" c="dimmed">
                                      {timeLabel}
                                      {outbound && deliveryInfo ? ` · ${deliveryInfo.label}` : ""}
                                    </Text>
                                  </Group>
                                ) : null}
                              </Stack>
                            );
                          })}
                        </Stack>
                      )}
                    </Stack>
                    </ScrollArea>
                    <Box
                      p="md"
                      bg="var(--mantine-color-body)"
                      style={{
                        flexShrink: 0,
                        borderTop: "1px solid var(--mantine-color-gray-2)",
                      }}
                    >
                    <Stack gap="xs">
                      {replyToMessage ? (
                        <Paper withBorder p="xs" bg="var(--mantine-color-gray-0)">
                          <Group justify="space-between" wrap="nowrap" gap="xs">
                            <Stack gap={2} style={{ minWidth: 0 }}>
                              <Text size="xs" c="dimmed">
                                Ответ на {replyToMessage.actorType === "CLIENT" ? "сообщение клиента" : "сообщение клиники"}
                              </Text>
                              <Text size="xs" lineClamp={1} component="div" style={{ minWidth: 0 }}>
                                <AppleEmojiRichText text={replyToMessage.content || ""} emojiEm={1} />
                              </Text>
                            </Stack>
                            <ActionIcon
                              size="sm"
                              variant="subtle"
                              color="gray"
                              aria-label="Убрать ответ"
                              onClick={() => setReplyToMessage(null)}
                            >
                              <IconChevronRight size={14} style={{ transform: "rotate(90deg)" }} />
                            </ActionIcon>
                          </Group>
                        </Paper>
                      ) : null}
                      <input
                        ref={omniFileInputRef}
                        type="file"
                        style={{ display: "none" }}
                        accept={omniFileAccept}
                        onChange={(e) => {
                          const f = e.target.files?.[0] ?? null;
                          e.target.value = "";
                          setOmniAttachError(null);
                          if (!f) return;
                          if (f.size > MAX_OMNI_UPLOAD_BYTES) {
                            setOmniAttachError("Файл больше 5 МБ");
                            return;
                          }
                          setPendingOmniFile(f);
                        }}
                      />
                      {pendingOmniFile ? (
                        <Text size="xs" c="dimmed">
                          К отправке: {pendingOmniFile.name}{" "}
                          <Text
                            component="button"
                            type="button"
                            span
                            c="red.7"
                            ml="xs"
                            style={{ cursor: "pointer", border: "none", background: "none", font: "inherit" }}
                            onClick={() => setPendingOmniFile(null)}
                          >
                            Убрать
                          </Text>
                        </Text>
                      ) : null}
                      {omniAttachError ? (
                        <Text size="xs" c="red">
                          {omniAttachError}
                        </Text>
                      ) : null}
                      <Group gap="xs" align="flex-end" wrap="nowrap">
                        <Menu shadow="md" width={280} position="top-start">
                          <Menu.Target>
                            <ActionIcon
                              variant="subtle"
                              color="gray"
                              aria-label="Действия: быстрые ответы, взять в работу, обновить"
                            >
                              <IconDotsVertical size={20} stroke={1.5} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item
                              disabled={!selectedChatId}
                              leftSection={<IconRefresh size={14} stroke={1.5} />}
                              onClick={() => handleRefreshOmniThread()}
                            >
                              Обновить переписку
                            </Menu.Item>
                            <Menu.Item
                              disabled={!selectedChatId || patchOmniChat.isPending}
                              onClick={() => handleAssignOmniToMe()}
                            >
                              Взять в работу
                            </Menu.Item>
                            <Menu.Divider />
                            {(quickRepliesData?.items ?? []).map((qr) => (
                              <Menu.Item
                                key={qr.id}
                                onClick={() => {
                                  setMessageText((prev) => (prev ? `${prev}\n${qr.body}` : qr.body));
                                }}
                              >
                                <Stack gap={2}>
                                  <Text size="sm" fw={600}>
                                    {qr.title}
                                  </Text>
                                  <Text size="xs" c="dimmed" lineClamp={2}>
                                    {qr.body}
                                  </Text>
                                </Stack>
                              </Menu.Item>
                            ))}
                          </Menu.Dropdown>
                        </Menu>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          size="lg"
                          aria-label="Документ"
                          onClick={() => {
                            setOmniFileAccept(
                              ".pdf,.doc,.docx,.txt,.xlsx,.xls,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain"
                            );
                            queueMicrotask(() => omniFileInputRef.current?.click());
                          }}
                        >
                          <IconPaperclip size={20} />
                        </ActionIcon>
                        <ActionIcon
                          variant="subtle"
                          color="gray"
                          size="lg"
                          aria-label="Изображение"
                          onClick={() => {
                            setOmniFileAccept("image/*");
                            queueMicrotask(() => omniFileInputRef.current?.click());
                          }}
                        >
                          <IconPhoto size={20} />
                        </ActionIcon>
                        <VoiceNoteRecorderButton
                          disabled={!selectedChatId || sendOmniWithFile.isPending || sendMessage.isPending}
                          onError={(msg) => setOmniAttachError(msg)}
                          onRecorded={(file) => {
                            setOmniAttachError(null);
                            if (file.size > MAX_OMNI_UPLOAD_BYTES) {
                              setOmniAttachError("Файл больше 5 МБ");
                              return;
                            }
                            setPendingOmniFile(file);
                          }}
                        />
                        <EmojiMartPopoverPicker
                          actionIconProps={{ variant: "subtle", color: "gray", size: "lg" }}
                          onPick={(native) => setMessageText((prev) => prev + native)}
                          onInserted={() => messageComposerRef.current?.focus()}
                        />
                        <AppleEmojiOverlayTextarea
                          ref={messageComposerRef}
                          autosize
                          minRows={1}
                          maxRows={6}
                          placeholder={`Написать ответ в ${effectiveReplyLabel || "канал"} (Ctrl+Enter)...`}
                          value={messageText}
                          size="sm"
                          onChange={(e) => setMessageText(e.currentTarget.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                              e.preventDefault();
                              handleSend();
                            }
                          }}
                          style={{ flex: 1, minWidth: 180 }}
                          styles={{ input: { border: `1px solid var(--mantine-color-gray-3)` } }}
                        />
                        <ActionIcon
                          size="lg"
                          color="indigo"
                          variant="filled"
                          onClick={handleSend}
                          disabled={(!messageText.trim() && !pendingOmniFile) || !selectedChatId}
                          loading={sendMessage.isPending || sendOmniWithFile.isPending}
                          aria-label="Отправить сообщение"
                        >
                          <IconSend size={18} />
                        </ActionIcon>
                      </Group>
                      <Group gap="sm" mt="xs" align="center" wrap="wrap">
                        <Button
                          size="xs"
                          variant="subtle"
                          leftSection={<IconCalendarPlus size={14} stroke={1.5} />}
                          title={!patientId ? "Выберите чат с привязанным пациентом" : "Создать запись без перехода в расписание (⌘B / Ctrl+B)"}
                          onClick={handleOpenBookingModal}
                          disabled={!patientId || !currentClinicId}
                        >
                          Запись
                        </Button>
                        <Button
                          size="xs"
                          variant="subtle"
                          leftSection={<IconFileDescription size={14} stroke={1.5} />}
                          onClick={() => setFormDrawerOpen(true)}
                          disabled={!patientId}
                          title={!patientId ? "Выберите чат с привязанным пациентом" : "Отправить анкету/форму"}
                        >
                          Анкета
                        </Button>
                        {selectedChatId && effectiveReplyChannelId && replyChannelOptions.length > 1 ? (
                          <Select
                            size="xs"
                            data={replyChannelOptions}
                            value={effectiveReplyChannelId}
                            onChange={(v) => setReplyChannelPick(v)}
                            w={180}
                          />
                        ) : null}
                        <Checkbox
                          size="xs"
                          label="Скрытые сообщения"
                          checked={showHiddenMessages}
                          onChange={(e) => setShowHiddenMessages(e.currentTarget.checked)}
                          styles={{ label: { color: "var(--mantine-color-dimmed)" } }}
                        />
                      </Group>
                    </Stack>
                  </Box>
                  </Box>
              )}
              </Flex>
              <Box
                w={inspectorCollapsed ? 56 : 350}
                miw={inspectorCollapsed ? 56 : 350}
                style={{
                  borderLeft: "1px solid var(--mantine-color-gray-2)",
                  backgroundColor: "white",
                  minHeight: 0,
                  display: "flex",
                  flexDirection: "column",
                  overflow: "hidden",
                }}
              >
                {inspectorCollapsed ? (
                  <Paper
                    p={4}
                    radius="md"
                    withBorder
                    shadow="none"
                    bg="var(--bg-card)"
                    style={{ borderColor: "var(--divider)", height: "100%" }}
                  >
                    <Stack gap={6} align="center" py="xs" style={{ minWidth: 0 }}>
                      <Tooltip
                        label="Развернуть рабочий центр (Ctrl+Shift+L / ⌘⇧L)"
                        position="left"
                      >
                        <ActionIcon
                          variant="light"
                          color="gray"
                          size="md"
                          onClick={() => setInspectorCollapsed(false)}
                          aria-label="Развернуть рабочий центр"
                        >
                          <IconChevronLeft size={18} stroke={1.5} />
                        </ActionIcon>
                      </Tooltip>
                      {currentClinicId ? (
                        <>
                          <Divider w="100%" style={{ borderTopColor: "var(--divider)" }} />
                          <Tooltip label="CRM" position="left">
                            <ActionIcon
                              component={Link}
                              to={ROUTE_PATHS.admin.sales}
                              variant="subtle"
                              color="blue"
                              size="md"
                              aria-label="CRM"
                            >
                              <IconBriefcase size={18} stroke={1.5} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Расписание" position="left">
                            <ActionIcon
                              component={Link}
                              to={ROUTE_PATHS.admin.schedule}
                              variant="subtle"
                              color={SEMANTIC.action.confirm}
                              size="md"
                              aria-label="Расписание"
                            >
                              <IconCalendarEvent size={18} stroke={1.5} />
                            </ActionIcon>
                          </Tooltip>
                          <Tooltip label="Задачи" position="left">
                            <ActionIcon
                              component={Link}
                              to={ROUTE_PATHS.admin.tasks}
                              variant="subtle"
                              color="gray"
                              size="md"
                              aria-label="Задачи"
                            >
                              <IconListCheck size={18} stroke={1.5} />
                            </ActionIcon>
                          </Tooltip>
                          <Divider w="100%" style={{ borderTopColor: "var(--divider)" }} />
                        </>
                      ) : null}
                      <Tooltip label="Клиент" position="left">
                        <ActionIcon
                          variant={inspectorTab === "client" ? "light" : "subtle"}
                          color="dark"
                          size="md"
                          aria-label="Вкладка Клиент"
                          onClick={() => {
                            setInspectorTab("client");
                            setInspectorCollapsed(false);
                          }}
                        >
                          <IconUser size={18} stroke={1.5} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Анкеты" position="left">
                        <ActionIcon
                          variant={inspectorTab === "forms" ? "light" : "subtle"}
                          color="dark"
                          size="md"
                          aria-label="Вкладка Анкеты"
                          onClick={() => {
                            setInspectorTab("forms");
                            setInspectorCollapsed(false);
                          }}
                        >
                          <IconFileDescription size={18} stroke={1.5} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="Таймлайн" position="left">
                        <ActionIcon
                          variant={inspectorTab === "timeline" ? "light" : "subtle"}
                          color="dark"
                          size="md"
                          aria-label="Вкладка Таймлайн"
                          onClick={() => {
                            setInspectorTab("timeline");
                            setInspectorCollapsed(false);
                          }}
                        >
                          <IconHistory size={18} stroke={1.5} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label="AI" position="left">
                        <ActionIcon
                          variant={inspectorTab === "ai" ? "light" : "subtle"}
                          color="dark"
                          size="md"
                          aria-label="Вкладка AI"
                          onClick={() => {
                            setInspectorTab("ai");
                            setInspectorCollapsed(false);
                          }}
                        >
                          <IconRobot size={18} stroke={1.5} />
                        </ActionIcon>
                      </Tooltip>
                    </Stack>
                  </Paper>
                ) : (
                <Stack gap="sm" style={{ minWidth: 0 }} p="sm">
                  <Paper
                    p="sm"
                    radius="md"
                    withBorder
                    shadow="none"
                    bg="var(--bg-card)"
                    style={{ borderColor: "var(--divider)" }}
                  >
                    <Stack gap="sm">
                      {currentClinicId ? (
                        <>
                          <Group justify="space-between" align="flex-start" wrap="nowrap" gap="xs">
                            <Stack gap={2} style={{ minWidth: 0 }}>
                              <Text size="xs" fw={700} tt="uppercase" c="dimmed" style={{ letterSpacing: rem(0.4) }}>
                                Рабочий центр
                              </Text>
                              <Text size="xs" c="dimmed" lineClamp={2}>
                                Быстрые переходы: воронка, расписание, задачи.
                              </Text>
                            </Stack>
                            <Tooltip
                              label="Свернуть в иконки — больше места для чата (Ctrl+Shift+L / ⌘⇧L)"
                              position="left"
                            >
                              <ActionIcon
                                variant="subtle"
                                color="gray"
                                size="sm"
                                onClick={() => setInspectorCollapsed(true)}
                                aria-label="Свернуть рабочий центр"
                              >
                                <IconChevronRight size={18} stroke={1.5} />
                              </ActionIcon>
                            </Tooltip>
                          </Group>
                          <Group gap={6} wrap="wrap">
                            <Button
                              component={Link}
                              to={ROUTE_PATHS.admin.sales}
                              size="compact-xs"
                              variant="subtle"
                              color="blue"
                              leftSection={<IconBriefcase size={14} stroke={1.5} />}
                            >
                              CRM
                            </Button>
                            <Button
                              component={Link}
                              to={ROUTE_PATHS.admin.schedule}
                              size="compact-xs"
                              variant="subtle"
                              color={SEMANTIC.action.confirm}
                              leftSection={<IconCalendarEvent size={14} stroke={1.5} />}
                            >
                              Расписание
                            </Button>
                            <Button
                              component={Link}
                              to={ROUTE_PATHS.admin.tasks}
                              size="compact-xs"
                              variant="subtle"
                              color="gray"
                              leftSection={<IconListCheck size={14} stroke={1.5} />}
                            >
                              Задачи
                            </Button>
                          </Group>
                          <Divider style={{ borderTopColor: "var(--divider)" }} />
                        </>
                      ) : null}
                      <Tabs
                        value={inspectorTab}
                        onChange={(v) => v && setInspectorTab(v as OmniInspectorTab)}
                        variant="pills"
                        radius="xl"
                        color="indigo"
                        styles={{
                          list: {
                            width: "100%",
                            flexWrap: "nowrap",
                            backgroundColor: "var(--bg-main)",
                            border: "1px solid var(--divider)",
                            padding: rem(3),
                            borderRadius: "var(--mantine-radius-sm)",
                            gap: rem(2),
                          },
                          tab: {
                            fontSize: "var(--mantine-font-size-xs)",
                            fontWeight: 600,
                          },
                          panel: {
                            minHeight: 300,
                          },
                        }}
                      >
                        <Tabs.List grow>
                          <Tabs.Tab value="client">Клиент</Tabs.Tab>
                          <Tabs.Tab value="forms">Анкеты</Tabs.Tab>
                          <Tabs.Tab value="timeline">Таймлайн</Tabs.Tab>
                          <Tabs.Tab value="ai">AI</Tabs.Tab>
                        </Tabs.List>
                        <Tabs.Panel value="client" pt="sm">
                          <OmniInspectorTabShell
                            title="Клиент"
                            description="Лояльность и задачи по выбранному контакту."
                          >
                            <Stack gap="md">
                              <OmniInspectorSection title="Профиль и лояльность">
                                {loyaltySummary ? (
                                  <Stack gap="xs">
                                    <Text size="xs" c="dimmed">
                                      Баланс и подписки
                                    </Text>
                                    {loyaltySummary.wallet ? (
                                      <Badge size="xs" variant="outline" color="teal">
                                        Баланс: {loyaltySummary.wallet.balance}{" "}
                                        {loyaltySummary.wallet.currency}
                                      </Badge>
                                    ) : (
                                      <Text size="xs" c="dimmed">
                                        Нет кошелька
                                      </Text>
                                    )}
                                    <Text size="xs" c="dimmed">
                                      Активных абонементов:{" "}
                                      {
                                        loyaltySummary.subscriptions.filter(
                                          (s) => s.status === "active",
                                        ).length
                                      }
                                    </Text>
                                    {loyaltySummary.patient_id ? (
                                      <Group gap="xs">
                                        <Button
                                          component={Link}
                                          to={ROUTE_PATHS.admin.schedule}
                                          size="xs"
                                          variant="subtle"
                                          color={SEMANTIC.action.confirm}
                                        >
                                          Создать запись
                                        </Button>
                                        <Button
                                          component={Link}
                                          to={`/admin/loyalty?patient_id=${encodeURIComponent(
                                            loyaltySummary.patient_id,
                                          )}`}
                                          size="xs"
                                          variant="subtle"
                                          color={SEMANTIC.action.confirm}
                                        >
                                          Открыть лояльность
                                        </Button>
                                      </Group>
                                    ) : null}
                                  </Stack>
                                ) : (
                                  <Text size="xs" c="dimmed">
                                    Данные по лояльности будут доступны после выбора чата.
                                  </Text>
                                )}
                              </OmniInspectorSection>
                              <OmniInspectorSection title="Задачи">
                                <Text size="xs" c="dimmed">
                                  Открытых задач в клинике: {openTasksCount}
                                </Text>
                                <Group gap="xs" wrap="wrap">
                                  <Button
                                    size="xs"
                                    variant="subtle"
                                    color="gray"
                                    onClick={handleOpenTaskDrawer}
                                    disabled={createTaskFeature.status === "stub" || !canCreateAiTask}
                                    title={
                                      createTaskFeature.status === "stub"
                                        ? getAiFeatureTooltip(createTaskFeature.status)
                                        : !canCreateAiTask
                                          ? "Недостаточно прав или backend‑tool недоступен."
                                          : "Создать задачу по контексту чата"
                                    }
                                  >
                                    Создать задачу
                                  </Button>
                                  <Button
                                    component={Link}
                                    to={ROUTE_PATHS.admin.tasks}
                                    size="xs"
                                    variant="subtle"
                                    color="gray"
                                  >
                                    Открыть список задач
                                  </Button>
                                </Group>
                              </OmniInspectorSection>
                            </Stack>
                          </OmniInspectorTabShell>
                        </Tabs.Panel>
                        <Tabs.Panel value="forms" pt="sm">
                          <OmniInspectorTabShell
                            title="Анкеты и согласия"
                            description="Статус форм пациента и быстрые действия."
                          >
                            {!patientId ? (
                              <Text size="xs" c="dimmed">
                                Выберите чат с привязанным пациентом, чтобы видеть статус форм.
                              </Text>
                            ) : (
                              <Stack gap="sm">
                                <Text size="xs" c="dimmed">
                                  Заполнено форм: {formSubmissions?.length ?? 0}
                                </Text>
                                {formSubmissions && formSubmissions.length > 0 ? (
                                  <Stack gap={6}>
                                    {formSubmissions.map((s) => (
                                      <Group key={s.id} gap="xs" align="flex-start" wrap="nowrap">
                                        <Badge size="xs" variant="light" color="gray">
                                          Форма
                                        </Badge>
                                        <Text size="xs" lineClamp={2}>
                                          {s.template_name}
                                        </Text>
                                      </Group>
                                    ))}
                                  </Stack>
                                ) : null}
                                <Button
                                  component={Link}
                                  to={`/admin/forms?patient_id=${encodeURIComponent(patientId)}`}
                                  size="xs"
                                  variant="subtle"
                                  color={SEMANTIC.action.send}
                                >
                                  Открыть формы и согласия
                                </Button>
                                <Text size="xs" c="dimmed">
                                  Отправьте пациенту ссылку на раздел «Анкеты и согласия» в PWA, чтобы
                                  он заполнил недостающие формы.
                                </Text>
                              </Stack>
                            )}
                          </OmniInspectorTabShell>
                        </Tabs.Panel>
                        <Tabs.Panel value="timeline" pt="sm">
                          <OmniInspectorTabShell
                            title="Таймлайн"
                            description="Сводка событий по пациенту (краткий вид)."
                          >
                            {loyaltySummary?.patient_id ? (
                              <Stack gap="sm">
                                <Text size="xs" c="dimmed">
                                  История записей и форм недоступна в кратком виде. Откройте формы и
                                  историю, чтобы увидеть детали.
                                </Text>
                                <Button
                                  component={Link}
                                  to={`/admin/forms`}
                                  size="xs"
                                  variant="subtle"
                                  color={SEMANTIC.action.send}
                                >
                                  Открыть формы и согласия
                                </Button>
                              </Stack>
                            ) : (
                              <Text size="xs" c="dimmed">
                                Нет связанного пациента. Выберите чат с привязанным контактом.
                              </Text>
                            )}
                          </OmniInspectorTabShell>
                        </Tabs.Panel>
                        <Tabs.Panel value="ai" pt="sm">
                          <OmniInspectorTabShell
                            title="AI‑агент"
                            description="Управляйте режимом работы AI‑агента в этом диалоге и наблюдайте за качеством ответов."
                          >
                            <Group gap="xs" align="center" wrap="wrap">
                              <Text size="xs" c="dimmed">
                                Spotlight (статус флага):
                              </Text>
                              <AiFeatureBadge status={spotlightGate.feature.status} />
                              {!spotlightGate.enabled && spotlightGate.disabledReason ? (
                                <Text size="xs" c="dimmed">
                                  {spotlightGate.disabledReason}
                                </Text>
                              ) : null}
                            </Group>
                            <OmniInspectorSection title="Функции Omni / AI">
                              <Stack gap={6}>
                                {aiFeatures.list.map((f) => (
                                  <Group key={f.id} gap="xs" align="flex-start" wrap="nowrap">
                                    <AiFeatureBadge status={f.status} />
                                    <Stack gap={0}>
                                      <Text size="xs" fw={500}>
                                        {f.label}
                                      </Text>
                                      {f.description ? (
                                        <Text size="xs" c="dimmed" lineClamp={3}>
                                          {f.description}
                                        </Text>
                                      ) : null}
                                    </Stack>
                                  </Group>
                                ))}
                              </Stack>
                            </OmniInspectorSection>
                            {chatDetail ? (
                              <Text size="xs" c="dimmed">
                                Текущий режим:{" "}
                                {chatDetail.ai_mode === "AUTO_REPLY"
                                  ? "Автоответ"
                                  : chatDetail.ai_mode === "ASSISTANT"
                                    ? "Подсказки"
                                    : "Выкл"}
                              </Text>
                            ) : null}
                          </OmniInspectorTabShell>
                        </Tabs.Panel>
                      </Tabs>
                    </Stack>
                  </Paper>
                </Stack>
              )}
              </Box>
            </Flex>
            </Box>
          )}
        </Stack>
      </Box>

      {messageContextMenu ? (
        <Paper
          withBorder
          shadow="md"
          p={4}
          style={{
            position: "fixed",
            left: messageContextMenu.x,
            top: messageContextMenu.y,
            zIndex: 400,
            minWidth: 180,
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <Stack gap={2}>
            <Button
              size="xs"
              variant="subtle"
              color="gray"
              justify="flex-start"
              leftSection={<IconMessageReply size={14} />}
              onClick={() => {
                handleReplyToMessage({
                  id: messageContextMenu.id,
                  content: messageContextMenu.content,
                  actorType: messageContextMenu.actorType,
                });
                setMessageContextMenu(null);
              }}
            >
              Ответить
            </Button>
            <Button
              size="xs"
              variant="subtle"
              color="gray"
              justify="flex-start"
              leftSection={<IconCopy size={14} />}
              onClick={() => {
                handleCopyMessage(messageContextMenu.content || "");
                setMessageContextMenu(null);
              }}
            >
              Копировать
            </Button>
            <Button
              size="xs"
              variant="subtle"
              color="gray"
              justify="flex-start"
              leftSection={<IconSend size={14} />}
              onClick={() => {
                setMessageContextMenu(null);
              }}
            >
              Переслать (скоро)
            </Button>
            <Button
              size="xs"
              variant="subtle"
              color="red"
              justify="flex-start"
              leftSection={<IconEyeOff size={14} />}
              onClick={() => {
                handleOpenHideModal(messageContextMenu.id);
                setMessageContextMenu(null);
              }}
            >
              Скрыть сообщение
            </Button>
          </Stack>
        </Paper>
      ) : null}

      <GlassModal
        opened={hideModalOpen}
        onClose={() => setHideModalOpen(false)}
        title="Скрыть сообщение"
        centered
      >
        <Stack gap="md">
          <Text size="sm" c="dimmed">
            Укажите причину скрытия. Сообщение останется в истории, но будет скрыто в
            обычном режиме просмотра.
          </Text>
          <Textarea
            label="Причина скрытия"
            minRows={3}
            value={hideReason}
            onChange={(e) => setHideReason(e.currentTarget.value)}
          />
          <Flex justify="flex-end" gap="sm">
            <Button
              variant="subtle"
              color={SEMANTIC.action.dismiss}
              size="sm"
              onClick={() => setHideModalOpen(false)}
              disabled={hideMessage.isPending}
            >
              Отмена
            </Button>
            <Button
              size="sm"
              color={SEMANTIC.action.danger}
              onClick={handleConfirmHide}
              loading={hideMessage.isPending}
            >
              Скрыть
            </Button>
          </Flex>
        </Stack>
      </GlassModal>

      <GlassModal
        opened={bookingModalOpen}
        onClose={() => setBookingModalOpen(false)}
        title="Быстрая запись из чата"
        centered
      >
        <Stack gap="md">
          {!patientId ? (
            <Text size="sm" c="dimmed">
              Выберите чат с привязанным пациентом.
            </Text>
          ) : (
            <>
              <Select
                label="Врач"
                placeholder="Выберите врача"
                data={(doctors ?? []).map((d) => ({ value: d.id, label: d.full_name }))}
                value={bookingDoctorId}
                onChange={setBookingDoctorId}
                searchable
              />
              <Select
                label="Услуга"
                placeholder="Выберите услугу"
                data={(services ?? []).map((s) => ({ value: s.id, label: s.name }))}
                value={bookingServiceId}
                onChange={setBookingServiceId}
                searchable
              />
              <Group grow>
                <TextInput
                  label="Дата"
                  type="date"
                  value={bookingDate}
                  onChange={(e) => setBookingDate(e.currentTarget.value)}
                />
                <TextInput
                  label="Время"
                  type="time"
                  value={bookingTime}
                  onChange={(e) => setBookingTime(e.currentTarget.value)}
                />
              </Group>
              <Textarea
                label="Комментарий"
                minRows={2}
                placeholder="Опционально"
                value={bookingNotes}
                onChange={(e) => setBookingNotes(e.currentTarget.value)}
              />
              {createBooking.isError ? (
                <QueryErrorAlert error={createBooking.error} title="Не удалось создать запись" />
              ) : null}
              <Group justify="flex-end">
                <Button variant="subtle" color={SEMANTIC.action.dismiss} onClick={() => setBookingModalOpen(false)}>
                  Отмена
                </Button>
                <Button
                  color={SEMANTIC.action.confirm}
                  onClick={handleCreateBooking}
                  loading={createBooking.isPending}
                  disabled={!bookingDoctorId || !bookingServiceId || !bookingDate || !bookingTime || !patientId}
                >
                  Создать запись
                </Button>
              </Group>
            </>
          )}
        </Stack>
      </GlassModal>

      <AdminDrawer
        opened={formDrawerOpen}
        onClose={() => setFormDrawerOpen(false)}
        position="right"
        size="sm"
        title="Отправить форму"
      >
        <Stack gap="md">
          {!patientId ? (
            <Text size="sm" c="dimmed">
              Выберите чат с привязанным пациентом, чтобы отправить форму.
            </Text>
          ) : (
            <>
              <Select
                label="Шаблон формы"
                placeholder="Выберите шаблон"
                data={(formTemplates ?? []).map((t) => ({ value: t.id, label: t.name }))}
                value={formTemplateId}
                onChange={(v) => setFormTemplateId(v)}
                searchable
              />
              <Select
                label="Куда отправить"
                data={[
                  { value: "copy_only", label: "Скопировать ссылку" },
                  { value: "whatsapp", label: "WhatsApp" },
                  { value: "sms", label: "SMS" },
                ]}
                value={formSendVia}
                onChange={(v) => setFormSendVia((v as "whatsapp" | "sms" | "copy_only") || "copy_only")}
              />
              <Group justify="flex-end">
                <Button variant="subtle" color={SEMANTIC.action.dismiss} onClick={() => setFormDrawerOpen(false)}>
                  Отмена
                </Button>
                <Button
                  color={SEMANTIC.action.send}
                  onClick={handleSendFormLink}
                  loading={sendFormLink.isPending}
                  disabled={!formTemplateId}
                >
                  Отправить ссылку
                </Button>
              </Group>
            </>
          )}
        </Stack>
      </AdminDrawer>

      <AdminDrawer
        opened={taskDrawerOpen}
        onClose={() => setTaskDrawerOpen(false)}
        position="right"
        size="sm"
        title={
          <Group gap="xs" wrap="wrap">
            <Text fw={600}>Создать задачу</Text>
            <AiFeatureBadge status={createTaskFeature.status} size="sm" />
          </Group>
        }
      >
        <Stack gap="md">
          {createTaskFeature.status === "stub" && (
            <Text size="sm" c="dimmed">
              {getAiFeatureTooltip(createTaskFeature.status)}
            </Text>
          )}
          <TextInput
            label="Заголовок"
            value={taskTitle}
            onChange={(e) => setTaskTitle(e.currentTarget.value)}
            required
          />
          <Textarea
            label="Описание"
            minRows={3}
            value={taskDescription}
            onChange={(e) => setTaskDescription(e.currentTarget.value)}
          />
          <Select
            label="Приоритет"
            data={[
              { value: "low", label: "Низкий" },
              { value: "medium", label: "Средний" },
              { value: "high", label: "Высокий" },
              { value: "urgent", label: "Срочно" },
            ]}
            value={taskPriority}
            onChange={setTaskPriority}
          />
          <TextInput
            label="Срок (опционально)"
            type="datetime-local"
            value={taskDueAt}
            onChange={(e) => setTaskDueAt(e.currentTarget.value)}
          />
          <Checkbox
            label="Взять в работу"
            checked={taskAssignMe}
            onChange={(e) => setTaskAssignMe(e.currentTarget.checked)}
          />
          <Text size="xs" c="dimmed">
            Привязки: {leadId ? `lead_id=${leadId}` : "lead_id=—"},{" "}
            {patientId ? `patient_id=${patientId}` : "patient_id=—"}
          </Text>
          {createTaskMutation.isError && (
            <QueryErrorAlert error={createTaskMutation.error} title="Не удалось создать задачу" />
          )}
          <Group justify="flex-end">
            <Button variant="subtle" color={SEMANTIC.action.dismiss} onClick={() => setTaskDrawerOpen(false)}>
              Отмена
            </Button>
            <Button
              color={SEMANTIC.action.confirm}
              onClick={handleCreateTask}
              loading={createTaskMutation.isPending}
              disabled={createTaskFeature.status === "stub" || !canCreateAiTask || !taskTitle.trim()}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>
    </Stack>
  );
}
