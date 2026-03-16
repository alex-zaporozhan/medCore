import { useState, useMemo } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Drawer,
  Group,
  HoverCard,
  Menu,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Select,
  SegmentedControl,
  Box,
  Paper,
} from "@mantine/core";
import { IconDotsVertical, IconRobot, IconMessageCircle, IconCalendarEvent, IconPhone, IconBrandWhatsapp } from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { ContextBar } from "@/shared/ui/ContextBar";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { EmptyState } from "@/shared/ui/EmptyState";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { usePatients } from "@/hooks/usePatients";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import type { QueryKey } from "@tanstack/react-query";
import { api, getAdminId } from "@/api/client";
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

interface Task {
  id: string;
  clinic_id: string;
  title: string;
  description: string | null;
  status: string;
  priority: string;
  assignee_id: string | null;
  role_assignee: string | null;
  due_at: string | null;
  source?: string;
  created_at?: string;
  booking_id?: string | null;
  patient_id?: string | null;
  lead_id?: string | null;
}

interface AdminRead {
  id: string;
  clinic_id: string;
  email: string;
  full_name: string | null;
}

const STATUS_COLUMNS = [
  { id: "open", label: "Открыты" },
  { id: "in_progress", label: "В работе" },
  { id: "done", label: "Выполнены" },
];

const TIME_BOMB_HOURS = 2;

function isTimeBomb(dueAt: string | null): boolean {
  if (!dueAt) return false;
  const due = dayjs(dueAt);
  const now = dayjs();
  return due.isBefore(now) || due.diff(now, "hour", true) <= TIME_BOMB_HOURS;
}

function fetchTasks(params?: { source?: string; assignee_id?: string }) {
  const search = new URLSearchParams();
  if (params?.source) search.set("source", params.source);
  if (params?.assignee_id) search.set("assignee_id", params.assignee_id);
  const qs = search.toString();
  return api.get<Task[]>(`/v1/admin/tasks${qs ? `?${qs}` : ""}`);
}

function useAdmins() {
  return useQuery({
    queryKey: ["admin-admins"],
    queryFn: () => api.get<AdminRead[]>("/v1/admin/admins"),
  });
}

