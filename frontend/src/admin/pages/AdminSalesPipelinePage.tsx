import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useVirtualizer } from "@tanstack/react-virtual";
import type { InfiniteData } from "@tanstack/react-query";
import { useQueryClient } from "@tanstack/react-query";
import {
  useCrmPipelines,
  useCrmStages,
  useCrmKanbanStageLeadsInfinite,
  useCrmLeadDetails,
  useCreateLeadNote,
  useUpdateLeadStage,
  useAiLeadSummary,
  useAiSuggestNextStage,
  useAiUpdateLeadStage,
  useAiCreateTaskForLead,
  useAiIgnoreLeadRecommendation,
  usePipelineStageSemantics,
  type LeadKanbanCard,
  type LeadKanbanCursorResponse,
  type LeadStage,
} from "@/hooks/useCrmLeads";
import {
  Alert,
  Badge,
  Box,
  Checkbox,
  Flex,
  Group,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  TextInput,
  Select,
  Button,
  Tooltip,
  Divider,
} from "@mantine/core";
import { IconBrandWhatsapp, IconBrandTelegram, IconMessageCircle } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import {
  DndContext,
  PointerSensor,
  useSensor,
  useSensors,
  useDraggable,
  useDroppable,
  type DragEndEvent,
} from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { ContextBar } from "@/shared/ui/ContextBar";
import { useSearchParams } from "react-router-dom";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useAiFeatures, getAiFeatureTooltip } from "@/shared/aiFeatures";
import { logUiEvent } from "@/shared/uiEvents";
import { useAvailableAiTools } from "@/hooks/useAvailableAiTools";
import { AdminDataTableSurface, AdminDataTableToolbar, AiFeatureBadge, QueryErrorAlert } from "@/shared/ui";
import {
  buildSemanticMapFromResolved,
  buildStageIdToSemantic,
  canTransitionSemantic,
} from "@/shared/crmStageSemantics";
import { ApiErrorWithCode } from "@/api/client";
import { useUiLocale } from "@/i18n/useUiLocale";
import { crmLeadStatusLabel } from "@/shared/crmI18n";

const STAGE_DROPPABLE_PREFIX = "stage-";

const CRM_KANBAN_STRICT_SEMANTICS_KEY = "crm-kanban-strict-semantics";

function formatCrmAmount(value: string | number | null | undefined, dateLocale: string): string {
  const n = Number(value ?? 0);
  if (!Number.isFinite(n)) return String(value ?? "0");
  return new Intl.NumberFormat(dateLocale).format(n);
}

function DraggableLeadCard({
  lead,
  onSelectLead,
  children,
}: {
  lead: LeadKanbanCard;
  onSelectLead: (leadId: string) => void;
  children: React.ReactNode;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: lead.id,
  });

  const style = {
    transform: transform ? CSS.Translate.toString(transform) : undefined,
    opacity: isDragging ? 0.85 : 1,
  };

  return (
    <Box
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      onClick={() => onSelectLead(lead.id)}
    >
      {children}
    </Box>
  );
}

const ROTTING_DAYS = 2;

function isLeadRotting(createdAt: string): boolean {
  const created = new Date(createdAt).getTime();
  const now = Date.now();
  return (now - created) / (24 * 60 * 60 * 1000) > ROTTING_DAYS;
}

interface KanbanColumnProps {
  stage: LeadStage;
  leads: LeadKanbanCard[];
  onSelectLead: (leadId: string) => void;
  selectedLeadId: string | null;
  hasNextPage?: boolean;
  fetchNextPage?: () => void;
  isFetchingNextPage?: boolean;
}

