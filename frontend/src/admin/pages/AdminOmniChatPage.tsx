import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  useAdminOmniChats,
  useAdminOmniChatDetail,
  useAdminOmniChatMessages,
  useSendAdminOmniMessage,
  useUpdateOmniChatAiMode,
  useHideAdminOmniMessage,
  OMNI_CHAT_AI_MODES,
} from "@/hooks/useAdminOmniChat";
import { useAdminLoyaltySummaryByContact, useAdminFormSubmissions } from "@/hooks";
import { Link } from "react-router-dom";
import { DataSkeleton, AppCard, SectionHeader } from "@/shared/ui";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Box,
  Flex,
  Stack,
  Text,
  TextInput,
  Button,
  Badge,
  Select,
  Checkbox,
  Tabs,
} from "@mantine/core";
import { GlassModal } from "@/shared/ui/GlassModal";
import { Textarea } from "@mantine/core";
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";
import { api } from "@/api/client";

interface AdminTask {
  id: string;
  title: string;
  status: string;
  priority: string;
  due_at: string | null;
}

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
  const contactId = selectedItem?.contact_id ?? chatDetail?.contact_id ?? null;
  const { data: loyaltySummary } = useAdminLoyaltySummaryByContact(contactId);
  const patientId = loyaltySummary?.patient_id ?? null;
  const { data: formSubmissions } = useAdminFormSubmissions({
    patient_id: patientId ?? undefined,
  });

  const { data: openTasks } = useQuery({
    queryKey: ["admin-omni-tasks-open"],
    queryFn: () => api.get<AdminTask[]>("/v1/admin/tasks?status=open"),
  });
  const openTasksCount = openTasks?.length ?? 0;

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

  return (
    <Stack gap="md">
      <SectionHeader
        overline="Chat & AI"
        title="Единый чат с пациентами"
        description="Все диалоги из Telegram, WhatsApp, сайта и AI‑агента в одном окне."
      />
      <AppCard>
        <Stack gap="md" style={{ height: 520 }}>
          <Flex gap="sm" wrap="wrap">
            <TextInput
              placeholder="Поиск по контакту"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              style={{ flex: 1, minWidth: 200 }}
            />
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

          {chatsLoading ? (
            <DataSkeleton lines={6} />
          ) : chatsError ? (
            <Text c="red">
              {chatsErr instanceof Error ? chatsErr.message : "Ошибка загрузки диалогов"}
            </Text>
          ) : (
            <ThreeColumnLayout
              preset="wide-center"
              left={
                <Stack gap={4} p="xs">
                  {!chatsData?.items?.length ? (
                    <EmptyStateHint
                      title="Нет диалогов"
                      subtitle="Сообщения появятся из Telegram, веб‑чата и других каналов."
                    />
                  ) : (
                    visibleChats.map((c) => (
                      <Box
                        key={c.chat_id}
                        p={6}
                        style={{
                          cursor: "pointer",
                          borderRadius: 6,
                          backgroundColor:
                            selectedChatId === c.chat_id
                              ? "var(--primary-light, rgba(59, 130, 246, 0.12))"
                              : "transparent",
                          border:
                            selectedChatId === c.chat_id
                              ? "1px solid var(--primary)"
                              : "1px solid transparent",
                        }}
                        onClick={() => setSelectedChatId(c.chat_id)}
                      >
                        <Text fw={600} size="sm" truncate>
                          {c.contact_name || c.contact_primary_phone || "Без имени"}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {c.contact_primary_phone || "—"}
                        </Text>
                        <Flex gap={4} align="center" wrap="wrap" mt={4}>
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
                    ))
                  )}
                </Stack>
              }
              center={
                !selectedChatId ? (
                  <Stack h="100%" align="center" justify="center">
                    <EmptyStateHint
                      title="Выберите диалог"
                      subtitle="Клик по строке слева, чтобы открыть переписку."
                    />
                  </Stack>
                ) : (
                  <Stack gap="md" p="xs" style={{ height: "100%" }}>
                    {(detailLoading || chatDetail) && (
                      <Stack gap="xs">
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
                          <Stack gap={6} align="flex-end">
                            {chatDetail?.lead_id && (
                              <Stack gap={4} align="flex-end">
                                <Text size="xs" c="dimmed">
                                  CRM‑лид:
                                </Text>
                                <Flex gap="xs" align="center" wrap="wrap" justify="flex-end">
                                  {chatDetail.lead_stage_name && (
                                    <Badge size="xs" variant="light" color="blue">
                                      {chatDetail.lead_stage_name}
                                    </Badge>
                                  )}
                                  {chatDetail.lead_estimated_value && (
                                    <Badge size="xs" variant="outline">
                                      Оценка: {chatDetail.lead_estimated_value} ₽
                                    </Badge>
                                  )}
                                  {chatDetail.lead_actual_value && (
                                    <Badge size="xs" variant="outline" color="green">
                                      Факт: {chatDetail.lead_actual_value} ₽
                                    </Badge>
                                  )}
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
                              </Stack>
                            )}
                          </Stack>
                        </Flex>
                      </Stack>
                    )}
                    <Box
                      style={{
                        flex: 1,
                        minHeight: 0,
                      }}
                    >
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
                                  : "var(--bg-card-soft, var(--bg-main))",
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
                    </Box>
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
                )
              }
              right={
                <Tabs defaultValue="client" orientation="vertical">
                  <Tabs.List>
                    <Tabs.Tab value="client">Client</Tabs.Tab>
                    <Tabs.Tab value="forms">Forms</Tabs.Tab>
                    <Tabs.Tab value="timeline">Timeline</Tabs.Tab>
                    <Tabs.Tab value="ai">AI</Tabs.Tab>
                  </Tabs.List>
                  <Tabs.Panel value="client" pt="xs">
                    <Stack gap="xs">
                      {loyaltySummary ? (
                        <>
                          <Text size="sm" fw={600}>
                            Профиль пациента
                          </Text>
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
                          {loyaltySummary.patient_id && (
                            <Button
                              component={Link}
                              to={`/admin/loyalty?patient_id=${encodeURIComponent(
                                loyaltySummary.patient_id,
                              )}`}
                              size="xs"
                              variant="light"
                            >
                              Открыть лояльность
                            </Button>
                          )}
                        </>
                      ) : (
                        <Text size="xs" c="dimmed">
                          Данные по лояльности будут доступны после выбора чата.
                        </Text>
                      )}
                      <Stack gap={4} mt="sm">
                        <Text size="sm" fw={600}>
                          Задачи
                        </Text>
                        <Text size="xs" c="dimmed">
                          Открытых задач в клинике: {openTasksCount}
                        </Text>
                        <Button
                          component={Link}
                          to="/admin/tasks"
                          size="xs"
                          variant="light"
                        >
                          Открыть список задач
                        </Button>
                      </Stack>
                    </Stack>
                  </Tabs.Panel>
                  <Tabs.Panel value="forms" pt="xs">
                    <Stack gap="xs">
                      <Text size="sm" fw={600}>
                        Анкеты и согласия
                      </Text>
                      {!patientId ? (
                        <Text size="xs" c="dimmed">
                          Выберите чат с привязанным пациентом, чтобы видеть статус форм.
                        </Text>
                      ) : (
                        <>
                          <Text size="xs" c="dimmed">
                            Заполнено форм: {formSubmissions?.length ?? 0}
                          </Text>
                          {formSubmissions && formSubmissions.length > 0 && (
                            <Stack gap={4}>
                              {formSubmissions.map((s) => (
                                <Text key={s.id} size="xs">
                                  • {s.template_name}
                                </Text>
                              ))}
                            </Stack>
                          )}
                          <Button
                            component={Link}
                            to={`/admin/forms?patient_id=${encodeURIComponent(patientId)}`}
                            size="xs"
                            variant="light"
                          >
                            Открыть формы и согласия
                          </Button>
                          <Text size="xs" c="dimmed">
                            Отправьте пациенту ссылку на раздел «Анкеты и согласия» в PWA, чтобы
                            он заполнил недостающие формы.
                          </Text>
                        </>
                      )}
                    </Stack>
                  </Tabs.Panel>
                  <Tabs.Panel value="timeline" pt="xs">
                    <Stack gap="xs">
                      <Text size="sm" fw={600}>
                        Timeline
                      </Text>
                      {loyaltySummary?.patient_id ? (
                        <Text size="xs" c="dimmed">
                          История записей и форм недоступна в кратком виде. Откройте формы и
                          историю, чтобы увидеть детали.
                        </Text>
                      ) : (
                        <Text size="xs" c="dimmed">
                          Нет связанного пациента.
                        </Text>
                      )}
                      {loyaltySummary?.patient_id && (
                        <Button component={Link} to={`/admin/forms`} size="xs" variant="light">
                          Открыть формы и согласия
                        </Button>
                      )}
                    </Stack>
                  </Tabs.Panel>
                  <Tabs.Panel value="ai" pt="xs">
                    <Stack gap="xs">
                      <Text size="sm" fw={600}>
                        AI‑агент
                      </Text>
                      <Text size="xs" c="dimmed">
                        Управляйте режимом работы AI‑агента в этом диалоге и наблюдайте за
                        качеством ответов.
                      </Text>
                      {chatDetail && (
                        <Text size="xs" c="dimmed">
                          Текущий режим:{" "}
                          {chatDetail.ai_mode === "AUTO_REPLY"
                            ? "Автоответ"
                            : chatDetail.ai_mode === "ASSISTANT"
                              ? "Подсказки"
                              : "Выкл"}
                        </Text>
                      )}
                    </Stack>
                  </Tabs.Panel>
                </Tabs>
              }
            />
          )}
        </Stack>
      </AppCard>

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
