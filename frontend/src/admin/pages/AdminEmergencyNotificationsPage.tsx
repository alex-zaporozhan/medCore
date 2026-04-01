import { useMemo, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  MultiSelect,
  Select,
  Stack,
  Text,
  Textarea,
  Divider,
  Alert,
  Collapse,
} from "@mantine/core";
import { ContextBar, EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { useAdminSession } from "@/hooks/useAdminSession";
import { useAdminAdmins } from "@/hooks/useAdminAdmins";
import {
  useAddStaffFeedComment,
  useCreateStaffFeedPost,
  useStaffFeedComments,
  useUpdateStaffFeedComment,
  useDeleteStaffFeedComment,
  useStaffFeedPostAckStatus,
  useStaffAnnouncements,
  useAckStaffFeedPost,
} from "@/hooks/useStaffCollab";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";
import { PersonNameLink } from "@/shared/ui";
import { ApiErrorWithCode, getAdminId } from "@/api/client";
import { ActionIcon, Menu } from "@mantine/core";
import { IconDots, IconTrash, IconEdit } from "@tabler/icons-react";

function canPublish(session: { roles: string[]; permissions: string[] } | undefined) {
  return Boolean(session);
}

function priorityColor(v?: string) {
  if (v === "critical") return "red";
  if (v === "priority") return "orange";
  return "gray";
}

function CommentList({ postId }: { postId: string }) {
  const { data: comments = [] } = useStaffFeedComments(postId);
  const [text, setText] = useState("");
  const [replyTo, setReplyTo] = useState<string | null>(null);
  const addMut = useAddStaffFeedComment(postId);
  const updateMut = useUpdateStaffFeedComment(postId);
  const deleteMut = useDeleteStaffFeedComment(postId);
  const { data: session } = useAdminSession();
  const myId = getAdminId();
  const canModerate =
    Boolean(session?.roles?.includes("owner")) ||
    Boolean(session?.permissions?.includes("staff.feed.comments.moderate"));
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  const options = comments.map((c) => ({
    value: c.id,
    label: c.author.full_name?.trim() || "Сотрудник",
  }));
  return (
    <Stack gap={6}>
      {err ? (
        <Alert color="red" title="Ошибка" onClose={() => setErr(null)} withCloseButton>
          {err}
        </Alert>
      ) : null}
      {comments.map((c) => (
        <Card key={c.id} withBorder padding="xs">
          <Group justify="space-between" align="flex-start" wrap="nowrap" gap="xs">
            <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
              <Text size="xs" c="dimmed">
                <PersonNameLink kind="staff" id={c.author.id} label={c.author.full_name} size="xs" />
              </Text>
              {c.deleted_at ? (
                <Text size="sm" c="dimmed" style={{ textDecoration: "line-through", whiteSpace: "pre-wrap" }}>
                  <AppleEmojiRichText text={c.body || "Удалено"} />
                </Text>
              ) : editingId === c.id ? (
                <Stack gap="xs">
                  <Textarea minRows={2} value={editText} onChange={(e) => setEditText(e.currentTarget.value)} />
                  <Group justify="flex-end" gap="xs">
                    <Button
                      size="xs"
                      variant="subtle"
                      onClick={() => {
                        setEditingId(null);
                        setEditText("");
                      }}
                      disabled={updateMut.isPending}
                    >
                      Отмена
                    </Button>
                    <Button
                      size="xs"
                      onClick={async () => {
                        if (!editText.trim()) return;
                        setErr(null);
                        try {
                          await updateMut.mutateAsync({ commentId: c.id, body: editText.trim() });
                          setEditingId(null);
                          setEditText("");
                        } catch (e) {
                          setErr(e instanceof ApiErrorWithCode ? e.message : "Не удалось сохранить комментарий");
                        }
                      }}
                      loading={updateMut.isPending}
                    >
                      Сохранить
                    </Button>
                  </Group>
                </Stack>
              ) : (
                <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                  <AppleEmojiRichText text={c.body} />
                </Text>
              )}
            </Stack>
            {!c.deleted_at && (c.author.id === myId || canModerate) ? (
              <Menu position="bottom-end" withinPortal>
                <Menu.Target>
                  <ActionIcon size="sm" variant="subtle" aria-label="Действия">
                    <IconDots size={16} />
                  </ActionIcon>
                </Menu.Target>
                <Menu.Dropdown>
                  {c.author.id === myId ? (
                    <Menu.Item
                      leftSection={<IconEdit size={14} />}
                      onClick={() => {
                        setErr(null);
                        setEditingId(c.id);
                        setEditText(c.body ?? "");
                      }}
                    >
                      Редактировать
                    </Menu.Item>
                  ) : null}
                  <Menu.Item
                    color="red"
                    leftSection={<IconTrash size={14} />}
                    disabled={deleteMut.isPending}
                    onClick={async () => {
                      const ok = window.confirm("Удалить комментарий?");
                      if (!ok) return;
                      setErr(null);
                      try {
                        await deleteMut.mutateAsync(c.id);
                      } catch (e) {
                        setErr(e instanceof ApiErrorWithCode ? e.message : "Не удалось удалить комментарий");
                      }
                    }}
                  >
                    Удалить
                  </Menu.Item>
                </Menu.Dropdown>
              </Menu>
            ) : null}
          </Group>
        </Card>
      ))}
      <Select
        placeholder="Ответить всем или конкретному"
        value={replyTo}
        onChange={setReplyTo}
        data={[{ value: "", label: "Ответить всем" }, ...options]}
      />
      <Textarea
        minRows={2}
        placeholder="Комментарий (текст + emoji)"
        value={text}
        onChange={(e) => setText(e.currentTarget.value)}
      />
      <Group justify="flex-end">
        <Button
          size="xs"
          onClick={() => {
            if (!text.trim()) return;
            addMut.mutate({
              body: text.trim(),
              parent_comment_id: replyTo ? replyTo : null,
            });
            setText("");
            setReplyTo(null);
          }}
          loading={addMut.isPending}
        >
          Отправить
        </Button>
      </Group>
    </Stack>
  );
}

export default function AdminEmergencyNotificationsPage() {
  const { data, isLoading, isError, error } = useStaffAnnouncements(50);
  const { data: session } = useAdminSession();
  const { data: admins = [] } = useAdminAdmins();
  const createMut = useCreateStaffFeedPost();
  const ackMut = useAckStaffFeedPost();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audienceRoles, setAudienceRoles] = useState<string[]>([]);
  const [audienceAdmins, setAudienceAdmins] = useState<string[]>([]);
  const [priority, setPriority] = useState<"normal" | "priority" | "critical">("normal");
  const [ackStatusPostId, setAckStatusPostId] = useState<string | null>(null);
  const { data: ackStatus } = useStaffFeedPostAckStatus(ackStatusPostId);

  const posts = useMemo(() => data ?? [], [data]);
  const allowCreate = canPublish(session);
  const [publishOpen, setPublishOpen] = useState(false);

  if (isLoading) {
    return (
      <Stack gap="md">
        <ContextBar title="Стена объявлений" />
        <PageSkeleton variant="table" rows={4} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack gap="md">
        <ContextBar title="Стена объявлений" />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <ContextBar title="Стена объявлений" />
      {allowCreate ? (
        <Card withBorder>
          <Stack gap="xs">
            <Group justify="space-between" align="center" wrap="wrap">
              <Stack gap={2}>
                <Text fw={600}>Публикация объявления</Text>
                <Text size="sm" c="dimmed">
                  По умолчанию объявление увидят все сотрудники. Можно ограничить аудиторию после нажатия «Опубликовать».
                </Text>
              </Stack>
              <Group gap="xs">
                {publishOpen ? (
                  <Button
                    variant="default"
                    onClick={() => setPublishOpen(false)}
                    disabled={createMut.isPending}
                  >
                    Отмена
                  </Button>
                ) : null}
                <Button
                  onClick={() => {
                    if (!publishOpen) {
                      setPublishOpen(true);
                      return;
                    }
                    if (!body.trim()) return;
                    createMut.mutate({
                      title: title.trim() || "Объявление",
                      body: body.trim(),
                      is_announcement: true,
                      requires_ack: true,
                      priority_level: priority,
                      audience_roles: audienceRoles,
                      audience_admin_ids: audienceAdmins,
                    });
                    setTitle("");
                    setBody("");
                    setAudienceRoles([]);
                    setAudienceAdmins([]);
                    setPriority("normal");
                    setPublishOpen(false);
                  }}
                  loading={createMut.isPending}
                  disabled={publishOpen ? !body.trim() : false}
                >
                  Опубликовать
                </Button>
              </Group>
            </Group>

            <Collapse in={publishOpen}>
              <Stack gap="xs" mt="sm">
                <Textarea
                  placeholder="Заголовок"
                  minRows={1}
                  value={title}
                  onChange={(e) => setTitle(e.currentTarget.value)}
                />
                <Textarea
                  placeholder="Текст объявления"
                  minRows={3}
                  value={body}
                  onChange={(e) => setBody(e.currentTarget.value)}
                />
                <Group grow align="flex-end">
                  <MultiSelect
                    label="По категориям персонала"
                    data={[
                      { value: "owner", label: "Владелец" },
                      { value: "manager", label: "Менеджер" },
                      { value: "admin", label: "Администратор" },
                      { value: "doctor", label: "Врач/мастер" },
                    ]}
                    value={audienceRoles}
                    onChange={setAudienceRoles}
                    placeholder="Пусто = всем"
                    searchable
                    hidePickedOptions
                    clearable
                    comboboxProps={{ withinPortal: true }}
                  />
                  <MultiSelect
                    label="Индивидуально"
                    data={admins.map((a) => ({ value: a.id, label: a.full_name?.trim() || a.email }))}
                    value={audienceAdmins}
                    onChange={setAudienceAdmins}
                    placeholder="Дополнительно"
                    searchable
                    hidePickedOptions
                    clearable
                    comboboxProps={{ withinPortal: true }}
                  />
                  <Select
                    label="Приоритет"
                    value={priority}
                    onChange={(v) => setPriority((v as "normal" | "priority" | "critical") || "normal")}
                    data={[
                      { value: "normal", label: "Обычный" },
                      { value: "priority", label: "Приоритет" },
                      { value: "critical", label: "Критично" },
                    ]}
                    comboboxProps={{ withinPortal: true }}
                  />
                </Group>
              </Stack>
            </Collapse>
          </Stack>
        </Card>
      ) : null}

      <Divider />
      {posts.length === 0 ? (
        <EmptyState title="Нет объявлений" description="Опубликованные рабочие объявления появятся здесь." />
      ) : (
        <Stack gap="sm">
          {posts.map((post) => (
            <Card key={post.id} withBorder style={!post.acknowledged_by_me ? { boxShadow: "0 0 0 2px rgba(250, 82, 82, 0.25)" } : undefined}>
              <Stack gap="xs">
                <Group justify="space-between" align="flex-start">
                  <Stack gap={2}>
                    <Text fw={600}>{post.title || "Объявление"}</Text>
                    <Text size="xs" c="dimmed">
                      {post.author.full_name || "Сотрудник"} · {new Date(post.created_at).toLocaleString()}
                    </Text>
                  </Stack>
                  <Group gap={6}>
                    <Badge color={priorityColor(post.priority_level)}>{post.priority_level || "normal"}</Badge>
                    <Badge variant="light">
                      {post.acknowledged_count ?? 0}/{post.audience_total ?? 0}
                    </Badge>
                  </Group>
                </Group>
                <Text size="sm">
                  <AppleEmojiRichText text={post.body} />
                </Text>
                <Group>
                  <Button
                    size="xs"
                    variant={post.acknowledged_by_me ? "subtle" : "filled"}
                    color={post.acknowledged_by_me ? "gray" : "red"}
                    onClick={() => ackMut.mutate(post.id)}
                    disabled={Boolean(post.acknowledged_by_me)}
                  >
                    Ознакомился
                  </Button>
                  <Button size="xs" variant="light" onClick={() => setAckStatusPostId(post.id)}>
                    Кто ознакомился
                  </Button>
                </Group>
                <CommentList postId={post.id} />
              </Stack>
            </Card>
          ))}
        </Stack>
      )}

      <Modal opened={Boolean(ackStatusPostId)} onClose={() => setAckStatusPostId(null)} title="Статус ознакомления" centered>
        <Stack gap="xs">
          <Text size="sm" fw={600}>Ознакомились</Text>
          {(ackStatus?.acknowledged ?? []).map((r) => (
            <Text key={r.admin_id} size="sm">
              {(r.admin_name || r.admin_id)} {r.acknowledged_at ? `· ${new Date(r.acknowledged_at).toLocaleString()}` : ""}
            </Text>
          ))}
          <Text size="sm" fw={600} mt="sm">Не ознакомились</Text>
          {(ackStatus?.pending ?? []).map((r) => (
            <Text key={r.admin_id} size="sm">{r.admin_name || r.admin_id}</Text>
          ))}
        </Stack>
      </Modal>
    </Stack>
  );
}