function KanbanColumn({
  stage,
  leads,
  onSelectLead,
  selectedLeadId,
  hasNextPage,
  fetchNextPage,
  isFetchingNextPage,
}: KanbanColumnProps) {
  const { t } = useTranslation("crm");
  const { locale } = useUiLocale();
  const dateLocale = locale === "en" ? "en-US" : "ru-RU";
  const droppableId = `${STAGE_DROPPABLE_PREFIX}${stage.id}`;
  const { isOver, setNodeRef } = useDroppable({ id: droppableId });
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const count = stage.leads_count ?? leads.length;
  const sumVal =
    stage.sum_estimated_value != null
      ? Number(stage.sum_estimated_value)
      : leads.reduce((a, l) => a + Number(l.estimated_value || 0), 0);
  const sumFormatted = new Intl.NumberFormat(dateLocale).format(sumVal);

  const virtualizer = useVirtualizer({
    count: leads.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 148,
    overscan: 6,
  });

  return (
    <Stack
      ref={setNodeRef}
      gap="xs"
      style={{
        minHeight: 120,
        borderRadius: "var(--radius-md)",
        padding: "var(--space-sm)",
        background: isOver ? "var(--primary-alpha-08)" : undefined,
        border: isOver ? "2px dashed var(--primary)" : undefined,
      }}
    >
      <Group gap="xs" wrap="wrap">
        <Badge color={stage.color || "blue"} variant="light" radius="sm">
          {stage.name}
        </Badge>
        <Text size="xs" c="dimmed">
          {t("pipeline.columnMeta", { count, sum: sumFormatted })}
        </Text>
      </Group>
      <Box
        ref={scrollRef}
        style={{
          height: 380,
          overflow: "auto",
          position: "relative",
        }}
      >
        <div
          style={{
            height: virtualizer.getTotalSize(),
            width: "100%",
            position: "relative",
          }}
        >
          {virtualizer.getVirtualItems().map((vi) => {
            const lead = leads[vi.index];
            return (
              <div
                key={vi.key}
                data-index={vi.index}
                ref={virtualizer.measureElement}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  transform: `translateY(${vi.start}px)`,
                }}
              >
                <DraggableLeadCard lead={lead} onSelectLead={onSelectLead}>
                  <Box
                    p="sm"
                    mb={6}
                    style={{
                      borderRadius: "var(--radius-md)",
                      border:
                        selectedLeadId === lead.id
                          ? "2px solid var(--primary)"
                          : isLeadRotting(lead.created_at)
                            ? "1px solid var(--mantine-color-orange-6)"
                            : "1px solid var(--divider)",
                      background:
                        selectedLeadId === lead.id
                          ? "var(--primary-alpha-08)"
                          : isLeadRotting(lead.created_at)
                            ? "var(--orange-alpha-06)"
                            : "var(--dark-alpha-02)",
                      cursor: "grab",
                      contentVisibility: "auto",
                    }}
                  >
                    <Stack gap={4}>
                      <Group gap={4} justify="space-between" wrap="nowrap">
                        <Text fw={600} size="sm" lineClamp={2} style={{ flex: 1 }}>
                          {lead.title}
                        </Text>
                        {lead.omnichannel_contact_id && (
                          <Tooltip label={t("pipeline.openChat")}>
                            <Button
                              component={Link}
                              to={`/admin/omni-chat?contact_id=${lead.omnichannel_contact_id}`}
                              variant="subtle"
                              size="compact-xs"
                              p={4}
                              onClick={(e) => e.stopPropagation()}
                              aria-label={t("pipeline.chatAria")}
                            >
                              {lead.source?.toLowerCase().includes("whatsapp") ? (
                                <IconBrandWhatsapp size={16} />
                              ) : lead.source?.toLowerCase().includes("telegram") ||
                                lead.source?.toLowerCase().includes("tg") ? (
                                <IconBrandTelegram size={16} />
                              ) : (
                                <IconMessageCircle size={16} />
                              )}
                            </Button>
                          </Tooltip>
                        )}
                      </Group>
                      <Text size="xs" c="dimmed">
                        {t("pipeline.source", { source: lead.source || "—" })}
                      </Text>
                      <Group gap={6} wrap="wrap">
                        <Tooltip label={t("pipeline.estimatedTooltip")}>
                          <Badge size="xs" variant="light">
                            {t("pipeline.estimated", {
                              amount: formatCrmAmount(lead.estimated_value, dateLocale),
                            })}
                          </Badge>
                        </Tooltip>
                        <Tooltip label={t("pipeline.actualTooltip")}>
                          <Badge size="xs" variant="light" color="green">
                            {t("pipeline.actual", {
                              amount: formatCrmAmount(lead.actual_value, dateLocale),
                            })}
                          </Badge>
                        </Tooltip>
                        <Badge
                          size="xs"
                          variant="outline"
                          color={
                            lead.status === "success"
                              ? "green"
                              : lead.status === "lost"
                                ? "red"
                                : "gray"
                          }
                        >
                          {crmLeadStatusLabel(lead.status)}
                        </Badge>
                      </Group>
                      {lead.status === "open" && Number(lead.actual_value) === 0 ? (
                        <Text size="xs" c="dimmed">
                          {t("pipeline.actualZeroOpen")}
                        </Text>
                      ) : null}
                      {lead.status === "success" && Number(lead.actual_value) === 0 ? (
                        <Text size="xs" c="orange">
                          {t("pipeline.actualZeroWon")}
                        </Text>
                      ) : null}
                      <Group gap={4} justify="space-between">
                        <Text size="xs" c="dimmed">
                          {t("pipeline.created", {
                            date: new Date(lead.created_at).toLocaleDateString(dateLocale),
                          })}
                        </Text>
                      </Group>
                    </Stack>
                  </Box>
                </DraggableLeadCard>
              </div>
            );
          })}
        </div>
      </Box>
      {hasNextPage && fetchNextPage ? (
        <Button
          size="xs"
          variant="light"
          fullWidth
          loading={isFetchingNextPage}
          onClick={() => fetchNextPage()}
        >
          {t("pipeline.loadMore")}
        </Button>
      ) : null}
    </Stack>
  );
}

