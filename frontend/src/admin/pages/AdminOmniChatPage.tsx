import { useMemo, useState } from "react";
import {
  useAdminOmniChats,
  useAdminOmniChatDetail,
  useAdminOmniChatMessages,
  useSendAdminOmniMessage,
  useUpdateOmniChatAiMode,
  useHideAdminOmniMessage,
  OMNI_CHAT_AI_MODES,
} from "@/hooks/useAdminOmniChat";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Box,
  Flex,
  Grid,
  Paper,
  ScrollArea,
  Stack,
  Text,
  TextInput,
  Button,
  Title,
  Badge,
  Select,
  Checkbox,
} from "@mantine/core";
import { GlassModal } from "@/shared/ui/GlassModal";
import { Textarea } from "@mantine/core";

export default function AdminOmniChatPage() {
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);
  const [search, setSearch] = useState("");
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null);
  const [messageText, setMessageText] = useState("");
  const [showOnlyWaiting, setShowOnlyWaiting] = useState(false);
  const [showHiddenMessages, setShowHiddenMessages] = useState(false);
  const [aiFilter, setAiFilter] = useState<string>("ALL");
  const [hideModalOpen, setHideModalOpen] = useState(false);
  const [hideMessageId, setHideMessageId] = useState<string | null>(null);
  const [hideReason, setHideReason] = useState("");

  const { data: chatsData, isLoading: chatsLoading, isError: chatsError, error: chatsErr } = useAdminOmniChats({
    status: showOnlyWaiting ? "WAITING_FOR_OPERATOR" : statusFilter,
    search: search || undefined,
    page: 1,
    page_size: 100,
  });

  const { data: chatDetail, isLoading: detailLoading } = useAdminOmniChatDetail(selectedChatId);
  const { data: messagesData, isLoading: messagesLoading } = useAdminOmniChatMessages(
    selectedChatId,
    {
      limit: 100,
      include_hidden: showHiddenMessages,
    }
  );

  const sendMessage = useSendAdminOmniMessage();
  const updateAiMode = useUpdateOmniChatAiMode();
  const hideMessage = useHideAdminOmniMessage();

  const handleSend = () => {
    if (!selectedChatId || !messageText.trim()) return;
    sendMessage.mutate(
      { chatId: selectedChatId, content: messageText.trim() },
      { onSuccess: () => setMessageText("") }
    );
  };

  const selectedItem = chatsData?.items?.find((c) => c.chat_id === selectedChatId) ?? null;

  const visibleChats = useMemo(() => {
    let items = chatsData?.items ?? [];
    if (aiFilter === "AI_ONLY") {
      items = items.filter(
        (c) => c.ai_mode && c.ai_mode !== "DISABLED"
      );
    }
    return items;
  }, [aiFilter, chatsData?.items]);

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

  if (chatsLoading) {
    return (
      <Stack>
        <Title order={3}>Единый чат</Title>
        <DataSkeleton lines={5} />
      </Stack>
    );
  }
  if (chatsError) {
    return (
      <Stack>
        <Title order={3}>Единый чат</Title>
        <Text c="red">{chatsErr instanceof Error ? chatsErr.message : "Ошибка загрузки"}</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Title order={3}>Единый чат</Title>
      <Flex gap="sm" wrap="wrap">
        <TextInput
          placeholder="Поиск по контакту"
          value={search}
          onChange={(e) => setSearch(e.currentTarget.value)}
          style={{ flex: 1, minWidth: 200 }}
        />
        <Select
          placeholder="Фильтр по статусу"
          value={statusFilter}
          onChange={(value) => {
            setStatusFilter(value || undefined);
            setShowOnlyWaiting(false);
          }}
          data={[
            { value: undefined, label: "Все" },
            { value: "OPEN", label: "Открыт" },
            { value: "WAITING_FOR_OPERATOR", label: "Ждёт оператора" },
            { value: "IN_PROGRESS", label: "В работе" },
            { value: "CLOSED", label: "Закрыт" },
          ].map((option) => ({
            value: option.value ?? "",
            label: option.label,
          }))}
          allowDeselect
          style={{ width: 220 }}
        />
        <Select
          placeholder="AI-режим"
          value={aiFilter}
          onChange={(value) => setAiFilter(value || "ALL")}
          data={[
            { value: "ALL", label: "Все режимы" },
            { value: "AI_ONLY", label: "Только AI (автоответ/подсказки)" },
          ]}
          style={{ width: 220 }}
        />
        <Button
          variant={showOnlyWaiting ? "filled" : "light"}
          size="xs"
          onClick={() => {
            setShowOnlyWaiting((prev) => !prev);
            if (!showOnlyWaiting) {
              setStatusFilter(undefined);
            }
          }}
        >
          Только «ждёт оператора»
        </Button>
      </Flex>

      <Grid gutter="md">
        <Grid.Col span={{ base: 12, md: 4 }}>
          <Paper p="sm" radius="md" withBorder style={{ maxHeight: 420 }}>
            <ScrollArea h={380} type="scroll">
              {!chatsData?.items?.length ? (
                <EmptyStateHint
                  title="Нет диалогов"
                  subtitle="Сообщения появятся из Telegram, веб-чата и других каналов."
                />
              ) : (
                <Stack gap="xs">
                  {visibleChats.map((c) => (
                    <Box
                      key={c.chat_id}
                      p="xs"
                      style={{
                        cursor: "pointer",
                        borderRadius: 8,
                        backgroundColor:
                          selectedChatId === c.chat_id
                            ? "var(--primary-light, rgba(59,130,246,0.12))"
                            : undefined,
                      }}
                      onClick={() => setSelectedChatId(c.chat_id)}
                    >
                      <Text fw={700} size="sm" truncate>
                        {c.contact_name || c.contact_primary_phone || "Без имени"}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {c.contact_primary_phone || "—"}
                      </Text>
                      <Flex gap="xs" align="center" wrap="wrap">
                        <Badge size="xs" variant="light">
                          {c.status}
                        </Badge>
                        {c.last_actor_type && (
                          <Text size="xs" c="dimmed">
                            {c.last_actor_type}
                          </Text>
                        )}
                        {c.ai_mode && (
                          <Badge size="xs" variant="outline" color="blue">
                            {c.ai_mode === "DISABLED"
                              ? "AI выкл."
                              : c.ai_mode === "AUTO_REPLY"
                                ? "AI автоответ"
                                : "AI подсказки"}
                          </Badge>
                        )}
                      </Flex>
                    </Box>
                  ))}
                </Stack>
              )}
            </ScrollArea>
          </Paper>
        </Grid.Col>
        <Grid.Col span={{ base: 12, md: 8 }}>
          <Paper p="md" radius="md" withBorder style={{ minHeight: 420 }}>
            {!selectedChatId ? (
              <EmptyStateHint title="Выберите диалог" subtitle="Клик по строке слева." />
            ) : (
              <Stack gap="md" style={{ height: "100%" }}>
                {(detailLoading || chatDetail) && (
                  <Flex justify="space-between" align="center" wrap="wrap" gap="xs">
                    <Stack gap={2}>
                      <Text fw={700}>
                        {chatDetail?.contact_name ||
                          chatDetail?.contact_primary_phone ||
                          selectedItem?.contact_name ||
                          selectedItem?.contact_primary_phone ||
                          "Контакт"}
                      </Text>
                      {chatDetail && (
                        <Flex gap="xs" align="center" wrap="wrap">
                          <Badge size="sm">{chatDetail.status}</Badge>
                          {chatDetail.channel_type && (
                            <Text size="xs" c="dimmed">
                              {chatDetail.channel_type}
                            </Text>
                          )}
                          <Select
                            size="xs"
                            style={{ width: 160 }}
                            label="Режим AI в этом чате"
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
                          />
                        </Flex>
                      )}
                    </Stack>
                  </Flex>
                )}
                <ScrollArea h={280} type="scroll">
                  {messagesLoading ? (
                    <DataSkeleton lines={3} />
                  ) : (
                    <Stack gap="xs">
                      {(messagesData?.items ?? []).map((m) => (
                        <Box
                          key={m.id}
                          p="xs"
                          style={{
                            alignSelf:
                              m.direction === "OUTBOUND" && m.actor_type !== "CLIENT"
                                ? "flex-end"
                                : "flex-start",
                            maxWidth: "80%",
                            borderRadius: 8,
                            backgroundColor: m.ui_hidden
                              ? "rgba(148,163,184,0.18)"
                              : m.direction === "OUTBOUND"
                                ? "var(--primary-light, rgba(59,130,246,0.12))"
                                : "var(--bg-main)",
                            opacity: m.ui_hidden ? 0.8 : 1,
                          }}
                        >
                          <Text size="xs" c="dimmed">
                            {m.actor_type}
                            {m.channel_type
                              ? ` • ${m.channel_type}`
                              : chatDetail?.channel_type
                                ? ` • ${chatDetail.channel_type}`
                                : ""}
                          </Text>
                          {m.ui_hidden ? (
                            <Text size="xs" c="dimmed">
                              Сообщение скрыто: {m.hidden_reason || "без указания причины"}
                            </Text>
                          ) : (
                            <Stack gap={4}>
                              <Text size="sm">{m.content}</Text>
                              <Button
                                size="xs"
                                variant="subtle"
                                color="red"
                                onClick={() => handleOpenHideModal(m.id)}
                              >
                                Скрыть сообщение
                              </Button>
                            </Stack>
                          )}
                          <Text size="xs" c="dimmed">
                            {m.created_at ? new Date(m.created_at).toLocaleString() : ""}
                          </Text>
                        </Box>
                      ))}
                    </Stack>
                  )}
                </ScrollArea>
                <Flex gap="sm" wrap="wrap" align="center">
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
                  <Checkbox
                    label="Показывать скрытые сообщения"
                    checked={showHiddenMessages}
                    onChange={(e) => setShowHiddenMessages(e.currentTarget.checked)}
                  />
                </Flex>
              </Stack>
            )}
          </Paper>
        </Grid.Col>
      </Grid>

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
              variant="default"
              size="sm"
              onClick={() => setHideModalOpen(false)}
              disabled={hideMessage.isPending}
            >
              Отмена
            </Button>
            <Button
              size="sm"
              color="red"
              onClick={handleConfirmHide}
              loading={hideMessage.isPending}
            >
              Скрыть
            </Button>
          </Flex>
        </Stack>
      </GlassModal>
    </Stack>
  );
}