function TaskKanbanCard({
  task,
  isTimeBombActive,
  onClaim,
  isAi,
  patientPhone,
}: {
  task: Task;
  isTimeBombActive: boolean;
  onClaim?: (taskId: string) => void;
  isAi?: boolean;
  patientPhone?: string | null;
}) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: task.id,
  });
  const style = {
    transform: transform ? CSS.Translate.toString(transform) : undefined,
    opacity: isDragging ? 0.85 : 1,
  };
  return (
    <Paper
      ref={setNodeRef}
      style={{
        ...style,
        border: isTimeBombActive ? "2px solid var(--mantine-color-red-6)" : undefined,
        boxShadow: isTimeBombActive ? "0 0 12px rgba(228, 55, 55, 0.3)" : undefined,
      }}
      p="sm"
      radius="md"
      withBorder
      {...attributes}
      {...listeners}
    >
      <Stack gap={4}>
        <Group gap={4} wrap="nowrap">
          {isAi && <IconRobot size={14} color="var(--mantine-color-blue-6)" />}
          <Text size="sm" fw={600} lineClamp={2}>
            {task.title}
          </Text>
        </Group>
        <Group gap={4}>
          <Badge size="xs" variant="light" color={task.priority === "urgent" ? "red" : task.priority === "high" ? "orange" : "gray"}>
            {task.priority}
          </Badge>
          {task.due_at && (
            <Text size="xs" c={isTimeBombActive ? "red" : "dimmed"}>
              {dayjs(task.due_at).format("DD.MM HH:mm")}
            </Text>
          )}
        </Group>
        {(task.patient_id || task.booking_id) && (
          <Group gap={4} wrap="wrap">
            {task.patient_id && (
              <>
                <Button
                  component={Link}
                  to={`/admin/omni-chat?patient_id=${task.patient_id}`}
                  variant="subtle"
                  size="compact-xs"
                  onClick={(e) => e.stopPropagation()}
                  leftSection={<IconMessageCircle size={10} />}
                >
                  Чат
                </Button>
                {patientPhone && (
                  <>
                    <Button
                      component="a"
                      href={`tel:${patientPhone.replace(/\s/g, "")}`}
                      variant="subtle"
                      size="compact-xs"
                      onClick={(e) => e.stopPropagation()}
                      leftSection={<IconPhone size={10} />}
                      title="Позвонить"
                    >
                      Позвонить
                    </Button>
                    <Button
                      component="a"
                      href={`https://wa.me/${patientPhone.replace(/\D/g, "").replace(/^8/, "7")}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      variant="subtle"
                      size="compact-xs"
                      onClick={(e) => e.stopPropagation()}
                      leftSection={<IconBrandWhatsapp size={10} />}
                      title="Отправить ссылку в WhatsApp"
                    >
                      WhatsApp
                    </Button>
                  </>
                )}
              </>
            )}
            {task.booking_id && (
              <Button
                component={Link}
                to={`/admin/schedule?booking_id=${task.booking_id}`}
                variant="subtle"
                size="compact-xs"
                onClick={(e) => e.stopPropagation()}
                leftSection={<IconCalendarEvent size={10} />}
              >
                Запись
              </Button>
            )}
          </Group>
        )}
        {isAi && onClaim && (
          <Button size="xs" variant="light" onClick={(e) => { e.stopPropagation(); onClaim(task.id); }}>
            Принять в работу
          </Button>
        )}
      </Stack>
    </Paper>
  );
}

export default function AdminTasksPage() {
  const { currentClinicId } = useAdminClinic();
  const queryClient = useQueryClient();
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");
  const [createOpened, setCreateOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<string | null>("medium");
  const [assigneeId, setAssigneeId] = useState<string | null>(null);
  const [dueDate, setDueDate] = useState("");

  const currentAdminId = getAdminId();
  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ["admin-tasks"],
    queryFn: () => fetchTasks(),
  });
  const { data: myFocusTasks = [] } = useQuery({
    queryKey: ["admin-tasks", "my-focus", currentAdminId],
    queryFn: () => fetchTasks({ assignee_id: currentAdminId ?? undefined }),
    enabled: !!currentAdminId,
  });
  const { data: aiTasks = [] } = useQuery({
    queryKey: ["admin-tasks", "ai"],
    queryFn: () => fetchTasks({ source: "ai" }),
  });
  const { data: admins = [] } = useAdmins();
  const { data: patientsList = [] } = usePatients({ clinic_id: currentClinicId ?? undefined, limit: 500 });
  const patientIdToPhone = useMemo(() => {
    const m = new Map<string, string>();
    patientsList.forEach((p) => {
      if (p.phone) m.set(p.id, p.phone);
    });
    return m;
  }, [patientsList]);

  const createTaskMutation = useMutation({
    mutationFn: (payload: {
      title: string;
      description?: string | null;
      priority?: string;
      assignee_id: string | null;
      due_at: string | null;
    }) => api.post<Task>("/v1/admin/tasks", payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tasks"] });
      setCreateOpened(false);
      setTitle("");
      setDescription("");
      setPriority("medium");
      setAssigneeId(null);
      setDueDate("");
    },
  });

  const claimMutation = useMutation({
    mutationFn: (taskId: string) => api.post<Task>(`/v1/admin/tasks/${taskId}/claim`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tasks"] });
    },
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: string }) =>
      api.patch<Task>(`/v1/admin/tasks/${taskId}`, { status }),
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: ["admin-tasks"] });
      const previous: [QueryKey, Task[] | undefined][] = queryClient.getQueriesData(
        { queryKey: ["admin-tasks"] }
      );
      queryClient.setQueriesData<Task[]>(
        { queryKey: ["admin-tasks"] },
        (old) =>
          old?.map((t) =>
            t.id === variables.taskId ? { ...t, status: variables.status } : t
          ) ?? old
      );
      return { previous };
    },
    onError: (_err, _variables, context: { previous: [QueryKey, Task[] | undefined][] } | undefined) => {
      if (context?.previous) {
        context.previous.forEach(([key, data]) => queryClient.setQueryData(key, data));
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tasks"] });
    },
  });

  const handleCreate = () => {
    if (!title.trim()) return;
    if (!assigneeId || !dueDate) return;
    createTaskMutation.mutate({
      title: title.trim(),
      description: description.trim() || null,
      priority: priority ?? "medium",
      assignee_id: assigneeId,
      due_at: dueDate ? new Date(dueDate).toISOString() : null,
    });
  };

  const adminOptions = admins.map((a) => ({
    value: a.id,
    label: a.full_name || a.email || a.id.slice(0, 8),
  }));

  const tasksByStatus = (list: Task[]) => {
    const m: Record<string, Task[]> = { open: [], in_progress: [], done: [] };
    list.forEach((t) => {
      const key = t.status === "done" ? "done" : t.status === "in_progress" ? "in_progress" : "open";
      if (m[key]) m[key].push(t);
    });
    return m;
  };

  const handleKanbanDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || typeof over.id !== "string") return;
    const status = String(over.id).replace("droppable-", "");
    if (!STATUS_COLUMNS.some((c) => c.id === status)) return;
    const taskId = String(active.id);
    const task = tasks.find((t) => t.id === taskId);
    if (!task || task.status === status) return;
    updateStatusMutation.mutate({ taskId, status });
  };

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } })
  );

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Задачи" />
        <PageSkeleton variant="table" rows={6} />
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar
        title="Задачи"
        actions={
          <Group>
            <SegmentedControl
              size="xs"
              data={[
                { label: "Таблица", value: "table" },
                { label: "Канбан", value: "kanban" },
              ]}
              value={viewMode}
              onChange={(v) => setViewMode(v as "table" | "kanban")}
            />
            <Button size="sm" onClick={() => setCreateOpened(true)}>
              Новая задача
            </Button>
          </Group>
        }
      />

      <Group align="flex-start" wrap="nowrap">
        <Stack gap="sm" style={{ minWidth: 220 }}>
          <Text size="sm" fw={500}>
            Контекст
          </Text>
          {currentAdminId && (
            <Card withBorder p="sm">
              <Text size="xs" fw={600} c="dimmed" mb="xs">
                My Focus
              </Text>
              {myFocusTasks.length === 0 ? (
                <Text size="xs" c="dimmed">
                  Нет задач, назначенных на вас
                </Text>
              ) : (
                <Stack gap={4}>
                  {myFocusTasks
                    .filter((t) => t.status !== "done" && t.status !== "cancelled")
                    .sort((a, b) => (a.due_at && b.due_at ? new Date(a.due_at).getTime() - new Date(b.due_at).getTime() : 0))
                    .slice(0, 5)
                    .map((t) => (
                      <TaskKanbanCard
                        key={t.id}
                        task={t}
                        isTimeBombActive={isTimeBomb(t.due_at)}
                        onClaim={(t.source === "ai_suggested" || t.source === "ai_auto") ? (id) => claimMutation.mutate(id) : undefined}
                        isAi={t.source === "ai_suggested" || t.source === "ai_auto"}
                        patientPhone={t.patient_id ? patientIdToPhone.get(t.patient_id) : null}
                      />
                    ))}
                </Stack>
              )}
            </Card>
          )}
          <Card withBorder p="sm">
            <Text size="xs" fw={600} c="dimmed" mb="xs">
              Задачи от AI
            </Text>
            {aiTasks.length === 0 ? (
              <Text size="xs" c="dimmed">
                Нет предложенных задач
              </Text>
            ) : (
              <Stack gap={4}>
                {aiTasks.slice(0, 5).map((t) => (
                  <TaskKanbanCard
                    key={t.id}
                    task={t}
                    isTimeBombActive={isTimeBomb(t.due_at)}
                    onClaim={(id) => claimMutation.mutate(id)}
                    isAi
                    patientPhone={t.patient_id ? patientIdToPhone.get(t.patient_id) : null}
                  />
                ))}
              </Stack>
            )}
          </Card>
        </Stack>

        <Box style={{ flex: 1 }}>
          {viewMode === "table" && (
            <Card shadow="sm" padding="md" withBorder>
              {tasks.length === 0 ? (
                <EmptyState
                  title="Нет задач"
                  description="Создайте первую задачу или примите задачу от AI в работу."
                  action={{ label: "Создать задачу", onClick: () => setCreateOpened(true) }}
                />
              ) : (
                <Table highlightOnHover striped withColumnBorders verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Заголовок</Table.Th>
                      <Table.Th>Приоритет</Table.Th>
                      <Table.Th>Статус</Table.Th>
                      <Table.Th>Исполнитель</Table.Th>
                      <Table.Th>Срок</Table.Th>
                      <Table.Th w={50}></Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {tasks.map((t) => (
                      <Table.Tr key={t.id}>
                        <Table.Td>
                          <Group gap={4}>
                            {(t.source === "ai_suggested" || t.source === "ai_auto") && (
                              <IconRobot size={14} color="var(--mantine-color-blue-6)" />
                            )}
                            <Text size="sm">{t.title}</Text>
                          </Group>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            size="sm"
                            color={
                              t.priority === "urgent"
                                ? "red"
                                : t.priority === "high"
                                  ? "orange"
                                  : "gray"
                            }
                            variant="light"
                          >
                            {t.priority}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          <Badge
                            size="sm"
                            variant="outline"
                            color={
                              t.status === "done"
                                ? "green"
                                : t.status === "in_progress"
                                  ? "blue"
                                  : t.status === "cancelled"
                                    ? "red"
                                    : "gray"
                            }
                          >
                            {t.status}
                          </Badge>
                        </Table.Td>
                        <Table.Td>
                          {t.assignee_id ? (
                            <HoverCard openDelay={300} width={220} shadow="md">
                              <HoverCard.Target>
                                <Text size="xs" span style={{ cursor: "default" }}>
                                  {admins.find((a) => a.id === t.assignee_id)?.full_name ||
                                    admins.find((a) => a.id === t.assignee_id)?.email ||
                                    t.assignee_id.slice(0, 8)}
                                </Text>
                              </HoverCard.Target>
                              <HoverCard.Dropdown>
                                <Stack gap={4}>
                                  <Text size="sm" fw={500}>
                                    {admins.find((a) => a.id === t.assignee_id)?.full_name || "Исполнитель"}
                                  </Text>
                                  {admins.find((a) => a.id === t.assignee_id)?.email && (
                                    <Text size="xs" c="dimmed">
                                      {admins.find((a) => a.id === t.assignee_id)?.email}
                                    </Text>
                                  )}
                                  <Text size="xs" c="dimmed">
                                    Срок: {t.due_at ? dayjs(t.due_at).format("DD.MM.YYYY HH:mm") : "—"}
                                  </Text>
                                </Stack>
                              </HoverCard.Dropdown>
                            </HoverCard>
                          ) : (
                            <Text size="xs">—</Text>
                          )}
                        </Table.Td>
                        <Table.Td>
                          <Text
                            size="xs"
                            c={isTimeBomb(t.due_at) ? "red" : "dimmed"}
                          >
                            {t.due_at ? dayjs(t.due_at).format("DD.MM.YYYY HH:mm") : "—"}
                          </Text>
                        </Table.Td>
                        <Table.Td>
                          <Group gap={4} wrap="nowrap">
                            {t.patient_id && (
                              <Button
                                component={Link}
                                to={`/admin/omni-chat?patient_id=${t.patient_id}`}
                                variant="subtle"
                                size="compact-xs"
                                title="Открыть чат с клиентом"
                                leftSection={<IconMessageCircle size={12} />}
                              >
                                Чат
                              </Button>
                            )}
                            {t.booking_id && (
                              <Button
                                component={Link}
                                to={`/admin/schedule?booking_id=${t.booking_id}`}
                                variant="subtle"
                                size="compact-xs"
                                title="Открыть запись"
                                leftSection={<IconCalendarEvent size={12} />}
                              >
                                Запись
                              </Button>
                            )}
                            <Menu position="bottom-end">
                              <Menu.Target>
                                <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                                  <IconDotsVertical size={16} />
                                </ActionIcon>
                              </Menu.Target>
                              <Menu.Dropdown>
                                {t.patient_id && patientIdToPhone.get(t.patient_id) && (
                                  <>
                                    <Menu.Item
                                      component="a"
                                      href={`tel:${patientIdToPhone.get(t.patient_id)!.replace(/\s/g, "")}`}
                                      leftSection={<IconPhone size={14} />}
                                    >
                                      Позвонить
                                    </Menu.Item>
                                    <Menu.Item
                                      component="a"
                                      href={`https://wa.me/${patientIdToPhone.get(t.patient_id)!.replace(/\D/g, "").replace(/^8/, "7")}`}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      leftSection={<IconBrandWhatsapp size={14} />}
                                    >
                                      Отправить ссылку в WhatsApp
                                    </Menu.Item>
                                  </>
                                )}
                                <Menu.Item
                                  onClick={() => updateStatusMutation.mutate({ taskId: t.id, status: "in_progress" })}
                                >
                                  В работу
                                </Menu.Item>
                                <Menu.Item
                                  onClick={() => updateStatusMutation.mutate({ taskId: t.id, status: "done" })}
                                >
                                  Выполнено
                                </Menu.Item>
                                <Menu.Item
                                  color="red"
                                  onClick={() => updateStatusMutation.mutate({ taskId: t.id, status: "cancelled" })}
                                >
                                  Отменить
                                </Menu.Item>
                              </Menu.Dropdown>
                            </Menu>
                          </Group>
                        </Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          )}

          {viewMode === "kanban" && (
            <Card shadow="sm" padding="md" withBorder>
              <DndContext sensors={sensors} onDragEnd={handleKanbanDragEnd}>
                <Group align="flex-start" gap="md" wrap="nowrap">
                  {STATUS_COLUMNS.map((col) => {
                    const droppableId = `droppable-${col.id}`;
                    const columnTasks = tasksByStatus(tasks)[col.id] ?? [];
                    return (
                      <KanbanColumn
                        key={col.id}
                        id={droppableId}
                        title={col.label}
                        tasks={columnTasks}
                        isTimeBomb={isTimeBomb}
                        onClaim={(id) => claimMutation.mutate(id)}
                        patientIdToPhone={patientIdToPhone}
                      />
                    );
                  })}
                </Group>
              </DndContext>
            </Card>
          )}
        </Box>
      </Group>

      <Drawer
        position="right"
        size="md"
        opened={createOpened}
        onClose={() => setCreateOpened(false)}
        title="Новая задача"
      >
        <Stack>
          <TextInput
            label="Заголовок задачи"
            placeholder="Например: Перезвонить пациенту по отменённой записи"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
            required
          />
          <Textarea
            label="Описание"
            placeholder="Добавьте детали, ссылки, ID брони/лида и т.д."
            minRows={3}
            value={description}
            onChange={(e) => setDescription(e.currentTarget.value)}
          />
          <Select
            label="Приоритет"
            data={[
              { value: "low", label: "Низкий" },
              { value: "medium", label: "Средний" },
              { value: "high", label: "Высокий" },
              { value: "urgent", label: "Срочно" },
            ]}
            value={priority}
            onChange={setPriority}
          />
          <Select
            label="Исполнитель"
            placeholder="Выберите исполнителя"
            data={adminOptions}
            value={assigneeId}
            onChange={setAssigneeId}
            required
            searchable
          />
          <TextInput
            label="Срок"
            type="datetime-local"
            value={dueDate}
            onChange={(e) => setDueDate(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button
              onClick={handleCreate}
              loading={createTaskMutation.isPending}
              disabled={!title.trim() || !assigneeId || !dueDate}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </Drawer>
    </Stack>
  );
}

function KanbanColumn({
  id,
  title,
  tasks,
  isTimeBomb,
  onClaim,
  patientIdToPhone,
}: {
  id: string;
  title: string;
  tasks: Task[];
  isTimeBomb: (due: string | null) => boolean;
  onClaim: (taskId: string) => void;
  patientIdToPhone: Map<string, string>;
}) {
  const { isOver, setNodeRef } = useDroppable({ id });
  return (
    <Stack
      ref={setNodeRef}
      gap="xs"
      style={{
        minWidth: 260,
        minHeight: 200,
        padding: 8,
        borderRadius: 8,
        background: isOver ? "var(--mantine-color-blue-0)" : undefined,
        border: isOver ? "2px dashed var(--mantine-color-blue-6)" : undefined,
      }}
    >
      <Group justify="space-between">
        <Text size="sm" fw={600}>
          {title}
        </Text>
        <Badge size="sm" variant="light">
          {tasks.length}
        </Badge>
      </Group>
      <Stack gap="xs">
        {tasks.map((t) => (
          <TaskKanbanCard
            key={t.id}
            task={t}
            isTimeBombActive={isTimeBomb(t.due_at)}
            onClaim={(t.source === "ai_suggested" || t.source === "ai_auto") ? onClaim : undefined}
            isAi={t.source === "ai_suggested" || t.source === "ai_auto"}
            patientPhone={t.patient_id ? patientIdToPhone.get(t.patient_id) ?? null : null}
          />
        ))}
      </Stack>
    </Stack>
  );
}