import { useMemo, useState, useCallback, useRef, useEffect } from "react";
import { useAdminTasksOpen, useCreateAdminTaskMutation } from "@/hooks";
import {
  useAdminOmniChats,
  useAdminOmniChatDetail,
  useAdminOmniChatMessages,
  useSendAdminOmniMessage,
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
  AppCard,
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
  Divider,
  Tooltip,
} from "@mantine/core";
import { useHotkeys } from "@mantine/hooks";
import { GlassModal } from "@/shared/ui/GlassModal";
import { Textarea } from "@mantine/core";
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";
import { getAdminId } from "@/api/client";
import { useAiFeatures, getAiFeatureTooltip } from "@/shared/aiFeatures";
import { useEffectiveAiFeatureGate } from "@/hooks/useEffectiveAiFeatureGate";
import { logUiEvent } from "@/shared/uiEvents";
import { useAvailableAiTools } from "@/hooks/useAvailableAiTools";

export default function AdminOmniChatPage() {
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
  const [showOnlyWaiting, setShowOnlyWaiting] = useState(false);
  const [showHiddenMessages, setShowHiddenMessages] = useState(false);
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
    ["mod+Enter", () => { if (selectedChatId && messageText.trim()) handleSend(); }],
    ["Escape", () => { setFormDrawerOpen(false); setTaskDrawerOpen(false); }],
  ]);

  useEffect(() => {
    // Prefill task template when context changes.
    if (!taskDrawerOpen) return;
    const base = leadId ? "Follow‑up по лиду из чата" : patientId ? "Follow‑up по пациенту из чата" : "Follow‑up по чату";
    setTaskTitle((prev) => prev || base);
  }, [taskDrawerOpen, leadId, patientId]);

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
      <ContextBar title="Chat & AI — единый чат с пациентами" />
      <AppCard>
        <Stack gap="md" style={{ height: 520, minHeight: 0 }}>
          <Flex gap="sm" wrap="wrap" align="center">
            <TextInput
              ref={searchInputRef}
              placeholder="Поиск по контакту (⌘J)"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              style={{ flex: 1, minWidth: 200 }}
            />
            <Group gap="xs" wrap="wrap">
              <Button
                variant={!showOnlyWaiting && !statusFilter ? "filled" : "light"}
                size="xs"
                onClick={() => { setShowOnlyWaiting(false); setStatusFilter(undefined); }}
              >
                Все
              </Button>
              <Button
                variant={showOnlyWaiting ? "filled" : "light"}
                size="xs"
                onClick={() => { setShowOnlyWaiting(true); setStatusFilter(undefined); }}
              >
                Неотвеченные
              </Button>
              <Button variant="light" size="xs" disabled title="Фильтр по VIP (при наличии API)">
                От VIP
              </Button>
              <Button variant="light" size="xs" disabled title="С ошибкой оплаты (при наличии API)">
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
          </Flex>

          {chatsLoading ? (
            <DataSkeleton lines={6} />
          ) : chatsError ? (
            <QueryErrorAlert error={chatsErr} title="Не удалось загрузить диалоги" />
          ) : (
            <Box style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
            <ThreeColumnLayout
              preset="omni-inspector"
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
                                        borderRadius: 8,
                                        background: "rgba(59, 130, 246, 0.06)",
                                        border: "1px solid rgba(59, 130, 246, 0.25)",
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
                                        borderRadius: 8,
                                        background: "rgba(15, 23, 42, 0.02)",
                                        border: "1px solid rgba(148, 163, 184, 0.4)",
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
                    <Stack gap="xs">
                      <Flex gap="sm" wrap="wrap" align="center">
                        <TextInput
                          placeholder="Сообщение... (⌘Enter — отправить)"
                          value={messageText}
                          onChange={(e) => setMessageText(e.currentTarget.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && !e.shiftKey) {
                              e.preventDefault();
                              handleSend();
                            }
                          }}
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
                      <Group gap="xs" wrap="wrap">
                        <Button
                          component={Link}
                          to={ROUTE_PATHS.admin.schedule}
                          size="xs"
                          variant="light"
                          title="Создать запись (откроется расписание)"
                        >
                          Запись
                        </Button>
                        <Button
                          size="xs"
                          variant="light"
                          onClick={() => setFormDrawerOpen(true)}
                          disabled={!patientId}
                          title={!patientId ? "Выберите чат с привязанным пациентом" : "Отправить анкету/форму"}
                        >
                          Анкета
                        </Button>
                      </Group>
                    </Stack>
                  </Stack>
                )
              }
              right={
                <Stack gap="sm" style={{ minWidth: 0 }}>
                  <Paper p="sm" withBorder radius="md" bg="gray.0">
                    <Stack gap="md">
                      {currentClinicId ? (
                        <>
                          <Stack gap="xs">
                            <Text size="xs" fw={600}>
                              Рабочий центр
                            </Text>
                            <Text size="xs" c="dimmed">
                              Быстрый переход: воронка, расписание, задачи.
                            </Text>
                            <Group gap="xs" wrap="wrap">
                              <Button component={Link} to={ROUTE_PATHS.admin.sales} size="xs" variant="light">
                                CRM
                              </Button>
                              <Button component={Link} to={ROUTE_PATHS.admin.schedule} size="xs" variant="light">
                                Расписание
                              </Button>
                              <Button component={Link} to={ROUTE_PATHS.admin.tasks} size="xs" variant="light">
                                Задачи
                              </Button>
                            </Group>
                          </Stack>
                          <Divider />
                        </>
                      ) : null}
                      <Tabs
                        defaultValue="client"
                        styles={{
                          list: {
                            width: "100%",
                            flexWrap: "nowrap",
                          },
                          panel: {
                            minHeight: 380,
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
                                          variant="light"
                                        >
                                          Создать запись
                                        </Button>
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
                                    variant="light"
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
                                    variant="light"
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
                                  variant="light"
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
                                <Button component={Link} to={`/admin/forms`} size="xs" variant="light">
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
              }
            />
            </Box>
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
                <Button variant="default" onClick={() => setFormDrawerOpen(false)}>
                  Отмена
                </Button>
                <Button
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
            label="Назначить на меня"
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
            <Button variant="default" onClick={() => setTaskDrawerOpen(false)}>
              Отмена
            </Button>
            <Button
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
