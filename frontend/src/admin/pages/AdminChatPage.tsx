import { useState, useEffect, useCallback, useRef } from "react";
import {
  useAdminChatConversations,
  useAdminChatMessages,
  useSendAdminMessage,
  useSendAdminMessageWithFile,
  useAdminAssignConversation,
  useAdminChatMarkRead,
  useDeleteAdminMessage,
} from "@/hooks/useAdminChat";
import {
  useConversationSummary,
  useSuggestReply,
  type ConversationSummaryWithStatus,
  type SuggestReplyWithStatus,
} from "@/hooks/useChatAi";
import { api } from "@/api/client";
import { useAdminSession } from "@/hooks/useAdminSession";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { QueryErrorAlert, ContextBar, AdminDataTableToolbar } from "@/shared/ui";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { ADMIN_CHAT_MESSAGES_REGION, adminChatIncomingBubbleStyle, adminChatOutgoingBubbleStyle } from "@/shared/adminChatChrome";
import { SEMANTIC } from "@/shared/semanticUi";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { ClinicChatAttachments } from "@/shared/ClinicChatAttachments";
import {
  shouldOmitChatBodyForAudioAttachment,
  shouldOmitOmniMediaPlaceholder,
} from "@/shared/chatMessageBodyDisplay";
import { EmojiMartPopoverPicker, AppleEmojiOverlayTextarea } from "@/shared/ui";
import { VoiceNoteRecorderButton } from "@/shared/ui/VoiceNoteRecorderButton";
import {
  ActionIcon,
  Box,
  Button,
  Flex,
  Grid,
  Group,
  Loader,
  Paper,
  ScrollArea,
  Select,
  Stack,
  Text,
  TextInput,
  Tooltip,
} from "@mantine/core";
import type { ChatMessageDto } from "@/api/types";
import { IconPaperclip, IconPhoto, IconVolume } from "@tabler/icons-react";

const MAX_CHAT_FILE_BYTES = 5 * 1024 * 1024;

const ADMIN_PATIENT_CHAT_DOC_ACCEPT =
  ".pdf,.doc,.docx,.txt,.xlsx,.xls,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain";

