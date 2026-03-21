import { useState, useEffect } from "react";
import {
  useAdminChatConversations,
  useAdminChatMessages,
  useSendAdminMessage,
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
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { QueryErrorAlert } from "@/shared/ui";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
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
  Title,
  Tooltip,
} from "@mantine/core";
import type { ChatMessageDto } from "@/api/types";

export default function AdminChatPage() {
  const [filter, setFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [messageText, setMessageText] = useState("");
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiSummaryStatus, setAiSummaryStatus] = useState<string | null>(null);
  const [aiVariants, setAiVariants] = useState<string[]>([]);
  const [aiSuggestStatus, setAiSuggestStatus] = useState<string | null>(null);
  const [aiError, setAiError] = useState<string | null>(null);

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

  const handleSend = () => {
    if (!selectedId || !messageText.trim()) return;
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

  if (convLoading) {
    return (
      <Stack>
        <Title order={3}>Чат</Title>
        <DataSkeleton lines={5} />
      </Stack>
    );
  }
  if (convError) {
    return (
      <Stack>
        <Title order={3}>Чат</Title>
        <QueryErrorAlert error={convErr} title="Не удалось загрузить диалоги" />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Title order={3}>Чат</Title>
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
      <Flex gap="sm" wrap="wrap">
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

      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Paper p="sm" radius="md" withBorder style={{ maxHeight: 420 }}>
            <ScrollArea h={380} type="scroll">
              {!convData?.items?.length ? (
                <EmptyStateHint title="Нет диалогов" subtitle="Сообщения появятся, когда пациенты напишут." />
              ) : (
                <Stack gap="xs">
                  {convData.items.map((c) => (
                    <Box
                      key={c.conversation_id}
                      p="xs"
                      style={{
                        cursor: "pointer",
                        borderRadius: 8,
                        backgroundColor: selectedId === c.conversation_id ? "var(--primary-light, rgba(59,130,246,0.12))" : undefined,
                      }}
                      onClick={() => setSelectedId(c.conversation_id)}
                    >
                      <Text fw={700} size="sm" truncate>
                        {c.patient_name || "Без имени"}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {c.patient_phone}
                      </Text>
                      {c.unread_by_admin_count > 0 && (
                        <Text size="xs" c="red">
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
                    <Stack gap="xs">
                      {(msgData?.items ?? []).map((m: ChatMessageDto) => (
                        <Box
                          key={m.id}
                          p="xs"
                          style={{
                            alignSelf: m.is_mine ? "flex-end" : "flex-start",
                            maxWidth: "80%",
                            borderRadius: 8,
                            backgroundColor: m.is_mine
                              ? "var(--primary-light, rgba(59,130,246,0.12))"
                              : "var(--bg-main)",
                          }}
                        >
                          <Text size="sm">
                            {m.message_type === "sticker" && !m.body ? "Стикер" : m.body}
                          </Text>
                          <Group gap="xs" wrap="nowrap" justify="space-between">
                            <Text size="xs" c="dimmed">
                              {new Date(m.created_at).toLocaleString()}
                            </Text>
                            {m.is_mine && (
                              <Button
                                variant="subtle"
                                size="compact-xs"
                                color="red"
                                onClick={() => handleDeleteMessage(m.id)}
                                loading={deleteMessage.isPending}
                              >
                                Удалить
                              </Button>
                            )}
                          </Group>
                        </Box>
                      ))}
                    </Stack>
                  )}
                </ScrollArea>
                <Flex gap="sm" wrap="wrap">
                  <TextInput
                    placeholder="Сообщение..."
                    value={messageText}
                    onChange={(e) => setMessageText(e.currentTarget.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    style={{ flex: 1, minWidth: 180 }}
                  />
                  <Button onClick={handleSend} loading={sendMessage.isPending}>
                    Отправить
                  </Button>
                </Flex>
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
