import { useEffect, useMemo, useState } from "react";
import {
  useCrmPipelines,
  useCrmStages,
  useCrmLeads,
  useCrmLeadDetails,
  useCreateLeadNote,
  useUpdateLeadStage,
  type LeadCard,
  type LeadStage,
} from "@/hooks/useCrmLeads";
import {
  Badge,
  Box,
  Flex,
  Group,
  Paper,
  ScrollArea,
  Stack,
  Text,
  Textarea,
  TextInput,
  Title,
  Select,
  Button,
} from "@mantine/core";
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
import { useSearchParams } from "react-router-dom";

const STAGE_DROPPABLE_PREFIX = "stage-";

function DraggableLeadCard({
  lead,
  onSelectLead,
  children,
}: {
  lead: LeadCard;
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

interface KanbanColumnProps {
  stage: LeadStage;
  leads: LeadCard[];
  onSelectLead: (leadId: string) => void;
  selectedLeadId: string | null;
}

function KanbanColumn({
  stage,
  leads,
  onSelectLead,
  selectedLeadId,
}: KanbanColumnProps) {
  const droppableId = `${STAGE_DROPPABLE_PREFIX}${stage.id}`;
  const { isOver, setNodeRef } = useDroppable({ id: droppableId });

  return (
    <Stack
      ref={setNodeRef}
      gap="xs"
      style={{
        minHeight: 120,
        borderRadius: 8,
        padding: 8,
        background: isOver ? "var(--primary-light, rgba(59, 130, 246, 0.08))" : undefined,
        border: isOver ? "2px dashed var(--primary, #3b82f6)" : undefined,
      }}
    >
      <Group gap="xs">
        <Badge color={stage.color || "blue"} variant="filled" radius="sm">
          {stage.name}
        </Badge>
        <Text size="xs" c="dimmed">
          {leads.length} лидов
        </Text>
      </Group>
      <Stack gap="xs">
        {leads.map((lead) => (
          <DraggableLeadCard
            key={lead.id}
            lead={lead}
            onSelectLead={onSelectLead}
          >
            <Box
              p="sm"
              style={{
                borderRadius: 10,
                border:
                  selectedLeadId === lead.id
                    ? "2px solid var(--primary, #3b82f6)"
                    : "1px solid var(--divider, rgba(148, 163, 184, 0.4))",
                background:
                  selectedLeadId === lead.id
                    ? "rgba(59, 130, 246, 0.08)"
                    : "rgba(15, 23, 42, 0.02)",
                cursor: "grab",
              }}
            >
              <Stack gap={4}>
                <Text fw={600} size="sm" lineClamp={2}>
                  {lead.title}
                </Text>
                <Text size="xs" c="dimmed">
                  Источник: {lead.source || "—"}
                </Text>
                <Group gap={6} wrap="wrap">
                  <Badge size="xs" variant="light">
                    Оценка: {lead.estimated_value} ₽
                  </Badge>
                  <Badge size="xs" variant="light" color="green">
                    Факт: {lead.actual_value} ₽
                  </Badge>
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
                    {lead.status}
                  </Badge>
                </Group>
                <Group gap={4} justify="space-between">
                  <Text size="xs" c="dimmed">
                    Создан: {new Date(lead.created_at).toLocaleDateString()}
                  </Text>
                </Group>
              </Stack>
            </Box>
          </DraggableLeadCard>
        ))}
      </Stack>
    </Stack>
  );
}

export default function AdminSalesPipelinePage() {
  const [searchParams] = useSearchParams();
  const initialLeadId = searchParams.get("lead_id");
  const [selectedPipelineId, setSelectedPipelineId] = useState<string | null>(null);
  const [selectedStageId, setSelectedStageId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [selectedLeadId, setSelectedLeadId] = useState<string | null>(
    initialLeadId
  );
  const [noteText, setNoteText] = useState("");

  const { data: pipelines, isLoading: pipelinesLoading } = useCrmPipelines();
  const { data: stages, isLoading: stagesLoading } = useCrmStages(selectedPipelineId);

  const { data: leadsResponse } = useCrmLeads({
    stage_id: selectedStageId || undefined,
    status: statusFilter || undefined,
    search: search || undefined,
    page: 1,
    page_size: 200,
  });

  const { data: leadDetails, isLoading: leadDetailsLoading } = useCrmLeadDetails(
    selectedLeadId
  );
  const createNote = useCreateLeadNote();
  const updateLeadStage = useUpdateLeadStage();

  const pipelineOptions =
    pipelines?.map((p) => ({
      value: p.id,
      label: p.name + (p.is_default ? " (по умолчанию)" : ""),
    })) ?? [];

  const stageOptions =
    stages?.map((s) => ({
      value: s.id,
      label: s.name,
    })) ?? [];

  const leads = leadsResponse?.items ?? [];

  const leadsByStage = useMemo(() => {
    const map: Record<string, LeadCard[]> = {};
    for (const lead of leads) {
      const key = lead.stage_id;
      if (!map[key]) map[key] = [];
      map[key].push(lead);
    }
    return map;
  }, [leads]);

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
    if (!over || typeof over.id !== "string") return;
    const overId = String(over.id);
    if (!overId.startsWith(STAGE_DROPPABLE_PREFIX)) return;
    const newStageId = overId.slice(STAGE_DROPPABLE_PREFIX.length);
    const leadId = String(active.id);
    const lead = leads.find((l) => l.id === leadId);
    if (!lead || lead.stage_id === newStageId) return;
    updateLeadStage.mutate({ leadId, newStageId });
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
    // we intentionally ignore deps like selectedPipelineId to avoid infinite loops
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [leadDetails, initialLeadId]);

  if (pipelinesLoading) {
    return (
      <Stack>
        <Title order={3}>CRM‑воронка продаж</Title>
        <DataSkeleton lines={4} />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Title order={3}>CRM‑воронка продаж</Title>
      <ThreeColumnLayout
        preset="wide-center"
        left={
          <Stack gap="sm" p="xs">
            <Text size="sm" fw={500}>
              Фильтры и выбор воронки
            </Text>
            <Select
              label="Pipeline"
              placeholder="Выберите воронку"
              data={pipelineOptions}
              value={selectedPipelineId}
              onChange={(v) => {
                setSelectedPipelineId(v);
                setSelectedStageId(null);
              }}
              styles={{ label: { fontSize: 12 } }}
            />
            <Select
              label="Стадия"
              placeholder="Все стадии"
              data={stageOptions}
              value={selectedStageId}
              onChange={setSelectedStageId}
              disabled={!stages?.length}
              styles={{ label: { fontSize: 12 } }}
            />
            <Select
              label="Статус"
              placeholder="Все статусы"
              value={statusFilter}
              onChange={setStatusFilter}
              data={[
                { value: "open", label: "Открытые" },
                { value: "success", label: "Успех" },
                { value: "lost", label: "Потеряно" },
              ]}
              styles={{ label: { fontSize: 12 } }}
            />
            <TextInput
              label="Поиск"
              placeholder="Имя/комментарий/источник"
              value={search}
              onChange={(e) => setSearch(e.currentTarget.value)}
              styles={{ label: { fontSize: 12 } }}
            />
          </Stack>
        }
        center={
          <Paper p="sm" radius="md" withBorder>
            {stagesLoading ? (
              <DataSkeleton lines={4} />
            ) : !stages || !stages.length ? (
              <EmptyStateHint
                title="Стадии не настроены"
                subtitle="Обратитесь к владельцу, чтобы настроить воронку продаж."
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
                        <KanbanColumn
                          stage={stage}
                          leads={leadsByStage[stage.id] ?? []}
                          onSelectLead={setSelectedLeadId}
                          selectedLeadId={selectedLeadId}
                        />
                      </Box>
                    ))}
                  </Flex>
                </DndContext>
              </ScrollArea>
            )}
          </Paper>
        }
        right={
          <Paper p="md" radius="md" withBorder>
            {!selectedLeadId ? (
              <EmptyStateHint
                title="Выберите лид"
                subtitle="Кликните по карточке лида в Kanban‑доске, чтобы увидеть детали."
              />
            ) : leadDetailsLoading ? (
              <DataSkeleton lines={4} />
            ) : !leadDetails ? (
              <EmptyStateHint
                title="Лид не найден"
                subtitle="Возможно, он был изменён или удалён."
              />
            ) : (
              <Stack gap="sm">
                <Stack gap={2}>
                  <Group justify="space-between" align="flex-start">
                    <Stack gap={2}>
                      <Text fw={700}>{leadDetails.lead.title}</Text>
                      <Text size="sm" c="dimmed">
                        Источник: {leadDetails.lead.source || "—"}
                      </Text>
                    </Stack>
                    <Stack gap={4} align="flex-end">
                      <Badge size="sm" variant="outline">
                        {leadDetails.lead.status}
                      </Badge>
                      <Text size="xs" c="dimmed">
                        Создан:{" "}
                        {new Date(leadDetails.lead.created_at).toLocaleString()}
                      </Text>
                    </Stack>
                  </Group>
                  <Group gap="xs">
                    <Badge size="sm" variant="light">
                      Оценка: {leadDetails.lead.estimated_value} ₽
                    </Badge>
                    <Badge size="sm" variant="light" color="green">
                      Факт: {leadDetails.lead.actual_value} ₽
                    </Badge>
                  </Group>
                </Stack>

                <Stack gap={4}>
                  <Text fw={600} size="sm">
                    Заметки
                  </Text>
                  <ScrollArea h={160} type="scroll">
                    {leadDetails.notes.length === 0 ? (
                      <Text size="xs" c="dimmed">
                        Пока нет заметок.
                      </Text>
                    ) : (
                      <Stack gap="xs">
                        {leadDetails.notes.map((note) => (
                          <Box
                            key={note.id}
                            p="xs"
                            style={{
                              borderRadius: 8,
                              background: "rgba(15, 23, 42, 0.02)",
                              border: "1px solid rgba(148, 163, 184, 0.4)",
                            }}
                          >
                            <Text size="sm">{note.text}</Text>
                            <Text size="xs" c="dimmed">
                              {new Date(note.created_at).toLocaleString()}
                            </Text>
                          </Box>
                        ))}
                      </Stack>
                    )}
                  </ScrollArea>
                  <Textarea
                    placeholder="Добавить заметку..."
                    minRows={2}
                    value={noteText}
                    onChange={(e) => setNoteText(e.currentTarget.value)}
                  />
                  <Group justify="flex-end">
                    <Button
                      size="xs"
                      onClick={handleAddNote}
                      loading={createNote.isPending}
                    >
                      Сохранить заметку
                    </Button>
                  </Group>
                </Stack>
              </Stack>
            )}
          </Paper>
        }
      />
    </Stack>
  );
}

