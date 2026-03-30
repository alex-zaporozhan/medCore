import { useCallback, useEffect, useRef, useState } from "react";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import {
  usePatientConversation,
  usePatientChatMessages,
  useSendPatientMessage,
  useSendPatientMessageWithFile,
  usePatientMarkRead,
  useDeletePatientMessage,
} from "@/hooks/usePatientChat";
import { useQueryClient } from "@tanstack/react-query";
import { useStickerSets } from "@/hooks/useStickers";
import { authApi } from "@/api/client";
import { DataSkeleton, QueryErrorAlert } from "@/shared/ui";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { SEMANTIC } from "@/shared/semanticUi";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { ClinicChatAttachments } from "@/shared/ClinicChatAttachments";
import {
  shouldOmitChatBodyForAudioAttachment,
  shouldOmitOmniMediaPlaceholder,
} from "@/shared/chatMessageBodyDisplay";
import { EmojiMartPopoverPicker } from "@/shared/ui/EmojiMartPopoverPicker";
import { AppleEmojiOverlayTextarea } from "@/shared/ui/AppleEmojiOverlayTextarea";
import { VoiceNoteRecorderButton } from "@/shared/ui/VoiceNoteRecorderButton";
import {
  ActionIcon,
  Box,
  Button,
  Group,
  Image,
  Modal,
  Paper,
  Popover,
  ScrollArea,
  SimpleGrid,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { IconPaperclip, IconPhoto, IconRefresh, IconVolume } from "@tabler/icons-react";

const MAX_CHAT_FILE_BYTES = 5 * 1024 * 1024;

const PATIENT_CHAT_DOC_ACCEPT =
  ".pdf,.doc,.docx,.txt,.xlsx,.xls,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain";

export default function ChatPage() {
  const { accessToken, patientId } = usePatientAuth();
  const [messageText, setMessageText] = useState("");
  const [pendingFile, setPendingFile] = useState<File | null>(null);
  const [attachError, setAttachError] = useState<string | null>(null);
  const { stickerKeyToUrl, defaultStickers } = useStickerSets(true);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const triggerAttachPick = useCallback((mode: "doc" | "image" | "audio") => {
    const el = fileInputRef.current;
    if (!el) return;
    if (mode === "doc") el.accept = PATIENT_CHAT_DOC_ACCEPT;
    else if (mode === "image") el.accept = "image/*";
    else el.accept = "audio/*";
    el.value = "";
    el.click();
  }, []);

  const { data: convData, isLoading: convLoading, isError: convError, error: convErr } = usePatientConversation(
    patientId,
    accessToken
  );

  const { data: msgData, isLoading: msgLoading } = usePatientChatMessages(
    patientId,
    null,
    100,
    accessToken
  );

  const queryClient = useQueryClient();
  const sendMessage = useSendPatientMessage(accessToken);
  const sendWithFile = useSendPatientMessageWithFile(accessToken);
  const markRead = usePatientMarkRead(accessToken);
  const deleteMessage = useDeletePatientMessage(accessToken);
  const [clearModalOpen, setClearModalOpen] = useState(false);
  const scrollBottomRef = useRef<HTMLDivElement>(null);

  const getAttachmentBlob = useCallback(
    (attachmentId: string) => {
      if (!accessToken) return Promise.reject(new Error("no token"));
      return authApi(accessToken).getBlob(`/v1/patient/chat/attachments/${attachmentId}/file`);
    },
    [accessToken]
  );

  useEffect(() => {
    scrollBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgData?.items?.length]);

  useEffect(() => {
    if (patientId && convData) {
      markRead.mutate({ patientId });
    }
  }, [patientId, convData?.conversation_id]);

  const scrollToBottom = () => scrollBottomRef.current?.scrollIntoView({ behavior: "smooth" });

  const handleSend = () => {
    if (!patientId) return;
    setAttachError(null);
    if (pendingFile) {
      if (pendingFile.size > MAX_CHAT_FILE_BYTES) {
        setAttachError("Файл больше 5 МБ");
        return;
      }
      const body = messageText.trim() || (pendingFile.type.startsWith("audio/") ? "" : "");
      sendWithFile.mutate(
        { patientId, body, file: pendingFile },
        {
          onSuccess: () => {
            setMessageText("");
            setPendingFile(null);
            scrollToBottom();
          },
          onError: () => setAttachError("Не удалось отправить файл"),
        }
      );
      return;
    }
    if (!messageText.trim()) return;
    sendMessage.mutate(
      { patientId, body: messageText.trim() },
      { onSuccess: () => { setMessageText(""); scrollToBottom(); } }
    );
  };

  const handleSendSticker = (stickerKey: string) => {
    if (!patientId) return;
    sendMessage.mutate(
      { patientId, message_type: "sticker", sticker_key: stickerKey },
      { onSuccess: () => scrollToBottom() }
    );
  };

  const handleDelete = (messageId: string) => {
    if (!patientId) return;
    deleteMessage.mutate({ patientId, messageId });
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

  if (!accessToken || !patientId) {
    return (
      <Stack>
        <Title order={3}>Чат с клиникой</Title>
        <Text c="dimmed">Войдите в аккаунт, чтобы писать в чат.</Text>
      </Stack>
    );
  }

  if (convLoading) {
    return (
      <Stack>
        <Title order={3}>Чат с клиникой</Title>
        <DataSkeleton lines={5} />
      </Stack>
    );
  }
  if (convError) {
    return (
      <Stack>
        <Title order={3}>Чат с клиникой</Title>
        <QueryErrorAlert error={convErr} title="Не удалось загрузить чат" />
      </Stack>
    );
  }

  const items = msgData?.items ?? [];
  const myMessageIds = items.filter((m) => m.is_mine).map((m) => m.id);
  const handleClearMyMessages = async () => {
    if (!patientId || myMessageIds.length === 0) {
      setClearModalOpen(false);
      return;
    }
    try {
      for (const id of myMessageIds) {
        await deleteMessage.mutateAsync({ patientId, messageId: id });
      }
    } finally {
      queryClient.invalidateQueries({ queryKey: ["patient-chat-messages", patientId] });
      setClearModalOpen(false);
    }
  };

  const refreshChat = () => {
    queryClient.invalidateQueries({ queryKey: ["patient-chat-messages", patientId] });
    queryClient.invalidateQueries({ queryKey: ["patient-chat-conversation", patientId] });
  };

  const sending = sendMessage.isPending || sendWithFile.isPending;
  const canSendText = Boolean(messageText.trim());
  const canSend = pendingFile ? true : canSendText;

  return (
    <Stack gap="md" maw={720} w="100%" mx="auto">
      <input ref={fileInputRef} type="file" style={{ display: "none" }} onChange={onPickFile} />
      <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
        <Title order={3} c="gray.9">
          Чат с клиникой
        </Title>
        <Group gap={4} wrap="nowrap">
          <ActionIcon
            variant="subtle"
            color="gray"
            size="sm"
            onClick={refreshChat}
            loading={msgLoading}
            aria-label="Обновить"
          >
            <IconRefresh size={16} />
          </ActionIcon>
          {items.some((m) => m.is_mine) && (
            <Text
              component="button"
              type="button"
              size="xs"
              c="dimmed"
              style={{
                cursor: "pointer",
                border: "none",
                background: "none",
                padding: "var(--space-xs) var(--space-sm)",
                opacity: 0.65,
                font: "inherit",
                whiteSpace: "nowrap",
              }}
              onClick={() => setClearModalOpen(true)}
            >
              Очистить мои
            </Text>
          )}
        </Group>
      </Group>
      <Text size="sm" c="dimmed" lh={1.4} maw={720}>
        Переписка с администрацией клиники (без сторонних мессенджеров). Удалённое у вас сообщение у администратора
        остаётся в истории. До 5 МБ: документы, фото,{" "}
        <strong>аудио</strong> — кнопка микрофона или файл; видео-кружки не используются.
      </Text>
      <Modal
        opened={clearModalOpen}
        onClose={() => setClearModalOpen(false)}
        title="Очистить мои сообщения"
      >
        <Stack>
          <Text size="sm">
            Удалить все ваши сообщения из этого чата? У администратора история переписки сохранится.
          </Text>
          <Group justify="flex-end">
            <Button variant="subtle" color={SEMANTIC.action.dismiss} onClick={() => setClearModalOpen(false)}>
              Отмена
            </Button>
            <Button color={SEMANTIC.action.danger} onClick={handleClearMyMessages} loading={deleteMessage.isPending}>
              Удалить мои сообщения
            </Button>
          </Group>
        </Stack>
      </Modal>
      <Paper
        radius="md"
        withBorder
        p="sm"
        style={{ borderColor: "var(--divider)", boxShadow: "var(--shadow-soft-sm)" }}
      >
        <ScrollArea h={360} type="scroll">
          {msgLoading ? (
            <DataSkeleton lines={3} />
          ) : items.length === 0 ? (
            <EmptyStateHint
              title="Пока нет сообщений"
              subtitle="Напишите или отправьте голосовое (микрофон) — администратор ответит. Можно прикрепить фото или документ."
            />
          ) : (
            <Stack gap="sm">
              {items.map((m) => (
                <Box
                  key={m.id}
                  style={{
                    alignSelf: m.is_mine ? "flex-end" : "flex-start",
                    maxWidth: "min(85%, 420px)",
                    minWidth:
                      (m.attachments?.length ?? 0) > 0 &&
                      m.attachments?.some((x) => x.content_type.startsWith("audio/"))
                        ? 280
                        : undefined,
                  }}
                >
                  <Paper
                    radius="md"
                    p="sm"
                    withBorder
                    style={{
                      borderColor: "var(--divider)",
                      boxShadow: "var(--shadow-soft-sm)",
                      backgroundColor: m.is_mine
                        ? "var(--bg-card-soft)"
                        : "var(--bg-card)",
                      borderLeftWidth: 3,
                      borderLeftStyle: "solid",
                      borderLeftColor: m.is_mine
                        ? "var(--mantine-color-dark-4)"
                        : "var(--mantine-color-gray-4)",
                      minWidth:
                        (m.attachments?.length ?? 0) > 0 &&
                        m.attachments?.some((x) => x.content_type.startsWith("audio/"))
                          ? 260
                          : undefined,
                    }}
                  >
                    {m.message_type === "sticker" && m.sticker_key && stickerKeyToUrl[m.sticker_key] ? (
                      <Image src={stickerKeyToUrl[m.sticker_key]} alt="" w={64} h={64} fit="contain" />
                    ) : shouldOmitChatBodyForAudioAttachment(m.body, m.attachments, m.message_type) ||
                      shouldOmitOmniMediaPlaceholder(m.body, m.attachments) ? null : (
                      <Text size="sm" c="gray.9" style={{ whiteSpace: "pre-wrap" }}>
                        <AppleEmojiRichText text={m.body || ""} />
                      </Text>
                    )}
                    {m.attachments && m.attachments.length > 0 ? (
                      <ClinicChatAttachments attachments={m.attachments} getBlob={getAttachmentBlob} />
                    ) : null}
                    <Group gap="xs" wrap="nowrap" justify="space-between" mt={6}>
                      <Text size="xs" c="dimmed">
                        {new Date(m.created_at).toLocaleString()}
                      </Text>
                      {m.is_mine && (
                        <Text
                          component="button"
                          type="button"
                          size="xs"
                          c="red.7"
                          style={{
                            cursor: "pointer",
                            border: "none",
                            background: "none",
                            padding: 0,
                            opacity: 0.85,
                            font: "inherit",
                          }}
                          onClick={() => handleDelete(m.id)}
                          disabled={deleteMessage.isPending}
                        >
                          Удалить
                        </Text>
                      )}
                    </Group>
                  </Paper>
                </Box>
              ))}
              <div ref={scrollBottomRef} />
            </Stack>
          )}
        </ScrollArea>
      </Paper>
      <Stack gap="xs">
        {pendingFile ? (
          <Text size="xs" c="dimmed">
            К сообщению: {pendingFile.name}{" "}
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
        <AppleEmojiOverlayTextarea
          ref={composerRef}
          placeholder="Сообщение… (Shift+Enter — новая строка, Enter — отправить)"
          value={messageText}
          minRows={2}
          onChange={(e) => setMessageText(e.currentTarget.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (canSend) handleSend();
            }
          }}
        />
        <Group gap="xs" align="center" wrap="wrap">
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
            actionIconProps={{ variant: "light", color: "gray", size: "lg" }}
            onPick={(native) => setMessageText((prev) => prev + native)}
            onInserted={() => composerRef.current?.focus()}
          />
          <ActionIcon
            variant="light"
            size="lg"
            color="gray"
            aria-label="Прикрепить документ"
            onClick={() => triggerAttachPick("doc")}
          >
            <IconPaperclip size={20} />
          </ActionIcon>
          <ActionIcon
            variant="light"
            size="lg"
            color="gray"
            aria-label="Прикрепить изображение"
            onClick={() => triggerAttachPick("image")}
          >
            <IconPhoto size={20} />
          </ActionIcon>
          <ActionIcon
            variant="light"
            size="lg"
            color="gray"
            aria-label="Прикрепить аудиофайл"
            title="Выбрать аудио (без видео)"
            onClick={() => triggerAttachPick("audio")}
          >
            <IconVolume size={20} />
          </ActionIcon>
          <Button color={SEMANTIC.action.send} onClick={handleSend} loading={sending} disabled={!canSend}>
            Отправить
          </Button>
          {defaultStickers.length > 0 && (
            <Popover width={220} position="top-start" shadow="md">
              <Popover.Target>
                <Button variant="light" color={SEMANTIC.action.send}>
                  Стикер
                </Button>
              </Popover.Target>
              <Popover.Dropdown>
                <SimpleGrid cols={3} spacing="xs">
                  {defaultStickers.map((s) => (
                    <Box
                      key={s.key}
                      style={{ cursor: "pointer" }}
                      onClick={() => handleSendSticker(s.key)}
                    >
                      <Image src={s.url} alt="" w={48} h={48} fit="contain" />
                    </Box>
                  ))}
                </SimpleGrid>
              </Popover.Dropdown>
            </Popover>
          )}
        </Group>
        <Text size="xs" c="dimmed">
          Голос — микрофоном или файлом аудио; подпись к вложению необязательна.
        </Text>
      </Stack>
    </Stack>
  );
}
