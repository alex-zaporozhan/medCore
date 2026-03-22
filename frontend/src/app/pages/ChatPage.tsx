import { useEffect, useRef, useState } from "react";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import {
  usePatientConversation,
  usePatientChatMessages,
  useSendPatientMessage,
  usePatientMarkRead,
  useDeletePatientMessage,
} from "@/hooks/usePatientChat";
import { useQueryClient } from "@tanstack/react-query";
import { useStickerSets } from "@/hooks/useStickers";
import { DataSkeleton, QueryErrorAlert } from "@/shared/ui";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { SEMANTIC } from "@/shared/semanticUi";
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
  TextInput,
  Title,
} from "@mantine/core";
import { IconRefresh } from "@tabler/icons-react";

export default function ChatPage() {
  const { accessToken, patientId } = usePatientAuth();
  const [messageText, setMessageText] = useState("");
  const { stickerKeyToUrl, defaultStickers } = useStickerSets(true);

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
  const markRead = usePatientMarkRead(accessToken);
  const deleteMessage = useDeletePatientMessage(accessToken);
  const [clearModalOpen, setClearModalOpen] = useState(false);
  const scrollBottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgData?.items?.length]);

  useEffect(() => {
    if (patientId && convData) {
      markRead.mutate({ patientId });
    }
  }, [patientId, convData?.conversation_id]);

  const handleSend = () => {
    if (!patientId) return;
    if (!messageText.trim()) return;
    sendMessage.mutate(
      { patientId, body: messageText.trim() },
      { onSuccess: () => { setMessageText(""); scrollBottomRef.current?.scrollIntoView({ behavior: "smooth" }); } }
    );
  };
  const handleSendSticker = (stickerKey: string) => {
    if (!patientId) return;
    sendMessage.mutate(
      { patientId, message_type: "sticker", sticker_key: stickerKey },
      { onSuccess: () => scrollBottomRef.current?.scrollIntoView({ behavior: "smooth" }) }
    );
  };
  const handleDelete = (messageId: string) => {
    if (!patientId) return;
    deleteMessage.mutate({ patientId, messageId });
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

  return (
    <Stack gap="md" maw={720} w="100%" mx="auto">
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
                padding: "4px 6px",
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
      <Text size="xs" c="dimmed" lh={1.35} maw={560}>
        Удалённое сообщение исчезнет только у вас; у администратора история сохраняется.
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
        style={{ borderColor: "var(--mantine-color-gray-3)", boxShadow: "var(--mantine-shadow-xs)" }}
      >
        <ScrollArea h={360} type="scroll">
          {msgLoading ? (
            <DataSkeleton lines={3} />
          ) : items.length === 0 ? (
            <EmptyStateHint title="Пока нет сообщений" subtitle="Напишите первым — администратор ответит." />
          ) : (
            <Stack gap="sm">
              {items.map((m) => (
                <Box
                  key={m.id}
                  style={{
                    alignSelf: m.is_mine ? "flex-end" : "flex-start",
                    maxWidth: "min(85%, 420px)",
                  }}
                >
                  <Paper
                    radius="md"
                    p="sm"
                    withBorder
                    style={{
                      borderColor: "var(--mantine-color-gray-3)",
                      boxShadow: "var(--mantine-shadow-xs)",
                      backgroundColor: m.is_mine
                        ? "var(--mantine-color-gray-0)"
                        : "var(--mantine-color-white)",
                      borderLeftWidth: 3,
                      borderLeftStyle: "solid",
                      borderLeftColor: m.is_mine
                        ? "var(--mantine-color-dark-4)"
                        : "var(--mantine-color-gray-4)",
                    }}
                  >
                    {m.message_type === "sticker" && m.sticker_key && stickerKeyToUrl[m.sticker_key] ? (
                      <Image src={stickerKeyToUrl[m.sticker_key]} alt="" w={64} h={64} fit="contain" />
                    ) : (
                      <Text size="sm" c="gray.9">
                        {m.body}
                      </Text>
                    )}
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
        <TextInput
          placeholder="Сообщение..."
          value={messageText}
          onChange={(e) => setMessageText(e.currentTarget.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <Group gap="xs">
          <Button color={SEMANTIC.action.send} onClick={handleSend} loading={sendMessage.isPending}>
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
      </Stack>
    </Stack>
  );
}
