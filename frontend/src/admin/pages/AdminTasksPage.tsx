import { useState, useMemo } from "react";
import {
  ActionIcon,
  Badge,
  Button,
  Card,
  Group,
  HoverCard,
  Loader,
  Menu,
  ScrollArea,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Select,
  MultiSelect,
  SegmentedControl,
  Box,
  Paper,
} from "@mantine/core";
import {
  IconDotsVertical,
  IconRobot,
  IconMessageCircle,
  IconMessages,
  IconCalendarEvent,
  IconPhone,
  IconBrandWhatsapp,
} from "@tabler/icons-react";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import { AdminDrawer } from "@/shared/ui";
import { ContextBar } from "@/shared/ui/ContextBar";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { EmptyState } from "@/shared/ui/EmptyState";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { usePatients } from "@/hooks/usePatients";
import {
  useAdminAdmins,
  useAdminTasksList,
  useAdminTasksMyFocus,
  useAdminTasksAi,
  useCreateAdminTaskMutation,
  useClaimAdminTaskMutation,
  useUpdateAdminTaskStatusMutation,
  useTaskComments,
  usePostTaskComment,
} from "@/hooks";
import type { AdminTaskRow, AdminUserRow } from "@/hooks";
import { getAdminId } from "@/api/client";
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

const STATUS_COLUMNS = [
  { id: "open", label: "Открыты" },
  { id: "in_progress", label: "В работе" },
  { id: "done", label: "Выполнены" },
];

const TIME_BOMB_HOURS = 2;

/** Имена личных исполнителей: assignee_ids или legacy assignee_id. */
function taskAssigneeIdList(task: AdminTaskRow): string[] {
  if (task.assignee_ids && task.assignee_ids.length > 0) return task.assignee_ids;
  if (task.assignee_id) return [task.assignee_id];
  return [];
}

function formatTaskAssigneeLine(task: AdminTaskRow, admins: AdminUserRow[]): string {
  const ids = taskAssigneeIdList(task);
  if (ids.length === 0) return "";
  return ids
    .map((id) => {
      const a = admins.find((x) => x.id === id);
      return a?.full_name || a?.email || id.slice(0, 8);
    })
    .join(", ");
}

function isTimeBomb(dueAt: string | null): boolean {
  if (!dueAt) return false;
  const due = dayjs(dueAt);
  const now = dayjs();
  return due.isBefore(now) || due.diff(now, "hour", true) <= TIME_BOMB_HOURS;
}