function KanbanColumnLoader({
  stage,
  selectedStageId,
  statusFilter,
  search,
  onSelectLead,
  selectedLeadId,
}: {
  stage: LeadStage;
  selectedStageId: string | null;
  statusFilter: string | null;
  search: string;
  onSelectLead: (leadId: string) => void;
  selectedLeadId: string | null;
}) {
  const enabled = !selectedStageId || selectedStageId === stage.id;
  const infinite = useCrmKanbanStageLeadsInfinite({
    stageId: stage.id,
    status: statusFilter || undefined,
    search: search || undefined,
    enabled,
  });
  const leads = infinite.data?.pages.flatMap((p) => p.items) ?? [];

  return (
    <KanbanColumn
      stage={stage}
      leads={leads}
      onSelectLead={onSelectLead}
      selectedLeadId={selectedLeadId}
      hasNextPage={infinite.hasNextPage}
      fetchNextPage={() => infinite.fetchNextPage()}
      isFetchingNextPage={infinite.isFetchingNextPage}
    />
  );
}

export default function AdminSalesPipelinePage() {
  const { t } = useTranslation("crm");
  const { locale } = useUiLocale();
  const dateLocale = locale === "en" ? "en-US" : "ru-RU";
  const [searchParams] = useSearchParams();
  const initialLeadId = searchParams.get("lead_id");
  const { currentClinicId } = useAdminClinic();
  const aiFeatures = useAiFeatures(currentClinicId ?? null);
  const crmStageFeature = aiFeatures.get("omni.tools.crm_suggest_next_stage");
  const createTaskFeature = aiFeatures.get("omni.tools.create_task");
  const availableTools = useAvailableAiTools(currentClinicId ?? null);
  const canCrmAi = availableTools.hasAll(["summarize_lead_context", "suggest_next_stage_for_lead"]);
  const canApplyStage = availableTools.hasAll(["update_lead_stage"]);
  const canCreateAiTask = availableTools.hasAll(["create_task_for_lead"]);
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(
    initialLeadId
  );
  const [noteText, setNoteText] = useState("");
  const [prepaymentCopyFeedback, setPrepaymentCopyFeedback] = useState(false);
  const [prepaymentCopyError, setPrepaymentCopyError] = useState<string | null>(null);

  const queryClient = useQueryClient();
  const {
    data: pipelines,
    isLoading: pipelinesLoading,
    isError: pipelinesError,
    error: pipelinesLoadError,
  } = useCrmPipelines();
  const {
    data: stages,
    isLoading: stagesLoading,
    isError: stagesError,
    error: stagesLoadError,
  } = useCrmStages(selectedPipelineId);
  const { data: pipelineSemantics } = usePipelineStageSemantics(selectedPipelineId);
  const stageIdToSemantic = useMemo(() => {
    const resolved = pipelineSemantics?.resolved_stage_semantics;
    if (resolved?.length) {
      return buildSemanticMapFromResolved(resolved);
    }
    return buildStageIdToSemantic(pipelineSemantics?.mappings ?? []);
  }, [pipelineSemantics?.resolved_stage_semantics, pipelineSemantics?.mappings]);

  const [strictKanbanSemantics, setStrictKanbanSemantics] = useState(() => {
    try {
      return typeof localStorage !== "undefined" && localStorage.getItem(CRM_KANBAN_STRICT_SEMANTICS_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [semanticDragBlock, setSemanticDragBlock] = useState<string | null>(null);

  useEffect(() => {
    try {
      localStorage.setItem(CRM_KANBAN_STRICT_SEMANTICS_KEY, strictKanbanSemantics ? "1" : "0");
    } catch {
      // ignore
    }
  }, [strictKanbanSemantics]);

  useEffect(() => {
    setSemanticDragBlock(null);
  }, [selectedPipelineId]);

  useEffect(() => {
    if (!prepaymentCopyFeedback) return;
    const timer = window.setTimeout(() => setPrepaymentCopyFeedback(false), 2500);
    return () => window.clearTimeout(timer);
  }, [prepaymentCopyFeedback]);

  const { data: leadDetails, isLoading: leadDetailsLoading, isError: leadDetailsError, error: leadDetailsLoadError } = useCrmLeadDetails(
    selectedLeadId
  );
  const createNote = useCreateLeadNote();
  const updateLeadStage = useUpdateLeadStage();
  const aiSummary = useAiLeadSummary(selectedLeadId);
  const aiSuggestStage = useAiSuggestNextStage(selectedLeadId);
  const aiApplyStage = useAiUpdateLeadStage(selectedLeadId);
  const aiCreateTask = useAiCreateTaskForLead(selectedLeadId);
  const aiIgnore = useAiIgnoreLeadRecommendation(selectedLeadId);

  useEffect(() => {
    setNoteText("");
    setPrepaymentCopyFeedback(false);
    setPrepaymentCopyError(null);
    createNote.reset();
    aiApplyStage.reset();
    aiCreateTask.reset();
    aiIgnore.reset();
  }, [selectedLeadId, createNote, aiApplyStage, aiCreateTask, aiIgnore]);

  const pipelineOptions =
    pipelines?.map((p) => ({
      value: p.id,
      label: p.name + (p.is_default ? t("pipeline.defaultSuffix") : ""),
    })) ?? [];

  const stageOptions =
    stages?.map((s) => ({
      value: s.id,
      label: s.name,
    })) ?? [];

  const handleAddNote = () => {
    if (!selectedLeadId || !noteText.trim()) return;
    createNote.mutate(
      { leadId: selectedLeadId, text: noteText.trim() },
      {
        onSuccess: () => {
          setNoteText("");
        },
      }
    );
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setSemanticDragBlock(null);
    if (!over || typeof over.id !== "string") return;
    const overId = String(over.id);
    if (!overId.startsWith(STAGE_DROPPABLE_PREFIX)) return;
    const newStageId = overId.slice(STAGE_DROPPABLE_PREFIX.length);
    const leadId = String(active.id);
    const flat = queryClient
      .getQueriesData<InfiniteData<LeadKanbanCursorResponse>>({ queryKey: ["crm-leads-kanban"] })
      .flatMap(([, d]) => d?.pages.flatMap((p) => p.items) ?? []);
    const lead = flat.find((l) => l.id === leadId);
    if (!lead || lead.stage_id === newStageId) return;
    if (strictKanbanSemantics) {
      const fromSem = stageIdToSemantic[lead.stage_id];
      const toSem = stageIdToSemantic[newStageId];
      if (fromSem && toSem && !canTransitionSemantic(fromSem, toSem)) {
        setSemanticDragBlock(
          t("pipeline.strictBlocked", { from: fromSem, to: toSem })
        );
        return;
      }
    }
    updateLeadStage.mutate(
      { leadId, newStageId, enforceSemanticTransition: strictKanbanSemantics },
      {
        onError: (err) => {
          const msg =
            err instanceof ApiErrorWithCode && err.code === "semantic_transition_invalid"
              ? t("errors.semanticRejected", {
                  from: String(err.details?.from_semantic ?? "?"),
                  to: String(err.details?.to_semantic ?? "?"),
                })
              : err instanceof Error
                ? err.message
                : t("errors.stageChangeFailed");
          setSemanticDragBlock(msg);
        },
      }
    );
  };

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: { distance: 6 },
    })
  );

  // When opened with lead_id in query, try to auto-select pipeline/stage once details are loaded
  useEffect(() => {
    if (!leadDetails || !initialLeadId) return;
    setSelectedLeadId(initialLeadId);
    if (!selectedPipelineId) {
      setSelectedPipelineId(leadDetails.lead.pipeline_id);
    }
    if (!selectedStageId) {
      setSelectedStageId(leadDetails.lead.stage_id);
    }
    // Intentionally limited deps (selectedPipelineId/selectedStageId omitted) to avoid loops
  }, [leadDetails, initialLeadId]);

  if (pipelinesLoading) {
    return (
      <Stack>
        <ContextBar title={t("pipeline.title")} />
        <DataSkeleton lines={4} />
      </Stack>
    );
  }

  if (pipelinesError) {
    return (
      <Stack>
        <ContextBar title={t("pipeline.title")} />
        <QueryErrorAlert error={pipelinesLoadError} title={t("errors.loadFailed", { ns: "common" })} />
      </Stack>
    );
  }

  if (!pipelines?.length) {
    return (
      <Stack>
        <ContextBar title={t("pipeline.title")} />
        <EmptyStateHint
          title={t("pipeline.emptyPipelinesTitle")}
          subtitle={t("pipeline.emptyPipelinesHint")}
        />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <ContextBar title={t("pipeline.title")} />
      <ThreeColumnLayout
        preset="wide-center"
        left={
          <AdminDataTableToolbar>
          <Stack gap="sm">
            <Text size="sm" fw={500}>
              {t("pipeline.filters")}
            </Text>
            <Select
              label={t("pipeline.pipeline")}
              placeholder={t("pipeline.pickPipeline")}
              data={pipelineOptions}
              value={selectedPipelineId}
              onChange={(v) => {
                setSelectedPipelineId(v);
                setSelectedStageId(null);
              }}
              styles={{ label: { fontSize: 12 } }}
            />
            <Select
              label={t("pipeline.stage")}
              placeholder={t("pipeline.allStages")}
              data={stageOptions}
              value={selectedStageId}
              onChange={setSelectedStageId}
              disabled={!stages?.length}
              styles={{ label: { fontSize: 12 } }}
            />
            <Select
              label={t("pipeline.status")}
              placeholder={t("pipeline.allStatuses")}
              value={statusFilter}
              onChange={setStatusFilter}
              data={[
                { value: "open", label: t("pipeline.statusOpen") },
                { value: "success", label: t("pipeline.statusWon") },
                { value: "lost", label: t("pipeline.statusLost") },
              ]}
              styles={{ label: { fontSize: 12 } }}
            />
            <TextInput
              label={t("pipeline.search")}
              placeholder={t("pipeline.searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              styles={{ label: { fontSize: 12 } }}
            />
            <Checkbox
              label={t("pipeline.strictKanban")}
              checked={strictKanbanSemantics}
              onChange={(e) => setStrictKanbanSemantics(e.currentTarget.checked)}
              styles={{ label: { fontSize: 12 } }}
            />
            <Text size="xs" c="dimmed">
              {t("pipeline.strictHint")}
            </Text>
          </Stack>
          </AdminDataTableToolbar>
        }
        center={
          <AdminDataTableSurface>
            {semanticDragBlock ? (
              <Alert color="orange" mb="sm" onClose={() => setSemanticDragBlock(null)} withCloseButton>
                {semanticDragBlock}
              </Alert>
            ) : null}
            {stagesError ? (
              <QueryErrorAlert error={stagesLoadError} title={t("errors.loadFailed", { ns: "common" })} />
            ) : stagesLoading ? (
              <DataSkeleton lines={4} />
            ) : !stages || !stages.length ? (
              <EmptyStateHint
                title={t("pipeline.emptyStagesTitle")}
                subtitle={t("pipeline.emptyStagesHint")}
              />
            ) : (
              <ScrollArea h={420} type="scroll">
                <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
                  <Flex gap="sm" align="flex-start">
                    {stages.map((stage) => (
                      <Box
                        key={stage.id}
                        style={{
                          minWidth: 260,
                          maxWidth: 320,
                        }}
                      >
                        <KanbanColumnLoader
                          stage={stage}
                          selectedStageId={selectedStageId}
                          statusFilter={statusFilter}
                          search={search}
                          onSelectLead={setSelectedLeadId}
                          selectedLeadId={selectedLeadId}
                        />
                      </Box>
                    ))}
                  </Flex>
                </DndContext>
              </ScrollArea>
            )}
          </AdminDataTableSurface>
        }
        right={
          <AdminDataTableSurface>
            {!selectedLeadId ? (
              <EmptyStateHint
                title={t("pipeline.pickLeadTitle")}
                subtitle={t("pipeline.pickLeadHint")}
              />
            ) : leadDetailsLoading ? (
              <DataSkeleton lines={4} />
            ) : leadDetailsError ? (
              <QueryErrorAlert error={leadDetailsLoadError} title={t("errors.loadFailed", { ns: "common" })} />
            ) : !leadDetails ? (
              <EmptyStateHint
                title={t("pipeline.leadMissingTitle")}
                subtitle={t("pipeline.leadMissingHint")}
              />
            ) : (
              <Stack gap="sm">
                <Stack gap={2}>
                  <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                      <Text fw={700}>{leadDetails.lead.title}</Text>
                      <Text size="sm" c="dimmed">
                        {t("pipeline.source", { source: leadDetails.lead.source || "—" })}
                      </Text>
                    </Stack>
                    <Stack gap={4} align="flex-end">
                      <Badge size="sm" variant="outline">
                        {crmLeadStatusLabel(leadDetails.lead.status)}
                      </Badge>
                      <Text size="xs" c="dimmed">
                        {t("pipeline.created", {
                          date: new Date(leadDetails.lead.created_at).toLocaleDateString(dateLocale),
                        })}
                      </Text>
                    </Stack>
                  </Group>
                  <Group gap="xs">
                    <Tooltip label={t("pipeline.estimatedTooltip")}>
                      <Badge size="sm" variant="light">
                        {t("pipeline.estimated", {
                          amount: formatCrmAmount(leadDetails.lead.estimated_value, dateLocale),
                        })}
                      </Badge>
                    </Tooltip>
                    <Tooltip label={t("pipeline.actualTooltip")}>
                      <Badge size="sm" variant="light" color="green">
                        {t("pipeline.actual", {
                          amount: formatCrmAmount(leadDetails.lead.actual_value, dateLocale),
                        })}
                      </Badge>
                    </Tooltip>
                  </Group>
                  {leadDetails.lead.status === "open" && Number(leadDetails.lead.actual_value) === 0 ? (
                    <Text size="xs" c="dimmed">
                      {t("pipeline.actualZeroOpenDetail")}
                    </Text>
                  ) : null}
                  {leadDetails.lead.status === "success" && Number(leadDetails.lead.actual_value) === 0 ? (
                    <Text size="xs" c="orange">
                      {t("pipeline.actualZeroWonDetail")}
                    </Text>
                  ) : null}
                </Stack>

                {leadDetails.lead.omnichannel_contact_id && (
                  <Button
                    component={Link}
                    to={`/admin/omni-chat?contact_id=${leadDetails.lead.omnichannel_contact_id}`}
                    variant="light"
                    size="sm"
                    fullWidth
                    mb="xs"
                    leftSection={<IconMessageCircle size={16} />}
                  >
                    {t("pipeline.openChat")}
                  </Button>
                )}

                <Divider my="xs" />

                <Stack gap={6}>
                  <Group gap="xs" wrap="wrap">
                    <Text fw={600} size="sm">
                      {t("pipeline.aiTitle")}
                    </Text>
                    <AiFeatureBadge status={crmStageFeature.status} />
                  </Group>
                  <Group grow>
                    <Button
                      variant="light"
                      size="xs"
                      onClick={() => {
                        if (crmStageFeature.status === "stub") return;
                        void logUiEvent({
                          event_name: "ai_click_summary",
                          clinic_id: currentClinicId,
                          feature_id: crmStageFeature.id,
                          feature_status: crmStageFeature.status,
                          meta: { lead_id: selectedLeadId },
                        });
                        aiSummary.refetch();
                      }}
                      loading={aiSummary.isFetching}
                      disabled={!selectedLeadId || crmStageFeature.status === "stub" || !canCrmAi}
                      title={
                        crmStageFeature.status === "stub"
                          ? getAiFeatureTooltip(crmStageFeature.status)
                          : !canCrmAi
                            ? t("pipeline.aiToolUnavailable")
                            : undefined
                      }
                    >
                      {t("pipeline.aiSummary")}
                    </Button>
                    <Button
                      variant="light"
                      size="xs"
                      onClick={() => {
                        if (crmStageFeature.status === "stub") return;
                        void logUiEvent({
                          event_name: "ai_click_suggest_stage",
                          clinic_id: currentClinicId,
                          feature_id: crmStageFeature.id,
                          feature_status: crmStageFeature.status,
                          meta: { lead_id: selectedLeadId },
                        });
                        aiSuggestStage.refetch();
                      }}
                      loading={aiSuggestStage.isFetching}
                      disabled={!selectedLeadId || crmStageFeature.status === "stub" || !canCrmAi}
                      title={
                        crmStageFeature.status === "stub"
                          ? getAiFeatureTooltip(crmStageFeature.status)
                          : !canCrmAi
                            ? t("pipeline.aiToolUnavailable")
                            : undefined
                      }
                    >
                      {t("pipeline.aiNextStage")}
                    </Button>
                  </Group>

                  {crmStageFeature.status === "stub" && (
                    <Text size="xs" c="dimmed">
                      {getAiFeatureTooltip(crmStageFeature.status)}
                    </Text>
                  )}

                  {aiSummary.isError ? (
                    <QueryErrorAlert error={aiSummary.error} title={t("pipeline.aiActionFailed")} />
                  ) : null}

                  {aiSummary.data?.summary && (
                    <Box
                      p="xs"
                      style={{
                        borderRadius: "var(--radius-md)",
                        background: "var(--primary-alpha-06)",
                        border: "1px solid var(--primary-alpha-25)",
                      }}
                    >
                      <Text size="xs" c="dimmed" mb={4}>
                        {t("pipeline.aiMode", {
                          status: aiSummary.data.ai_status ?? "—",
                        })}
                      </Text>
                      <Text size="sm">{aiSummary.data.summary}</Text>
                    </Box>
                  )}

                  {aiSuggestStage.isError ? (
                    <QueryErrorAlert error={aiSuggestStage.error} title={t("pipeline.aiActionFailed")} />
                  ) : null}

                  {aiSuggestStage.data && (
                    <Box
                      p="xs"
                      style={{
                        borderRadius: "var(--radius-md)",
                        background: "var(--dark-alpha-02)",
                        border: "1px solid var(--muted-alpha-40)",
                      }}
                    >
                      <Text size="xs" c="dimmed">
                        {t("pipeline.confidence", {
                          pct: Math.round((aiSuggestStage.data.confidence || 0) * 100),
                        })}
                      </Text>
                      <Text size="sm">
                        {t("pipeline.suggestedStage", {
                          name: aiSuggestStage.data.suggested_stage_id
                            ? stages?.find((s) => s.id === aiSuggestStage.data!.suggested_stage_id)?.name ??
                              "—"
                            : "—",
                        })}
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
                                lead_id: selectedLeadId,
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
                          {t("pipeline.apply")}
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
                              meta: { lead_id: selectedLeadId, kind: "stage" },
                            });
                            aiIgnore.mutate({
                              clinic_id: currentClinicId,
                              kind: "stage",
                              reason: "operator_ignored",
                            });
                          }}
                        >
                          {t("pipeline.ignore")}
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
                                ? t("pipeline.aiToolUnavailable")
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
                              meta: { lead_id: selectedLeadId },
                            });
                            aiCreateTask.mutate({
                              clinic_id: currentClinicId,
                              title: t("pipeline.aiTaskTitle"),
                              description: aiSuggestStage.data?.rationale ?? undefined,
                              priority: "medium",
                              initiated_by_ai: true,
                              reason: "ai_recommendation_followup",
                            });
                          }}
                        >
                          {t("pipeline.createTask")}
                        </Button>
                      </Group>
                      {aiApplyStage.isError ? (
                        <QueryErrorAlert error={aiApplyStage.error} title={t("pipeline.aiActionFailed")} />
                      ) : null}
                      {aiIgnore.isError ? (
                        <QueryErrorAlert error={aiIgnore.error} title={t("pipeline.aiActionFailed")} />
                      ) : null}
                      {aiCreateTask.isError ? (
                        <QueryErrorAlert error={aiCreateTask.error} title={t("pipeline.aiActionFailed")} />
                      ) : null}
                    </Box>
                  )}
                </Stack>

                <Button
                  variant="light"
                  size="sm"
                  fullWidth
                  mb="sm"
                  onClick={() => {
                    const amount = leadDetails.lead.estimated_value || leadDetails.lead.actual_value || "0";
                    const url = `${window.location.origin}/prepayment?lead_id=${leadDetails.lead.id}&amount=${amount}`;
                    setPrepaymentCopyError(null);
                    void navigator.clipboard.writeText(url).then(
                      () => {
                        setPrepaymentCopyFeedback(true);
                      },
                      () => {
                        setPrepaymentCopyError(t("pipeline.copyFailed"));
                      }
                    );
                  }}
                >
                  {t("pipeline.prepaymentLink")}
                </Button>
                {prepaymentCopyFeedback ? (
                  <Text size="xs" c="green" mb="xs">
                    {t("pipeline.prepaymentCopied")}
                  </Text>
                ) : null}
                {prepaymentCopyError ? (
                  <Text size="xs" c="red" mb="xs">
                    {prepaymentCopyError}
                  </Text>
                ) : null}

                <Stack gap={4}>
                  <Text fw={600} size="sm">
                    {t("pipeline.notes")}
                  </Text>
                  <ScrollArea h={160} type="scroll">
                    {leadDetails.notes.length === 0 ? (
                      <Text size="xs" c="dimmed">
                        {t("pipeline.noNotes")}
                      </Text>
                    ) : (
                      <Stack gap="xs">
                        {leadDetails.notes.map((note) => (
                          <Box
                            key={note.id}
                            p="xs"
                            style={{
                              borderRadius: "var(--radius-md)",
                              background: "var(--dark-alpha-02)",
                              border: "1px solid var(--muted-alpha-40)",
                            }}
                          >
                            <Text size="sm">{note.text}</Text>
                            <Text size="xs" c="dimmed">
                              {new Date(note.created_at).toLocaleString(dateLocale)}
                            </Text>
                          </Box>
                        ))}
                      </Stack>
                    )}
                  </ScrollArea>
                  <Textarea
                    placeholder={t("pipeline.notePlaceholder")}
                    minRows={2}
                    value={noteText}
                    onChange={(e) => setNoteText(e.currentTarget.value)}
                  />
                  <Group justify="flex-end">
                    <Button
                      size="xs"
                      onClick={handleAddNote}
                      loading={createNote.isPending}
                      disabled={!noteText.trim() || createNote.isPending}
                    >
                      {t("pipeline.saveNote")}
                    </Button>
                  </Group>
                  {createNote.isError ? (
                    <QueryErrorAlert error={createNote.error} title={t("errors.saveFailed")} />
                  ) : null}
                </Stack>
              </Stack>
            )}
          </AdminDataTableSurface>
        }
      />
    </Stack>
  );
}

