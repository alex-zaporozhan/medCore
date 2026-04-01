import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Divider,
  Group,
  Input,
  Loader,
  MultiSelect,
  Paper,
  ScrollArea,
  Select,
  SimpleGrid,
  Stack,
  Text,
  Textarea,
  Tooltip,
} from "@mantine/core";
import {
  IconAlertTriangle,
  IconExternalLink,
  IconLock,
  IconLockOpen,
} from "@tabler/icons-react";
import dayjs from "dayjs";
import { useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { ApiErrorWithCode, getAdminId } from "@/api/client";
import {
  useAdminAdmins,
  useAdminSession,
  useAdminTaskDetails,
  useInviteTaskCalendarParticipants,
  usePatchAdminTaskAssigneesMutation,
  usePatchAdminTaskDueMutation,
  usePatchAdminTaskStreamTagsMutation,
  usePostTaskComment,
  useTaskCalendarContext,
  useTaskComments,
  useTaskStreamsQuery,
  useTaskTagsQuery,
  useTaskTransitions,
  useUpdateAdminTaskMetaMutation,
  useUpdateAdminTaskStatusMutation,
} from "@/hooks";
import { AppleEmojiOverlayTextarea } from "@/shared/ui/AppleEmojiOverlayTextarea";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { PersonNameLink } from "@/shared/ui/PersonNameLink";
import { priorityBadgeColor, taskStatusBadgeStyles, taskStatusCardSurface, taskStatusTextColors } from "@/shared/taskStatusSemantic";

const STATUS_META: Record<string, string> = {
  open: "Открыто",
  in_progress: "В работе",
  on_hold: "На паузе",
  review: "На проверке",
  done: "Выполнено",
  cancelled: "Отменено",
};

const PRIORITY_META: Record<string, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  urgent: "Срочно",
};

function taskAssigneeIdList(task: { assignee_ids?: string[]; assignee_id?: string | null }): string[] {
  if (task.assignee_ids && task.assignee_ids.length > 0) return task.assignee_ids;
  if (task.assignee_id) return [task.assignee_id];
  return [];
}