function TaskKanbanCard({
  task,
  admins,
  isTimeBombActive,
  onClaim,
  onTaskChat,
  isAi,
  patientPhone,
}: {
  task: AdminTaskRow;
  admins: AdminUserRow[];
  isTimeBombActive: boolean;
  onClaim?: (taskId: string) => void;
  onTaskChat?: (taskId: string) => void;
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
  const assigneeLine = formatTaskAssigneeLine(task, admins);
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
        {assigneeLine ? (
          <Text size="xs" c="dimmed" lineClamp={2}>
            {assigneeLine}
          </Text>
        ) : task.role_assignee && taskAssigneeIdList(task).length === 0 ? (
          <Text size="xs" c="dimmed">
            Очередь роли: {task.role_assignee}
          </Text>
        ) : null}
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
          <Button
            component={Link}
            to={`${ROUTE_PATHS.admin.staffCalendar}?task_id=${task.id}&open_create=1`}
            variant="subtle"
            size="compact-xs"
            title="Добавить событие в календарь, привязав к задаче"
            leftSection={<IconCalendarEvent size={10} />}
            onClick={(e) => e.stopPropagation()}
          >
            В календарь
          </Button>
        </Group>
        {onTaskChat && (
          <Button
            size="xs"
            variant="light"
            color="gray"
            leftSection={<IconMessages size={12} />}
            onClick={(e) => {
              e.stopPropagation();
              onTaskChat(task.id);
            }}
          >
            Чат задачи
          </Button>
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
  const [viewMode, setViewMode] = useState<"table" | "kanban">("table");
  const [taskChatId, setTaskChatId] = useState<string | null>(null);
  const [taskChatDraft, setTaskChatDraft] = useState("");
  const { data: taskComments = [], isLoading: taskCommentsLoading } = useTaskComments(taskChatId);
  const postTaskComment = usePostTaskComment(taskChatId);
  const [createOpened, setCreateOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<string | null>("medium");
  const [assigneeIds, setAssigneeIds] = useState<string[]>([]);
  const [dueDate, setDueDate] = useState("");

  const currentAdminId = getAdminId();
  const { data: tasks = [], isLoading } = useAdminTasksList();
  const taskChatTitle = useMemo(() => {
    if (!taskChatId) return "";
    return tasks.find((t) => t.id === taskChatId)?.title ?? "";
  }, [taskChatId, tasks]);
  const { data: myFocusTasks = [] } = useAdminTasksMyFocus(currentAdminId);
  const { data: aiTasks = [] } = useAdminTasksAi();
  const { data: admins = [] } = useAdminAdmins();
  const { data: patientsList = [] } = usePatients({ clinic_id: currentClinicId ?? undefined, limit: 500 });
  const patientIdToPhone = useMemo(() => {
    const m = new Map<string, string>();
    patientsList.forEach((p) => {
      if (p.phone) m.set(p.id, p.phone);
    });
    return m;
  }, [patientsList]);

  const createTaskMutation = useCreateAdminTaskMutation();
  const claimMutation = useClaimAdminTaskMutation();
  const updateStatusMutation = useUpdateAdminTaskStatusMutation();

  const handleCreate = () => {
    if (!title.trim()) return;
    if (assigneeIds.length === 0 || !dueDate) return;
    createTaskMutation.mutate(
      {
        title: title.trim(),
        description: description.trim() || null,
        priority: priority ?? "medium",
        assignee_ids: assigneeIds,
        due_at: dueDate ? new Date(dueDate).toISOString() : null,
      },
      {
        onSuccess: () => {
          setCreateOpened(false);
          setTitle("");
          setDescription("");
          setPriority("medium");
          setAssigneeIds([]);
          setDueDate("");
        },
      }
    );
  };

  const adminOptions = admins.map((a) => ({
    value: a.id,
    label: a.full_name || a.email || a.id.slice(0, 8),
  }));

  const tasksByStatus = (list: AdminTaskRow[]) => {
    const m: Record<string, AdminTaskRow[]> = { open: [], in_progress: [], done: [] };
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
                        admins={admins}
                        isTimeBombActive={isTimeBomb(t.due_at)}
                        onClaim={(t.source === "ai_suggested" || t.source === "ai_auto") ? (id) => claimMutation.mutate(id) : undefined}
                        onTaskChat={setTaskChatId}
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
                    admins={admins}
                    isTimeBombActive={isTimeBomb(t.due_at)}
                    onClaim={(id) => claimMutation.mutate(id)}
                    onTaskChat={setTaskChatId}
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
                      <Table.Th>Источник</Table.Th>
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
                        <Badge size="sm" variant="outline">
                          {t.attention_kind
                            ? "from Attention"
                            : t.source === "ai_suggested" || t.source === "ai_auto"
                              ? "from AI"
                              : t.source === "system"
                                ? "system"
                                : "manual"}
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
                          {formatTaskAssigneeLine(t, admins) ? (
                            <HoverCard openDelay={300} width={260} shadow="md">
                              <HoverCard.Target>
                                <Text size="xs" span style={{ cursor: "default" }} lineClamp={2}>
                                  {formatTaskAssigneeLine(t, admins)}
                                </Text>
                              </HoverCard.Target>
                              <HoverCard.Dropdown>
                                <Stack gap={4}>
                                  {taskAssigneeIdList(t).map((id) => (
                                    <Text key={id} size="sm" fw={500}>
                                      {admins.find((a) => a.id === id)?.full_name ||
                                        admins.find((a) => a.id === id)?.email ||
                                        id.slice(0, 8)}
                                    </Text>
                                  ))}
                                  <Text size="xs" c="dimmed">
                                    Срок: {t.due_at ? dayjs(t.due_at).format("DD.MM.YYYY HH:mm") : "—"}
                                  </Text>
                                </Stack>
                              </HoverCard.Dropdown>
                            </HoverCard>
                          ) : t.role_assignee ? (
                            <Badge size="xs" variant="outline" title="Очередь по роли (без личного исполнителя)">
                              {t.role_assignee}
                            </Badge>
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
                            <Button
                              variant="subtle"
                              size="compact-xs"
                              title="Чат задачи (команда)"
                              leftSection={<IconMessages size={12} />}
                              onClick={() => setTaskChatId(t.id)}
                            >
                              Чат задачи
                            </Button>
                            <Button
                              component={Link}
                              to={`${ROUTE_PATHS.admin.staffCalendar}?task_id=${t.id}&open_create=1`}
                              variant="subtle"
                              size="compact-xs"
                              title="Создать событие в календаре, привязанное к задаче"
                              leftSection={<IconCalendarEvent size={12} />}
                            >
                              Календарь
                            </Button>
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
                        admins={admins}
                        isTimeBomb={isTimeBomb}
                        onClaim={(id) => claimMutation.mutate(id)}
                        onTaskChat={setTaskChatId}
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

      <AdminDrawer
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
          <MultiSelect
            label="Исполнители"
            placeholder="Выберите одного или нескольких"
            data={adminOptions}
            value={assigneeIds}
            onChange={setAssigneeIds}
            required
            searchable
            hidePickedOptions
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
              disabled={!title.trim() || assigneeIds.length === 0 || !dueDate}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>

      <AdminDrawer
        position="right"
        size="md"
        opened={!!taskChatId}
        onClose={() => {
          setTaskChatId(null);
          setTaskChatDraft("");
        }}
        title={taskChatTitle ? `Чат задачи: ${taskChatTitle}` : "Чат задачи"}
      >
        <Stack gap="sm" style={{ minHeight: 280 }}>
          {taskCommentsLoading ? (
            <Loader size="sm" />
          ) : (
            <ScrollArea h={320} offsetScrollbars>
              <Stack gap="xs">
                {taskComments.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    Пока нет сообщений. Напишите коллегам в контексте этой задачи.
                  </Text>
                ) : (
                  taskComments.map((c) => (
                    <Paper key={c.id} p="xs" withBorder>
                      <Text size="xs" c="dimmed" mb={4}>
                        {c.author_full_name || "Сотрудник"} ·{" "}
                        {dayjs(c.created_at).format("DD.MM.YYYY HH:mm")}
                      </Text>
                      <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        {c.text}
                      </Text>
                    </Paper>
                  ))
                )}
              </Stack>
            </ScrollArea>
          )}
          {taskChatId ? (
            <Button
              component={Link}
              to={`/admin/staff-chat?task=${taskChatId}`}
              variant="light"
              size="xs"
            >
              Открыть thread в мессенджере персонала
            </Button>
          ) : null}
          <Textarea
            label="Сообщение"
            placeholder="Текст для команды…"
            minRows={3}
            value={taskChatDraft}
            onChange={(e) => setTaskChatDraft(e.currentTarget.value)}
          />
          <Group justify="flex-end">
            <Button
              onClick={() => {
                const text = taskChatDraft.trim();
                if (!text || !taskChatId) return;
                postTaskComment.mutate(text, {
                  onSuccess: () => setTaskChatDraft(""),
                });
              }}
              loading={postTaskComment.isPending}
              disabled={!taskChatDraft.trim()}
            >
              Отправить
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>
    </Stack>
  );
}

function KanbanColumn({
  id,
  title,
  tasks,
  admins,
  isTimeBomb,
  onClaim,
  onTaskChat,
  patientIdToPhone,
}: {
  id: string;
  title: string;
  tasks: AdminTaskRow[];
  admins: AdminUserRow[];
  isTimeBomb: (due: string | null) => boolean;
  onClaim: (taskId: string) => void;
  onTaskChat?: (taskId: string) => void;
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
            admins={admins}
            isTimeBombActive={isTimeBomb(t.due_at)}
            onClaim={(t.source === "ai_suggested" || t.source === "ai_auto") ? onClaim : undefined}
            onTaskChat={onTaskChat}
            isAi={t.source === "ai_suggested" || t.source === "ai_auto"}
            patientPhone={t.patient_id ? patientIdToPhone.get(t.patient_id) ?? null : null}
          />
        ))}
      </Stack>
    </Stack>
  );
}