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
} from "@mantine/core";
import { ContextBar, EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { useAdminSession } from "@/hooks/useAdminSession";
import { useAdminAdmins } from "@/hooks/useAdminAdmins";
import {
  useAddStaffFeedComment,
  useCreateStaffFeedPost,
  useStaffFeedComments,
  useStaffFeedPostAckStatus,
  useStaffFeedPosts,
  useToggleStaffFeedPostLike,
} from "@/hooks/useStaffCollab";
import { AppleEmojiRichText } from "@/shared/AppleEmojiRichText";

function canPublish(session: { roles: string[]; permissions: string[] } | undefined) {
  if (!session) return false;
  if (session.permissions.includes("manage_staff_collab")) return true;
  return !session.roles.includes("doctor");
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
  const options = comments.map((c) => ({
    value: c.id,
    label: c.author.full_name?.trim() || "Сотрудник",
  }));
  return (
    <Stack gap={6}>
      {comments.map((c) => (
        <Card key={c.id} withBorder padding="xs">
          <Text size="xs" c="dimmed">
            {c.author.full_name || "Сотрудник"}
          </Text>
          <Text size="sm">
            <AppleEmojiRichText text={c.body} />
          </Text>
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
  const { data, isLoading, isError, error } = useStaffFeedPosts(50);
  const { data: session } = useAdminSession();
  const { data: admins = [] } = useAdminAdmins();
  const createMut = useCreateStaffFeedPost();
  const ackMut = useToggleStaffFeedPostLike();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [audienceRoles, setAudienceRoles] = useState<string[]>([]);
  const [audienceAdmins, setAudienceAdmins] = useState<string[]>([]);
  const [priority, setPriority] = useState<"normal" | "priority" | "critical">("normal");
  const [ackStatusPostId, setAckStatusPostId] = useState<string | null>(null);
  const { data: ackStatus } = useStaffFeedPostAckStatus(ackStatusPostId);

  const posts = useMemo(() => (data ?? []).filter((p) => p.is_announcement), [data]);
  const allowCreate = canPublish(session);

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
            <Text size="sm" c="dimmed">
              Публикация объявления для всех или выбранных сотрудников.
            </Text>
            <Textarea placeholder="Заголовок" minRows={1} value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
            <Textarea placeholder="Текст объявления" minRows={3} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
            <Group grow>
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
              />
              <MultiSelect
                label="Индивидуально"
                data={admins.map((a) => ({ value: a.id, label: a.full_name?.trim() || a.email }))}
                value={audienceAdmins}
                onChange={setAudienceAdmins}
                placeholder="Дополнительно"
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
              />
            </Group>
            <Group justify="flex-end">
              <Button
                onClick={() => {
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
                }}
                loading={createMut.isPending}
              >
                Опубликовать
              </Button>
            </Group>
          </Stack>
        </Card>
      ) : null}

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