export function TaskDetailsView({
  taskId,
  mode,
  onClose,
}: {
  taskId: string;
  mode: "modal" | "page";
  onClose?: () => void;
}) {
  const { data: adminSession } = useAdminSession();
  const currentAdminId = useMemo(() => getAdminId(), []);
  const { data: admins = [] } = useAdminAdmins();
  const { data: taskStreams = [] } = useTaskStreamsQuery();
  const { data: taskTags = [] } = useTaskTagsQuery();
  const { data: task, isLoading: taskLoading } = useAdminTaskDetails(taskId);

  const { data: transitions = [] } = useTaskTransitions(taskId);
  useTaskCalendarContext(taskId);

  const { data: comments = [], isLoading: commentsLoading } = useTaskComments(taskId);
  const postComment = usePostTaskComment(taskId);

  const patchAssigneesMutation = usePatchAdminTaskAssigneesMutation();
  const patchStreamTagsMutation = usePatchAdminTaskStreamTagsMutation();
  const patchDueMutation = usePatchAdminTaskDueMutation();
  const updateMetaMutation = useUpdateAdminTaskMetaMutation();
  const updateStatusMutation = useUpdateAdminTaskStatusMutation();
  useInviteTaskCalendarParticipants(taskId, null);

  const canEditAssignees =
    adminSession?.permissions?.includes("manage_tasks") ||
    adminSession?.permissions?.includes("assign_tasks");
  const canManageBoards = Boolean(adminSession?.permissions?.includes("manage_tasks"));
  const canPatchTaskFields =
    Boolean(adminSession?.permissions?.includes("manage_tasks")) ||
    Boolean(adminSession?.permissions?.includes("assign_tasks")) ||
    Boolean(adminSession?.permissions?.includes("tasks.change_status"));

  const canEditDue = Boolean(adminSession?.permissions?.includes("manage_tasks")) || (task?.creator_id && task.creator_id === currentAdminId);

  const [apiError, setApiError] = useState<string | null>(null);

  const assigneeServerSig = useMemo(() => (task ? JSON.stringify([...taskAssigneeIdList(task)].sort()) : ""), [task]);
  const [assigneeDraft, setAssigneeDraft] = useState<string[]>([]);
  const [assigneeAuditComment, setAssigneeAuditComment] = useState(true);

  const [streamDraft, setStreamDraft] = useState<string | null>(null);
  const [tagDraft, setTagDraft] = useState<string[]>([]);

  const [dueDayIso, setDueDayIso] = useState<string>("");
  const [dueTimeStr, setDueTimeStr] = useState<string>("");

  const [blockedReasonDraft, setBlockedReasonDraft] = useState("");

  const [commentDraft, setCommentDraft] = useState("");
  const commentTextareaRef = useRef<HTMLTextAreaElement>(null);

  const adminOptions = useMemo(
    () =>
      admins
        .map((a) => ({ value: a.id, label: a.full_name || a.email || a.id }))
        .sort((a, b) => a.label.localeCompare(b.label)),
    [admins]
  );

  const streamOptions = useMemo(
    () => taskStreams.filter((s) => !s.is_archived).map((s) => ({ value: s.id, label: s.name })),
    [taskStreams]
  );

  useEffect(() => {
    if (!task) return;
    setAssigneeDraft(taskAssigneeIdList(task));
    setStreamDraft(task.stream_id);
    setTagDraft([...(task.tag_ids ?? [])]);
    setBlockedReasonDraft(task.blocked_reason ?? "");
    if (!task.due_at) {
      setDueDayIso("");
      setDueTimeStr("");
      return;
    }
    const d = dayjs(task.due_at);
    setDueDayIso(d.format("YYYY-MM-DD"));
    setDueTimeStr(d.format("HH:mm"));
  }, [task?.id, task?.due_at, task?.stream_id, task?.blocked_reason, assigneeServerSig]);

  const assigneeListUnchanged = useMemo(() => {
    if (!task) return true;
    const cur = JSON.stringify([...taskAssigneeIdList(task)].sort());
    const next = JSON.stringify([...assigneeDraft].sort());
    return cur === next;
  }, [task, assigneeDraft]);

  const contextUnchanged = useMemo(() => {
    if (!task) return true;
    const tagsEq =
      JSON.stringify([...(task.tag_ids ?? [])].sort()) === JSON.stringify([...tagDraft].sort());
    return task.stream_id === streamDraft && tagsEq;
  }, [task, streamDraft, tagDraft]);

  const dueUnchanged = useMemo(() => {
    if (!task) return true;
    const cur = task.due_at ? dayjs(task.due_at).format("YYYY-MM-DD HH:mm") : "";
    const next = dueDayIso && dueTimeStr ? `${dueDayIso} ${dueTimeStr}` : "";
    return cur === next;
  }, [task, dueDayIso, dueTimeStr]);

  if (taskLoading) return <Loader size="sm" />;
  if (!task) return <Alert color="red" icon={<IconAlertTriangle size={16} />}>Не удалось загрузить задачу</Alert>;

  const tc = taskStatusTextColors(task.status);

  return (
    <Stack gap="md">
      {apiError ? (
        <Alert color="red" variant="light" icon={<IconAlertTriangle size={16} />}>
          {apiError}
        </Alert>
      ) : null}

      <Group justify="space-between" align="center" wrap="wrap">
        <Group gap="xs" wrap="wrap">
          <Badge size="sm" variant="light" color={priorityBadgeColor(task.priority)} tt="uppercase">
            {PRIORITY_META[task.priority] ?? task.priority}
          </Badge>
          <Badge size="sm" variant="transparent" tt="uppercase" styles={taskStatusBadgeStyles(task.status)}>
            {STATUS_META[task.status] ?? task.status}
          </Badge>
          {task.blocked ? (
            <Tooltip
              label={task.blocked_reason?.trim() ? `Причина: ${task.blocked_reason}` : "Причина блокировки не указана"}
              withArrow
              multiline
              maw={320}
            >
              <Badge size="sm" color="red" variant="light" leftSection={<IconLock size={12} />}>
                Заблокировано
              </Badge>
            </Tooltip>
          ) : null}
        </Group>

        {mode === "modal" ? (
          <Button
            component={Link}
            to={`/admin/tasks/${task.id}`}
            target="_blank"
            variant="light"
            size="xs"
            leftSection={<IconExternalLink size={14} />}
          >
            Открыть в новой вкладке
          </Button>
        ) : null}
      </Group>

      <Paper p="md" style={{ ...taskStatusCardSurface(task.status), borderRadius: "var(--calendar-slot-radius)" }}>
        {task.description ? (
          <Text size="sm" style={{ whiteSpace: "pre-wrap", color: tc.title }}>
            {task.description}
          </Text>
        ) : (
          <Text size="sm" c="dimmed">
            Без описания
          </Text>
        )}
        <Text size="xs" mt="xs" style={{ color: tc.meta }}>
          Срок: {task.due_at ? dayjs(task.due_at).format("DD.MM.YYYY HH:mm") : "—"}
          {!canEditAssignees ? (
            <>
              {" "}
              · Исполнители:{" "}
              {(() => {
                const ids = taskAssigneeIdList(task);
                if (!ids.length) return task.role_assignee || "—";
                return ids.map((id, idx) => {
                  const a = admins.find((x) => x.id === id);
                  return (
                    <span key={id}>
                      <PersonNameLink kind="staff" id={id} label={a?.full_name || a?.email || null} size="xs" />
                      {idx < ids.length - 1 ? ", " : ""}
                    </span>
                  );
                });
              })()}
            </>
          ) : null}
        </Text>
      </Paper>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Stack gap="md">
          {canEditAssignees ? (
            <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
              <Stack gap="xs">
                <Text size="sm" fw={600}>Исполнители</Text>
                <MultiSelect
                  label="Назначение и делегирование"
                  description="Первый в списке — основной исполнитель."
                  placeholder="Выберите одного или нескольких"
                  data={adminOptions}
                  value={assigneeDraft}
                  onChange={setAssigneeDraft}
                  searchable
                  hidePickedOptions
                  clearable
                />
                <Checkbox
                  label="Добавить служебную запись в комментарии об изменении состава"
                  checked={assigneeAuditComment}
                  onChange={(e) => setAssigneeAuditComment(e.currentTarget.checked)}
                />
                <Group justify="flex-end">
                  <Button
                    size="xs"
                    variant="light"
                    onClick={() => task && setAssigneeDraft(taskAssigneeIdList(task))}
                    disabled={assigneeListUnchanged}
                  >
                    Сбросить
                  </Button>
                  <Button
                    size="xs"
                    loading={patchAssigneesMutation.isPending}
                    disabled={assigneeListUnchanged}
                    onClick={() => {
                      if (!task || assigneeListUnchanged) return;
                      setApiError(null);
                      patchAssigneesMutation.mutate(
                        { taskId: task.id, assignee_ids: assigneeDraft },
                        {
                          onSuccess: () => {
                            setApiError(null);
                            if (assigneeAuditComment) {
                              postComment.mutate("Системное событие: обновлён состав исполнителей.");
                            }
                          },
                          onError: (e) => {
                            setApiError(e instanceof ApiErrorWithCode ? e.message : "Не удалось сохранить исполнителей");
                          },
                        }
                      );
                    }}
                  >
                    Сохранить
                  </Button>
                </Group>
              </Stack>
            </Card>
          ) : null}

          {canManageBoards ? (
            <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
              <Stack gap="xs">
                <Text size="sm" fw={600}>Поток и теги</Text>
                <Select
                  label="Поток"
                  placeholder="Выберите поток"
                  data={streamOptions}
                  value={streamDraft}
                  onChange={(v) => setStreamDraft(v)}
                  searchable
                />
                <MultiSelect
                  label="Теги"
                  placeholder="Необязательно"
                  data={taskTags.map((t) => ({ value: t.id, label: t.name }))}
                  value={tagDraft}
                  onChange={setTagDraft}
                  searchable
                  clearable
                />
                <Group justify="flex-end">
                  <Button
                    size="xs"
                    variant="light"
                    disabled={contextUnchanged}
                    onClick={() => {
                      setStreamDraft(task.stream_id);
                      setTagDraft([...(task.tag_ids ?? [])]);
                    }}
                  >
                    Сбросить
                  </Button>
                  <Button
                    size="xs"
                    loading={patchStreamTagsMutation.isPending}
                    disabled={contextUnchanged || streamDraft === null}
                    onClick={() => {
                      if (!task || streamDraft === null || contextUnchanged) return;
                      setApiError(null);
                      patchStreamTagsMutation.mutate(
                        { taskId: task.id, stream_id: streamDraft, tag_ids: tagDraft },
                        {
                          onSuccess: () => setApiError(null),
                          onError: (e) => {
                            setApiError(e instanceof ApiErrorWithCode ? e.message : "Не удалось сохранить поток и теги");
                          },
                        }
                      );
                    }}
                  >
                    Сохранить
                  </Button>
                </Group>
              </Stack>
            </Card>
          ) : null}
        </Stack>

        <Stack gap="md">
          {canPatchTaskFields ? (
            <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
              <Stack gap="xs">
                <Text size="sm" fw={600}>Срок выполнения</Text>
                <Select
                  label="Статус"
                  placeholder="Выберите статус"
                  data={Object.entries(STATUS_META).map(([value, label]) => ({ value, label }))}
                  value={String(task.status)}
                  onChange={(v) => {
                    if (!v || v === task.status) return;
                    setApiError(null);
                    updateStatusMutation.mutate(
                      { taskId: task.id, status: v },
                      { onError: (e) => setApiError(e instanceof ApiErrorWithCode ? e.message : "Не удалось изменить статус") }
                    );
                  }}
                />
                <Group align="flex-end" gap="md" wrap="wrap">
                  <Input.Wrapper label="Дата">
                    <Input
                      type="date"
                      value={dueDayIso}
                      onChange={(e) => setDueDayIso(e.currentTarget.value)}
                      w={160}
                      disabled={!canEditDue}
                    />
                  </Input.Wrapper>
                  <Input.Wrapper label="Время">
                    <Input
                      type="time"
                      value={dueTimeStr}
                      onChange={(e) => setDueTimeStr(e.currentTarget.value)}
                      w={120}
                      disabled={!canEditDue}
                    />
                  </Input.Wrapper>
                </Group>
                <Group justify="flex-end">
                  <Button
                    size="xs"
                    variant="light"
                    loading={patchDueMutation.isPending}
                    onClick={() => {
                      setApiError(null);
                      patchDueMutation.mutate(
                        { taskId: task.id, due_at: null },
                        {
                          onError: (e) => setApiError(e instanceof ApiErrorWithCode ? e.message : "Не удалось очистить срок"),
                        }
                      );
                    }}
                    disabled={!canEditDue || !task.due_at}
                  >
                    Очистить
                  </Button>
                  <Button
                    size="xs"
                    loading={patchDueMutation.isPending}
                    onClick={() => {
                      if (!dueDayIso || !dueTimeStr) return;
                      const iso = `${dueDayIso}T${dueTimeStr}:00`;
                      setApiError(null);
                      patchDueMutation.mutate(
                        { taskId: task.id, due_at: iso },
                        {
                          onError: (e) => setApiError(e instanceof ApiErrorWithCode ? e.message : "Не удалось сохранить срок"),
                        }
                      );
                    }}
                    disabled={!canEditDue || dueUnchanged || !dueDayIso || !dueTimeStr}
                  >
                    Сохранить срок
                  </Button>
                </Group>
              </Stack>
            </Card>
          ) : null}

          {canPatchTaskFields ? (
            <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
              <Stack gap="xs">
                <Text size="sm" fw={600}>Статус и блокировка</Text>
                <Group gap="xs" wrap="wrap">
                  <Button
                    size="xs"
                    variant="light"
                    loading={updateStatusMutation.isPending}
                    onClick={() => updateStatusMutation.mutate({ taskId: task.id, status: "in_progress" })}
                  >
                    В работу
                  </Button>
                  <Button
                    size="xs"
                    variant="light"
                    loading={updateStatusMutation.isPending}
                    onClick={() => updateStatusMutation.mutate({ taskId: task.id, status: "review" })}
                  >
                    На проверку
                  </Button>
                  <Button
                    size="xs"
                    variant="light"
                    loading={updateStatusMutation.isPending}
                    onClick={() => updateStatusMutation.mutate({ taskId: task.id, status: "done" })}
                  >
                    Завершить
                  </Button>
                </Group>
                <Divider />
                <Textarea
                  label="Причина блокировки"
                  placeholder="Опционально"
                  value={blockedReasonDraft}
                  onChange={(e) => setBlockedReasonDraft(e.currentTarget.value)}
                  minRows={2}
                />
                <Group justify="space-between" wrap="wrap" gap="xs">
                  <Button
                    size="xs"
                    variant="light"
                    color={task.blocked ? "gray" : "red"}
                    leftSection={task.blocked ? <IconLockOpen size={12} /> : <IconLock size={12} />}
                    loading={updateMetaMutation.isPending}
                    onClick={() => {
                      setApiError(null);
                      updateMetaMutation.mutate(
                        { taskId: task.id, blocked: !task.blocked, blocked_reason: blockedReasonDraft.trim() || null },
                        {
                          onError: (e) => setApiError(e instanceof ApiErrorWithCode ? e.message : "Не удалось обновить блокировку"),
                        }
                      );
                    }}
                  >
                    {task.blocked ? "Разблокировать" : "Заблокировать"}
                  </Button>
                  <Button size="xs" variant="default" onClick={onClose} disabled={!onClose}>
                    Закрыть
                  </Button>
                </Group>
              </Stack>
            </Card>
          ) : null}
        </Stack>
      </SimpleGrid>

      <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
        <Stack gap="sm" style={{ minHeight: 240 }}>
          <Group justify="space-between" wrap="wrap" gap="xs">
            <Text size="sm" fw={600}>Комментарии</Text>
          </Group>

          {commentsLoading ? (
            <Loader size="sm" />
          ) : (
            <ScrollArea h={260} offsetScrollbars>
              <Stack gap="xs">
                {comments.length === 0 ? (
                  <Text size="sm" c="dimmed">Пока нет сообщений. Напишите коллегам в контексте этой задачи.</Text>
                ) : (
                  comments.map((c) => (
                    <Paper key={c.id} p="xs" withBorder>
                      <Text size="xs" c="dimmed" mb={4}>
                        {c.author_full_name || "Сотрудник"} · {dayjs(c.created_at).format("DD.MM.YYYY HH:mm")}
                      </Text>
                      <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        <AppleEmojiRichText text={c.text} />
                      </Text>
                    </Paper>
                  ))
                )}
              </Stack>
            </ScrollArea>
          )}

          <Input.Wrapper label="Сообщение">
            <AppleEmojiOverlayTextarea
              ref={commentTextareaRef}
              placeholder="Текст для команды…"
              minRows={3}
              value={commentDraft}
              onChange={(e) => setCommentDraft(e.currentTarget.value)}
            />
          </Input.Wrapper>
          <Group justify="flex-end" wrap="wrap" gap="xs">
            <Button
              size="xs"
              loading={postComment.isPending}
              disabled={!commentDraft.trim()}
              onClick={() => {
                const text = commentDraft.trim();
                if (!text) return;
                postComment.mutate(text, { onSuccess: () => setCommentDraft("") });
              }}
            >
              Отправить
            </Button>
          </Group>
        </Stack>
      </Card>

      <Card withBorder p="sm" style={{ borderColor: "var(--calendar-card-border)", boxShadow: "var(--calendar-card-shadow)" }}>
        <Stack gap="xs">
          <Text size="sm" fw={600}>История статусов</Text>
          {transitions.length === 0 ? (
            <Text size="sm" c="dimmed">Пока нет переходов.</Text>
          ) : (
            transitions.slice(0, 20).map((tr) => (
              <Text key={tr.id} size="xs" c="dimmed">
                {dayjs(tr.created_at).format("DD.MM HH:mm")} · {STATUS_META[tr.from_status] ?? tr.from_status} →{" "}
                {STATUS_META[tr.to_status] ?? tr.to_status}
              </Text>
            ))
          )}
        </Stack>
      </Card>
    </Stack>
  );
}

