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
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Box,
  Button,
  Group,
  Image,
  Modal,
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
        <Text c="red">{convErr instanceof Error ? convErr.message : "Ошибка загрузки"}</Text>
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
    <Stack gap="md">
      <Group justify="space-between" wrap="wrap">
        <Title order={3}>Чат с клиникой</Title>
        <Group gap="xs">
          <Button
            variant="subtle"
            size="xs"
            color="gray"
            leftSection={<IconRefresh size={14} />}
            onClick={refreshChat}
            loading={msgLoading}
            aria-label="Обновить"
          >
            Обновить
          </Button>
          {items.some((m) => m.is_mine) && (
            <Button
              variant="subtle"
              size="xs"
              color="gray"
              onClick={() => setClearModalOpen(true)}
            >
              Очистить мои сообщения
            </Button>
          )}
        </Group>
      </Group>
      <Text size="xs" c="dimmed">
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
            <Button variant="default" onClick={() => setClearModalOpen(false)}>
              Отмена
            </Button>
            <Button color="red" onClick={handleClearMyMessages} loading={deleteMessage.isPending}>
              Удалить мои сообщения
            </Button>
          </Group>
        </Stack>
      </Modal>
      <ScrollArea h={360} type="scroll">
        {msgLoading ? (
          <DataSkeleton lines={3} />
        ) : items.length === 0 ? (
          <EmptyStateHint title="Пока нет сообщений" subtitle="Напишите первым — администратор ответит." />
        ) : (
          <Stack gap="xs">
            {items.map((m) => (
              <Box
                key={m.id}
                p="xs"
                style={{
                  alignSelf: m.is_mine ? "flex-end" : "flex-start",
                  maxWidth: "85%",
                  borderRadius: 8,
                  backgroundColor: m.is_mine
                    ? "var(--primary-light, rgba(59,130,246,0.12))"
                    : "var(--bg-main)",
                }}
              >
                {m.message_type === "sticker" && m.sticker_key && stickerKeyToUrl[m.sticker_key] ? (
                  <Image src={stickerKeyToUrl[m.sticker_key]} alt="" w={64} h={64} fit="contain" />
                ) : (
                  <Text size="sm">{m.body}</Text>
                )}
                <Group gap="xs" wrap="nowrap" justify="space-between">
                  <Text size="xs" c="dimmed">
                    {new Date(m.created_at).toLocaleString()}
                  </Text>
                  {m.is_mine && (
                    <Button
                      variant="subtle"
                      size="compact-xs"
                      color="red"
                      onClick={() => handleDelete(m.id)}
                      loading={deleteMessage.isPending}
                    >
                      Удалить
                    </Button>
                  )}
                </Group>
              </Box>
            ))}
            <div ref={scrollBottomRef} />
          </Stack>
        )}
      </ScrollArea>
      <Stack gap="xs">
        <TextInput
          placeholder="Сообщение..."
          value={messageText}
          onChange={(e) => setMessageText(e.currentTarget.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <Group gap="xs">
          <Button onClick={handleSend} loading={sendMessage.isPending}>
            Отправить
          </Button>
          {defaultStickers.length > 0 && (
            <Popover width={220} position="top-start" shadow="md">
              <Popover.Target>
                <Button variant="light">Стикер</Button>
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