export default function AdminChatPage() {
  const { data: adminSession } = useAdminSession();
  const allowAudioAttachmentDownload = adminSession?.roles?.includes("owner") ?? false;

  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messageText, setMessageText] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiSummaryStatus, setAiSummaryStatus] = useState<string | null>(null);
  const [aiVariants, setAiVariants] = useState<string[]>([]);
  const [aiSuggestStatus, setAiSuggestStatus] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const triggerAttachPick = useCallback((mode: "doc" | "image" | "audio") => {
    const el = fileInputRef.current;
    if (!el) return;
    if (mode === "doc") el.accept = ADMIN_PATIENT_CHAT_DOC_ACCEPT;
    else if (mode === "image") el.accept = "image/*";
    else el.accept = "audio/*";
    el.value = "";
    el.click();
  }, []);

  const { data: convData, isLoading: convLoading, isError: convError, error: convErr } = useAdminChatConversations({
    filter,
    search: search || undefined,
    skip: 0,
    limit: 100,
  });

  const { data: msgData, isLoading: msgLoading } = useAdminChatMessages(
    selectedId,
    null,
    100
  );

  const sendMessage = useSendAdminMessage();
  const sendWithFile = useSendAdminMessageWithFile();
  const assignConv = useAdminAssignConversation();
  const markRead = useAdminChatMarkRead();
  const deleteMessage = useDeleteAdminMessage();
  const summaryMutation = useConversationSummary(selectedId);
  const suggestMutation = useSuggestReply(selectedId);

  useEffect(() => {
    if (selectedId) {
      markRead.mutate({ conversationId: selectedId });
    }
  }, [selectedId]);

  const selectedItem = convData?.items?.find((c) => c.conversation_id === selectedId) ?? null;

  const getAttachmentBlob = useCallback(
    (attachmentId: string) => {
      if (!selectedId) return Promise.reject(new Error("no conversation"));
      return api.getBlob(
        `/v1/admin/chat/conversations/${selectedId}/attachments/${attachmentId}/file`
      );
    },
    [selectedId]
  );

  const handleSend = () => {
    if (!selectedId) return;
    setAttachError(null);
    if (pendingFile) {
      if (pendingFile.size > MAX_CHAT_FILE_BYTES) {
        setAttachError("Файл больше 5 МБ");
        return;
      }
      const body = messageText.trim() || (pendingFile.type.startsWith("audio/") ? "" : "");
      sendWithFile.mutate(
        { conversationId: selectedId, body, file: pendingFile },
        {
          onSuccess: () => {
            setMessageText("");
            setPendingFile(null);
          },
          onError: () => setAttachError("Не удалось отправить файл"),
        }
      );
      return;
    }
    if (!messageText.trim()) return;
    sendMessage.mutate(
      { conversationId: selectedId, body: messageText.trim() },
      { onSuccess: () => setMessageText("") }
    );
  };

  const handleAiSummary = async () => {
    if (!selectedId) return;
    setAiSummary(null);
    setAiSummaryStatus(null);
    setAiError(null);
    try {
      const res: ConversationSummaryWithStatus = await summaryMutation.mutateAsync();
      setAiSummary(res.summary);
      setAiSummaryStatus(res.aiStatus);
    } catch {
      setAiError("Подсказка резюме временно недоступна. Попробуйте ещё раз позже.");
    }
  };

  const handleAiSuggest = async () => {
    if (!selectedId) return;
    setAiVariants([]);
    setAiSuggestStatus(null);
    setAiError(null);
    try {
      const res: SuggestReplyWithStatus = await suggestMutation.mutateAsync(undefined);
      setAiVariants(res.variants || []);
      setAiSuggestStatus(res.aiStatus);
    } catch {
      setAiError("AI‑подсказка временно недоступна. Напишите ответ вручную.");
    }
  };

  const handleAssign = () => {
    if (!selectedId) return;
    assignConv.mutate({ conversationId: selectedId });
  };
  const handleDeleteMessage = (messageId: string) => {
    if (!selectedId) return;
    deleteMessage.mutate({ conversationId: selectedId, messageId });
  };

  const onPickFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    setAttachError(null);
    const f = e.target.files?.[0] ?? null;
    e.target.value = "";
    if (!f) return;
    if (f.size > MAX_CHAT_FILE_BYTES) {
      setAttachError("Файл больше 5 МБ");
      return;
    }
    setPendingFile(f);
  };

  const sending = sendMessage.isPending || sendWithFile.isPending;
  const canSend = pendingFile ? true : Boolean(messageText.trim());

  const patientChatSubtitle = (
    <Text size="sm" c="dimmed" maw={720} lh={1.4}>
      Диалоги с пациентами из PWA. Текст и вложения; <strong>голос</strong> — микрофон или аудиофайл (без
      видео-кружков). До 5 МБ.
    </Text>
  );

  if (convLoading) {
    return (
      <Stack>
        <ContextBar title="Чат с пациентами" breadcrumbs={patientChatSubtitle} />
        <DataSkeleton lines={5} />
      </Stack>
    );
  }
  if (convError) {
    return (
      <Stack>
        <ContextBar title="Чат с пациентами" breadcrumbs={patientChatSubtitle} />
        <QueryErrorAlert error={convErr} title="Не удалось загрузить диалоги" />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <input ref={fileInputRef} type="file" style={{ display: "none" }} onChange={onPickFile} />
      <ContextBar title="Чат с пациентами" breadcrumbs={patientChatSubtitle} />
      {(summaryMutation.isPending || suggestMutation.isPending) && (
        <Group gap="xs">
          <Loader size="xs" />
          <Text size="xs" c="dimmed">
            AI думает…
          </Text>
        </Group>
      )}
      {aiError && (
        <QueryErrorAlert error={aiError} title="AI‑подсказки недоступны" />
      )}
      <AdminDataTableToolbar>
        <Flex gap="sm" wrap="wrap" w="100%">
          <Select
            placeholder="Фильтр"
            data={[
              { value: "all", label: "Все" },
              { value: "mine", label: "Мои" },
              { value: "unassigned", label: "Без ответа" },
            ]}
            value={filter}
            onChange={(v) => setFilter(v ?? "all")}
            w={140}
          />
          <TextInput
            placeholder="Поиск по имени или телефону"
            value={search}
            onChange={(e) => setSearch(e.currentTarget.value)}
            style={{ flex: 1, minWidth: 200 }}
          />
        </Flex>
      </AdminDataTableToolbar>

      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Paper p="sm" radius="md" withBorder style={{ maxHeight: 420 }}>
            <ScrollArea h={380} type="scroll">
              {!convData?.items?.length ? (
                <EmptyStateHint
                  title="Нет диалогов"
                  subtitle="Сообщения появятся, когда пациенты напишут или пришлют голосовое из приложения."
                />
              ) : (
                <Stack gap="xs">
                  {convData.items.map((c) => (
                    <Box
                      key={c.conversation_id}
                      p="xs"
                      style={{
                        cursor: "pointer",
                        borderRadius: "var(--radius-md)",
                        backgroundColor: selectedId === c.conversation_id ? "var(--primary-alpha-12)" : undefined,
                      }}
                      onClick={() => {
                        setSelectedId(c.conversation_id);
                        setPendingFile(null);
                        setAttachError(null);
                      }}
                    >
                      <Text fw={700} size="sm" truncate>
                        {c.patient_name || "Без имени"}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {c.patient_phone}
                      </Text>
                      {c.unread_by_admin_count > 0 && (
                        <Text size="xs" c={SEMANTIC.opsSeverity.critical}>
                          {c.unread_by_admin_count} непрочитанных
                        </Text>
                      )}
                    </Box>
                  ))}
                </Stack>
              )}
            </ScrollArea>
          </Paper>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Paper p="md" radius="md" withBorder style={{ minHeight: 420 }}>
            {!selectedId ? (
              <EmptyStateHint title="Выберите диалог" subtitle="Клик по строке слева." />
            ) : (
              <Stack gap="md" style={{ height: "100%" }}>
                <Flex justify="space-between" align="center" wrap="wrap" gap="xs">
                  <Stack gap={2}>
                    <Text fw={700}>
                      {selectedItem?.patient_name || selectedItem?.patient_phone || "Пациент"}
                    </Text>
                    {aiSummary && (
                      <Text size="xs" c="dimmed">
                        AI‑резюме: {aiSummary}
                      </Text>
                    )}
                    {(aiSummaryStatus || aiSuggestStatus) && (
                      <Text size="xs" c="dimmed">
                        {aiSummaryStatus === "fallback_local" || aiSuggestStatus === "fallback_local"
                          ? "AI‑резюме и AI‑ответ сейчас работают в локальном режиме (без внешнего провайдера)."
                          : aiSummaryStatus === "disabled" || aiSuggestStatus === "disabled"
                            ? "AI‑подсказки сейчас отключены администратором клиники."
                            : null}
                      </Text>
                    )}
                  </Stack>
                  <Group gap="xs">
                    <Button size="xs" variant="light" onClick={handleAiSummary} loading={summaryMutation.isPending}>
                      AI‑резюме
                    </Button>
                    <Button size="xs" variant="light" onClick={handleAiSuggest} loading={suggestMutation.isPending}>
                      AI‑ответ
                    </Button>
                    <Tooltip
                      label="Помечает диалог как взятый в работу. Фильтр «Мои» покажет такие диалоги."
                      multiline
                      w={260}
                    >
                      <Button size="xs" variant="light" onClick={handleAssign} loading={assignConv.isPending}>
                        Взять в работу
                      </Button>
                    </Tooltip>
                  </Group>
                </Flex>
                <ScrollArea h={280} type="scroll">
                  {msgLoading ? (
                    <DataSkeleton lines={3} />
                  ) : (
                    <Stack gap="xs" {...ADMIN_CHAT_MESSAGES_REGION}>
                      {(msgData?.items ?? []).map((m: ChatMessageDto) => {
                        const audioMinW = (m.attachments ?? []).some((a) =>
                          (a.content_type || "").toLowerCase().startsWith("audio/")
                        )
                          ? 280
                          : undefined;
                        return (
                        <Box
                          key={m.id}
                          p="xs"
                          style={{
                            alignSelf: m.is_mine ? "flex-end" : "flex-start",
                            maxWidth: "80%",
                            minWidth: audioMinW,
                            ...(m.is_mine
                              ? adminChatOutgoingBubbleStyle()
                              : adminChatIncomingBubbleStyle()),
                          }}
                        >
                          {m.message_type === "sticker" && !m.body ? (
                            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                              Стикер
                            </Text>
                          ) : shouldOmitChatBodyForAudioAttachment(m.body, m.attachments, m.message_type) ||
                            shouldOmitOmniMediaPlaceholder(m.body, m.attachments) ? null : (
                            <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                              <AppleEmojiRichText text={m.body || ""} />
                            </Text>
                          )}
                          {m.attachments && m.attachments.length > 0 ? (
                            <ClinicChatAttachments
                              attachments={m.attachments}
                              getBlob={getAttachmentBlob}
                              allowAudioAttachmentDownload={allowAudioAttachmentDownload}
                            />
                          ) : null}
                          <Group gap="xs" wrap="nowrap" justify="space-between" mt={4}>
                            <Text size="xs" c="dimmed">
                              {new Date(m.created_at).toLocaleString()}
                            </Text>
                            {m.is_mine && (
                              <Button
                                variant="subtle"
                                size="compact-xs"
                                color="red"
                                aria-label="Удалить сообщение"
                                onClick={() => handleDeleteMessage(m.id)}
                                loading={deleteMessage.isPending}
                              >
                                Удалить
                              </Button>
                            )}
                          </Group>
                        </Box>
                        );
                      })}
                    </Stack>
                  )}
                </ScrollArea>
                {pendingFile ? (
                  <Text size="xs" c="dimmed">
                    Вложение: {pendingFile.name}{" "}
                    <Text
                      component="button"
                      type="button"
                      span
                      c="red.7"
                      ml="xs"
                      style={{ cursor: "pointer", border: "none", background: "none", font: "inherit" }}
                      onClick={() => setPendingFile(null)}
                    >
                      Убрать
                    </Text>
                  </Text>
                ) : null}
                {attachError ? (
                  <Text size="xs" c="red">
                    {attachError}
                  </Text>
                ) : null}
                <Flex gap="sm" wrap="wrap" align="flex-end">
                  <VoiceNoteRecorderButton
                    disabled={sending}
                    onError={() => setAttachError("Нет доступа к микрофону")}
                    onRecorded={(file) => {
                      setAttachError(null);
                      if (file.size > MAX_CHAT_FILE_BYTES) {
                        setAttachError("Файл больше 5 МБ");
                        return;
                      }
                      setPendingFile(file);
                    }}
                  />
                  <EmojiMartPopoverPicker
                    actionIconProps={{ variant: "light", color: "indigo", size: "lg" }}
                    onPick={(native) => setMessageText((prev) => prev + native)}
                    onInserted={() => composerRef.current?.focus()}
                  />
                  <ActionIcon
                    variant="light"
                    size="lg"
                    color="gray"
                    aria-label="Документ"
                    onClick={() => triggerAttachPick("doc")}
                  >
                    <IconPaperclip size={20} />
                  </ActionIcon>
                  <ActionIcon
                    variant="light"
                    size="lg"
                    color="gray"
                    aria-label="Изображение"
                    onClick={() => triggerAttachPick("image")}
                  >
                    <IconPhoto size={20} />
                  </ActionIcon>
                  <ActionIcon
                    variant="light"
                    size="lg"
                    color="gray"
                    aria-label="Аудиофайл"
                    title="Выбрать аудио (без видео)"
                    onClick={() => triggerAttachPick("audio")}
                  >
                    <IconVolume size={20} />
                  </ActionIcon>
                  <AppleEmojiOverlayTextarea
                    ref={composerRef}
                    placeholder="Сообщение… (голос — микрофон или значок аудио)"
                    value={messageText}
                    onChange={(e) => setMessageText(e.currentTarget.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (canSend) handleSend();
                      }
                    }}
                    minRows={2}
                    style={{ flex: 1, minWidth: 180 }}
                  />
                  <Button color={SEMANTIC.action.send} onClick={handleSend} loading={sending} disabled={!canSend}>
                    Отправить
                  </Button>
                </Flex>
                <Text size="xs" c="dimmed">
                  Голос — микрофоном или файлом аудио; подпись необязательна.
                </Text>
                {aiVariants.length > 0 && (
                  <Group gap="xs" wrap="wrap">
                    {aiVariants.map((v) => (
                      <Button
                        key={v}
                        size="xs"
                        variant="subtle"
                        onClick={() => setMessageText(v)}
                      >
                        {v}
                      </Button>
                    ))}
                  </Group>
                )}
              </Stack>
            )}
          </Paper>
        </Grid.Col>
      </Grid>
    </Stack>
  );
}
