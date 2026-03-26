import { useAdminReportsDashboardByClinics } from "@/hooks/useAdminReports";
import { useAttentionFeed } from "@/hooks/useAttentionFeed";
import {
  useCreateStaffFeedPost,
  useStaffFeedPosts,
  useToggleStaffFeedPostLike,
  useUpdateStaffFeedPost,
  useDeleteStaffFeedPost,
  downloadStaffFeedPostAttachmentFile,
  useStaffFeedComments,
  useAddStaffFeedComment,
} from "@/hooks/useStaffCollab";
import type { StaffAttachmentBrief, StaffFeedPostResponse } from "@/hooks/useStaffCollab";
import { api } from "@/api/client";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/queryKeys";
import { useRevenueHunterSaved, isRevenueHunterEnabled, useAdminSession } from "@/hooks";
import { PageSkeleton, EmptyState, ContextBar, QueryErrorAlert, GlassModal } from "@/shared/ui";
import {
  Card,
  Grid,
  Group,
  MultiSelect,
  Stack,
  Text,
  Button,
  ThemeIcon,
  Textarea,
  TextInput,
  Progress,
  Anchor,
  ActionIcon,
  Divider,
  Paper,
  Menu,
  Box,
} from "@mantine/core";
import { Link } from "react-router-dom";
import { useState, useMemo, useEffect, useRef } from "react";
import { ROUTE_PATHS } from "@/routePaths";
import { SEMANTIC } from "@/shared/semanticUi";
import type { AttentionFeed, AttentionItem } from "@/api/types";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  IconUsers,
  IconX,
  IconRobot,
  IconMail,
  IconSun,
  IconCalendarStats,
  IconClock,
  IconAlertTriangle,
  IconPaperclip,
  IconPhoto,
  IconMicrophone,
  IconHeart,
  IconMessageCircle,
  IconDots,
} from "@tabler/icons-react";

const BACKEND_HINT =
  "Если данные не загружаются, проверьте, что бэкенд запущен на порту 8000 (см. docs/RUN_SERVICES.md).";

function flattenAttentionFeed(
  data: AttentionFeed | undefined,
): AttentionItem[] {
  if (!data) return [];
  return [...data.follow_up, ...data.retention_gap, ...data.conflicts];
}

const metricCardShell = {
  bg: "white" as const,
  h: 95,
  styles: {
    root: {
      borderColor: "var(--mantine-color-gray-2)",
      height: 95,
      display: "flex" as const,
      flexDirection: "column" as const,
      justifyContent: "space-between" as const,
    },
  },
};

function parseHours(v: string | number | undefined): number {
  if (v === undefined || v === null) return 0;
  const n = typeof v === "number" ? v : Number.parseFloat(String(v));
  return Number.isFinite(n) ? n : 0;
}

function StaffFeedAttachmentPreview({ attachment }: { attachment: StaffAttachmentBrief }) {
  const [url, setUrl] = useState<string | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let objectUrl: string | null = null;
    setLoadFailed(false);
    async function run() {
      try {
        const blob = await api.getBlob(
          `/v1/admin/staff/feed/attachments/${attachment.id}/file`
        );
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch (e) {
        console.error("staff feed attachment preview failed", e);
        if (!cancelled) setLoadFailed(true);
      }
    }
    void run();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [attachment.id]);

  const ct = (attachment.content_type || "").toLowerCase();

  if (url && ct.startsWith("image/")) {
    return (
      <Box mt="md" mb="md">
        <img
          src={url}
          alt={attachment.file_name}
          style={{
            width: "100%",
            maxHeight: 320,
            objectFit: "contain",
            borderRadius: "var(--mantine-radius-md)",
          }}
        />
      </Box>
    );
  }

  if (url && ct.startsWith("audio/")) {
    return <audio controls src={url} style={{ width: "100%" }} />;
  }

  if (url && ct.startsWith("video/")) {
    return (
      <video
        controls
        src={url}
        style={{ width: "100%", maxHeight: 360, objectFit: "contain", borderRadius: 8 }}
      />
    );
  }

  if (loadFailed) {
    return (
      <Text size="xs" c="dimmed">
        Вложение недоступно
      </Text>
    );
  }

  return (
    <Anchor
      component="button"
      type="button"
      size="sm"
      onClick={() => void downloadStaffFeedPostAttachmentFile(attachment.id, attachment.file_name)}
      style={{ textAlign: "left", cursor: "pointer" }}
    >
      {attachment.file_name}
    </Anchor>
  );
}

function StaffFeedPostComments({
  postId,
  isOpen,
}: {
  postId: string;
  isOpen: boolean;
}) {
  const [body, setBody] = useState("");
  const { data: comments, isLoading } = useStaffFeedComments(isOpen ? postId : null);
  const addComment = useAddStaffFeedComment(postId);

  useEffect(() => {
    if (!isOpen) setBody("");
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <Stack gap="xs" mt="sm">
      <Text size="xs" fw={700} c="gray.9">
        Комментарии
      </Text>
      {isLoading ? (
        <Text size="xs" c="dimmed">
          Загрузка...
        </Text>
      ) : comments && comments.length ? (
        <Stack gap="xs">
          {comments.map((c) => (
            <Card key={c.id} padding="sm" radius="md" withBorder bg="white">
              <Text size="xs" c="dimmed">
                {c.author.full_name?.trim() || "Сотрудник"} · {new Date(c.created_at).toLocaleString()}
              </Text>
              <Text size="sm" style={{ whiteSpace: "pre-wrap" }} mt={4}>
                {c.body}
              </Text>
            </Card>
          ))}
        </Stack>
      ) : (
        <Text size="xs" c="dimmed">
          Пока комментариев нет
        </Text>
      )}

      <Textarea
        value={body}
        onChange={(e) => setBody(e.currentTarget.value)}
        minRows={2}
        placeholder="Ваш комментарий..."
      />
      <Group justify="flex-end">
        <Button
          size="xs"
          variant="filled"
          color="indigo"
          onClick={() => addComment.mutate(body)}
          disabled={!body.trim() || addComment.isPending}
          loading={addComment.isPending}
        >
          Отправить
        </Button>
      </Group>
    </Stack>
  );
}

export default function AdminDashboardPage() {
  const queryClient = useQueryClient();
  const { clinics, currentClinicId } = useAdminClinic();
  const [selectedClinicIds, setSelectedClinicIds] = useState<string[]>([]);
  const [feedTitle, setFeedTitle] = useState("");
  const [feedBody, setFeedBody] = useState("");
  const [feedFiles, setFeedFiles] = useState<File[]>([]);
  const [isComposerOpen, setIsComposerOpen] = useState(false);
  const feedFileRef = useRef<HTMLInputElement>(null);
  const toggleLike = useToggleStaffFeedPostLike();
  const updatePost = useUpdateStaffFeedPost();
  const deletePost = useDeleteStaffFeedPost();

  const [editingPost, setEditingPost] = useState<StaffFeedPostResponse | null>(null);
  const [editTitle, setEditTitle] = useState<string>("");
  const [editBody, setEditBody] = useState<string>("");
  const [editFile, setEditFile] = useState<File | null>(null);
  const [editFilePreviewUrl, setEditFilePreviewUrl] = useState<string | null>(null);
  const editFileRef = useRef<HTMLInputElement>(null);

  const [openCommentsByPostId, setOpenCommentsByPostId] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!editingPost) return;
    setEditTitle(editingPost.title ?? "");
    setEditBody(editingPost.body ?? "");
    setEditFile(null);
    setEditFilePreviewUrl(null);
  }, [editingPost?.id]);

  useEffect(() => {
    if (!editFile) {
      setEditFilePreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(editFile);
    setEditFilePreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [editFile]);
  const today = dayjs().format("YYYY-MM-DD");
  const dashboardClinicFilterInitialized = useRef(false);

  useEffect(() => {
    if (dashboardClinicFilterInitialized.current || !currentClinicId) return;
    dashboardClinicFilterInitialized.current = true;
    setSelectedClinicIds([currentClinicId]);
  }, [currentClinicId]);

  const clinicOptions = clinics.map((c) => ({ value: c.id, label: c.name }));

  const { data: reportData, isLoading: reportLoading, isError: reportError, error: reportErr } =
    useAdminReportsDashboardByClinics(
      today,
      "day",
      selectedClinicIds.length > 0 ? selectedClinicIds : null
    );

  const { data: attentionData } = useAttentionFeed(currentClinicId ?? null);
  const { data: staffPosts, isLoading: staffPostsLoading } = useStaffFeedPosts(20);
  const createPost = useCreateStaffFeedPost();
  const { data: revenueHunter } = useRevenueHunterSaved(currentClinicId ?? null);
  const { data: adminSession, isLoading: sessionLoading } = useAdminSession();
  const canPostToStaffFeed = adminSession?.permissions?.includes("manage_staff_collab") ?? false;
  /** Выручка на ленте: владелец или связка маркетинг+финансы (не линейный admin без finance). */
  const canViewRevenueDashboard =
    (adminSession?.roles?.includes("owner") ?? false) ||
    ((adminSession?.permissions?.includes("view_marketing_analytics") ?? false) &&
      (adminSession?.permissions?.includes("view_finance") ?? false));

  const attentionItems = useMemo(() => flattenAttentionFeed(attentionData), [attentionData]);
  const unreadAttentionCount = useMemo(
    () => attentionItems.filter((i) => i.status === "new").length,
    [attentionItems]
  );
  const hasUnreadAttention = unreadAttentionCount > 0;

  const isLoading = reportLoading;
  const isError = reportError;
  const error = reportErr;

  const publishPost = () => {
    const body = feedBody.trim();
    if (!body) return;
    const filesToUpload = [...feedFiles];
    createPost.mutate(
      { title: feedTitle.trim() || null, body },
      {
        onSuccess: async (post) => {
          setFeedTitle("");
          setFeedBody("");
          setFeedFiles([]);
          for (const f of filesToUpload) {
            try {
              const fd = new FormData();
              fd.append("file", f);
              await api.postFormData<unknown>(
                `/v1/admin/staff/feed/posts/${post.id}/attachments`,
                fd
              );
            } catch (e) {
              console.error("feed attachment upload", e);
            }
          }
          void queryClient.invalidateQueries({ queryKey: queryKeys.staffCollab.feedPosts() });
          setIsComposerOpen(false);
        },
      }
    );
  };

  if (isLoading) {
    return (
      <Stack gap="lg">
        <ContextBar title="Лента" />
        {clinics.length > 0 && (
          <MultiSelect
            label="Клиники"
            placeholder="Выберите одну или несколько клиник (пусто = все)"
            data={clinicOptions}
            value={selectedClinicIds}
            onChange={setSelectedClinicIds}
            searchable
            clearable
          />
        )}
        <Text size="sm" c="dimmed">
          {BACKEND_HINT}
        </Text>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <PageSkeleton variant="cards" cardsCount={1} />
          </Grid.Col>
        </Grid>
        <Grid>
          <Grid.Col span={{ base: 12, md: 7 }}>
            <PageSkeleton variant="table" rows={4} />
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 5 }}>
            <PageSkeleton variant="table" rows={6} />
          </Grid.Col>
        </Grid>
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack gap="lg">
        <ContextBar title="Лента" />
        {clinics.length > 0 && (
          <MultiSelect
            label="Клиники"
            placeholder="Выберите одну или несколько клиник (пусто = все)"
            data={clinicOptions}
            value={selectedClinicIds}
            onChange={setSelectedClinicIds}
            searchable
            clearable
          />
        )}
        <QueryErrorAlert error={error} />
        <Text size="sm" c="dimmed">
          {BACKEND_HINT}
        </Text>
      </Stack>
    );
  }

  const data = reportData;
  const emptyH = parseHours(data?.empty_slot_hours);
  const pulse = data?.day_pulse_score ?? 50;
  const requestsCount = data?.chat_writers_count ?? 0;

  return (
    <Stack gap="md">
      <ContextBar title="Лента" />

      <Group justify="space-between" align="center" wrap="wrap">
        <Button
          component={Link}
          to={ROUTE_PATHS.admin.attention}
          variant={hasUnreadAttention ? "filled" : "light"}
          color={hasUnreadAttention ? "orange" : "teal"}
          leftSection={<IconAlertTriangle size={18} />}
          className={hasUnreadAttention ? "admin-emergency-blink" : undefined}
        >
          Приоритетные сообщения
          {unreadAttentionCount > 0 ? ` (${unreadAttentionCount})` : ""}
        </Button>
      </Group>

      {clinics.length > 0 && (
        <MultiSelect
          label="Клиники"
          placeholder="Выберите одну или несколько клиник (пусто = все)"
          data={clinicOptions}
          value={selectedClinicIds}
          onChange={setSelectedClinicIds}
          searchable
          clearable
        />
      )}

      <Grid>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card padding="sm" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={2} wrap="nowrap">
              <ThemeIcon variant="light" color="teal" size="md" radius="md">
                <IconCalendarStats size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Всего посещений
              </Text>
            </Group>
            <Text fw={700} fz="lg" c="gray.9">
              {data?.bookings_completed ?? 0}
            </Text>
            <Text size="xs" c="dimmed" mt={0}>
              завершённые записи
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card padding="sm" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={2} wrap="nowrap">
              <ThemeIcon variant="light" color={SEMANTIC.metrics.patients} size="md" radius="md">
                <IconUsers size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Новые пациенты
              </Text>
            </Group>
            <Text fw={700} fz="lg" c="gray.9">
              {data?.new_patients ?? 0}
            </Text>
            <Text size="xs" c="dimmed" mt={0}>
              за день
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card padding="sm" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={2} wrap="nowrap">
              <ThemeIcon variant="light" color={SEMANTIC.metrics.cancellations} size="md" radius="md">
                <IconX size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Отмены / неявки
              </Text>
            </Group>
            <Text fw={700} fz="lg" c="gray.9">
              {(data?.bookings_cancelled ?? 0) + (data?.bookings_no_show ?? 0)}
            </Text>
            <Text size="xs" c="dimmed" mt={0}>
              отмены {data?.bookings_cancelled ?? 0} · неявки {data?.bookings_no_show ?? 0}
            </Text>
          </Card>
        </Grid.Col>
        {canViewRevenueDashboard ? (
          <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
            <Card padding="sm" radius="md" shadow="sm" withBorder {...metricCardShell}>
              <Group gap="xs" mb={2} wrap="nowrap">
                <ThemeIcon variant="light" color={SEMANTIC.metrics.appointments} size="md" radius="md">
                  <IconMail size={18} />
                </ThemeIcon>
                <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                  Количество обращений
                </Text>
              </Group>
              <Text fw={700} fz="lg" c="gray.9">
                {requestsCount}
              </Text>
              <Text size="xs" c="dimmed" mt={0}>
                уникальные пациенты в чате
              </Text>
            </Card>
          </Grid.Col>
        ) : null}
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card padding="sm" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={2} wrap="nowrap">
              <ThemeIcon variant="light" color="grape" size="md" radius="md">
                <IconSun size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Настроение дня
              </Text>
            </Group>
            <Progress value={pulse} size="sm" radius="md" color="grape" mb={4} />
            <Text fw={600} fz="lg" c="gray.9">
              {pulse} / 100
            </Text>
            <Text size="xs" c="dimmed" mt={0}>
              коэф. занятые / пустые
            </Text>
          </Card>
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6, md: 4 }}>
          <Card padding="sm" radius="md" shadow="sm" withBorder {...metricCardShell}>
            <Group gap="xs" mb={2} wrap="nowrap">
              <ThemeIcon variant="light" color="gray" size="md" radius="md">
                <IconClock size={18} />
              </ThemeIcon>
              <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                Пустые окна
              </Text>
            </Group>
            <Text fw={700} fz="lg" c="gray.9">
              {emptyH.toFixed(1)} ч
            </Text>
            <Text size="xs" c="dimmed" mt={0}>
              свободные слоты
            </Text>
          </Card>
        </Grid.Col>
      </Grid>

      {revenueHunter && isRevenueHunterEnabled(revenueHunter) && canViewRevenueDashboard ? (
        <Card
          padding="md"
          radius="md"
          shadow="sm"
          withBorder
          bg="white"
          styles={{
            root: {
              borderColor: "var(--mantine-color-gray-2)",
            },
          }}
        >
          <Group gap="xs" mb={4} wrap="nowrap">
            <ThemeIcon variant="light" color={SEMANTIC.ai.accent} size="lg" radius="md">
              <IconRobot size={18} />
            </ThemeIcon>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              Выручка, спасённая ИИ{" "}
              {revenueHunter.period === "night"
                ? "за ночь"
                : revenueHunter.period === "day"
                  ? "за день"
                  : revenueHunter.period === "week"
                    ? "за неделю"
                    : "за ночь"}
            </Text>
          </Group>
          <Text fw={700} fz="xl" c="teal.8">
            {revenueHunter.amount} ₽
          </Text>
        </Card>
      ) : null}

      <Divider my="xs" />

      <div id="clinic-wall">
        <Stack
          gap="sm"
          mt="xs"
          bg="var(--mantine-color-gray-0)"
          p="sm"
          style={{ borderRadius: 8 }}
        >
          <Group justify="flex-start" align="center" wrap="wrap">
            <Button
              variant="light"
              disabled={!canPostToStaffFeed || sessionLoading}
              onClick={() => {
                if (!canPostToStaffFeed) return;
                setIsComposerOpen((v) => !v);
              }}
            >
              Добавить пост
            </Button>
          </Group>

          {!sessionLoading && !canPostToStaffFeed ? (
            <Text size="xs" c="dimmed" maw={480}>
              Публикация постов только при праве manage_staff_collab.
            </Text>
          ) : null}

          {canPostToStaffFeed && isComposerOpen ? (
            <Card withBorder radius="md" padding="md" bg="var(--mantine-color-gray-0)">
              <Stack gap="sm">
                <Text size="xs" c="dimmed" fw={600}>
                  Добавить пост
                </Text>
                <TextInput
                  label="Тема"
                  placeholder="Например: С праздником 8 Марта!"
                  value={feedTitle}
                  onChange={(e) => setFeedTitle(e.currentTarget.value)}
                />
                <Textarea
                  label="Текст"
                  placeholder="Текст новости для персонала…"
                  minRows={5}
                  value={feedBody}
                  onChange={(e) => setFeedBody(e.currentTarget.value)}
                />
                <Group gap="xs">
                  <input
                    ref={feedFileRef}
                    type="file"
                    multiple
                    style={{ display: "none" }}
                    onChange={(e) => {
                      const list = e.target.files;
                      if (!list?.length) return;
                      setFeedFiles(Array.from(list));
                    }}
                  />
                  <ActionIcon
                    variant="light"
                    size="lg"
                    aria-label="Прикрепить файлы"
                    onClick={() => feedFileRef.current?.click()}
                  >
                    <IconPaperclip size={20} />
                  </ActionIcon>
                  <ActionIcon
                    variant="light"
                    size="lg"
                    aria-label="Изображение"
                    onClick={() => feedFileRef.current?.click()}
                  >
                    <IconPhoto size={20} />
                  </ActionIcon>
                  <ActionIcon
                    variant="light"
                    size="lg"
                    color="gray"
                    aria-label="Аудио (в разработке)"
                    title="Аудио: единый контур для админки и чатов — в плане"
                    disabled
                  >
                    <IconMicrophone size={20} />
                  </ActionIcon>
                  {feedFiles.length > 0 ? (
                    <Text size="xs" c="dimmed">
                      Файлов: {feedFiles.length} (загрузятся после публикации)
                    </Text>
                  ) : null}
                </Group>
                <Group justify="flex-end">
                  <Button
                    variant="filled"
                    color="indigo"
                    onClick={() => void publishPost()}
                    loading={createPost.isPending}
                    disabled={!feedBody.trim()}
                  >
                    Опубликовать
                  </Button>
                </Group>
              </Stack>
            </Card>
          ) : null}

          {staffPostsLoading ? (
            <PageSkeleton variant="table" rows={2} />
          ) : !staffPosts?.length ? (
            <EmptyState
              title="Пока нет постов"
              description="Делитесь новостями клиники — посты видят все сотрудники с доступом к ленте."
            />
          ) : (
            <Stack gap="sm">
              {staffPosts
                .slice()
                .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                .map((p) => (
                  <Paper
                    key={p.id}
                    withBorder
                    shadow="sm"
                    radius="md"
                    p="lg"
                    bg="white"
                    styles={{ root: { borderColor: "var(--mantine-color-gray-2)" } }}
                  >
                    <Stack gap="sm">
                      <Group justify="space-between" align="flex-start" wrap="nowrap" gap="sm">
                        <Stack gap={4} style={{ flex: 1, minWidth: 0 }}>
                          {p.title ? (
                            <Text size="sm" fw={600}>
                              {p.title}
                            </Text>
                          ) : null}
                          <Text size="xs" c="dimmed">
                            {p.author.full_name?.trim() || "Сотрудник"} ·{" "}
                            {new Date(p.created_at).toLocaleString()}
                          </Text>
                        </Stack>
                        {canPostToStaffFeed ? (
                          <Menu position="bottom-end" withinPortal>
                            <Menu.Target>
                              <ActionIcon variant="subtle" color="gray" aria-label="Действия с постом">
                                <IconDots size={18} stroke={1.5} />
                              </ActionIcon>
                            </Menu.Target>
                            <Menu.Dropdown>
                              <Menu.Item
                                onClick={() => {
                                  setEditingPost(p);
                                }}
                              >
                                Редактировать
                              </Menu.Item>
                              <Menu.Item
                                color="red"
                                disabled={deletePost.isPending}
                                onClick={() => {
                                  const ok = window.confirm("Удалить пост?");
                                  if (!ok) return;
                                  void deletePost.mutateAsync(p.id).then(() => {
                                    setEditingPost(null);
                                  });
                                }}
                              >
                                Удалить
                              </Menu.Item>
                            </Menu.Dropdown>
                          </Menu>
                        ) : null}
                      </Group>
                      <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                        {p.body}
                      </Text>
                      {(p.attachments ?? []).length > 0 ? (
                        <Stack gap="xs">
                          {(p.attachments ?? []).map((att) => (
                            <StaffFeedAttachmentPreview key={att.id} attachment={att} />
                          ))}
                        </Stack>
                      ) : null}
                      <Group gap="md" align="center" mt={4}>
                        <Group gap={6} align="center">
                          <ActionIcon
                            variant="subtle"
                            aria-label="Лайк"
                            loading={toggleLike.isPending}
                            onClick={() => toggleLike.mutate(p.id)}
                            styles={{
                              root: {
                                color: "var(--mantine-color-dimmed)",
                                "&:hover": { color: "var(--mantine-color-red-6)" },
                              },
                            }}
                          >
                            <IconHeart size={20} stroke={1.5} />
                          </ActionIcon>
                          <Text size="sm" c="dimmed" component="span">
                            {p.likes_count ?? 0}
                          </Text>
                        </Group>
                        <Group gap={6} align="center">
                          <ActionIcon
                            variant="subtle"
                            aria-label="Комментарии"
                            onClick={() =>
                              setOpenCommentsByPostId((prev) => ({
                                ...prev,
                                [p.id]: !prev[p.id],
                              }))
                            }
                            styles={{
                              root: {
                                color: "var(--mantine-color-dimmed)",
                                "&:hover": { color: "var(--mantine-color-red-6)" },
                              },
                            }}
                          >
                            <IconMessageCircle size={20} stroke={1.5} />
                          </ActionIcon>
                          <Text size="sm" c="dimmed" component="span">
                            {p.comments_count ?? 0}
                          </Text>
                        </Group>
                      </Group>

                      <StaffFeedPostComments postId={p.id} isOpen={Boolean(openCommentsByPostId[p.id])} />
                    </Stack>
                  </Paper>
                ))}
            </Stack>
          )}
        </Stack>
      </div>

      <GlassModal
        opened={!!editingPost}
        onClose={() => setEditingPost(null)}
        title="Редактировать пост"
      >
        {editingPost ? (
          <Stack gap="md">
            <TextInput
              label="Заголовок"
              placeholder="Необязательно"
              value={editTitle}
              onChange={(e) => setEditTitle(e.currentTarget.value)}
            />
            <Textarea
              label="Текст"
              value={editBody}
              onChange={(e) => setEditBody(e.currentTarget.value)}
              minRows={5}
            />

            <Text size="sm" fw={700} c="gray.9">
              Изображение / вложение
            </Text>
            {editingPost.attachments?.length ? (
              <Stack gap="xs">
                {editingPost.attachments.slice(0, 3).map((att) => (
                  <StaffFeedAttachmentPreview key={att.id} attachment={att} />
                ))}
              </Stack>
            ) : (
              <Text size="xs" c="dimmed">
                Пока вложений нет
              </Text>
            )}

            <input
              ref={editFileRef}
              type="file"
              accept="image/*,audio/*,video/*"
              style={{ display: "none" }}
              onChange={(e) => {
                const f = e.target.files?.[0] ?? null;
                setEditFile(f);
              }}
            />
            <Group justify="space-between" align="center">
              <Button
                size="xs"
                variant="light"
                onClick={() => editFileRef.current?.click()}
                disabled={updatePost.isPending}
              >
                Выбрать файл
              </Button>
              {editFile ? (
                <Text size="xs" c="dimmed">
                  {editFile.name}
                </Text>
              ) : null}
            </Group>

            {editFilePreviewUrl && (editFile?.type || "").toLowerCase().startsWith("image/") ? (
              <img
                src={editFilePreviewUrl}
                alt="preview"
                style={{ width: "100%", maxHeight: 320, objectFit: "contain", borderRadius: 8 }}
              />
            ) : null}
            {editFilePreviewUrl && (editFile?.type || "").toLowerCase().startsWith("audio/") ? (
              <audio controls src={editFilePreviewUrl} style={{ width: "100%" }} />
            ) : null}
            {editFilePreviewUrl && (editFile?.type || "").toLowerCase().startsWith("video/") ? (
              <video
                controls
                src={editFilePreviewUrl}
                style={{ width: "100%", maxHeight: 360, objectFit: "contain", borderRadius: 8 }}
              />
            ) : null}

            <Group justify="flex-end" mt="xs">
              <Button variant="default" onClick={() => setEditingPost(null)} disabled={updatePost.isPending}>
                Отмена
              </Button>
              <Button
                variant="filled"
                color="indigo"
                loading={updatePost.isPending}
                onClick={() => {
                  const title = editTitle.trim() ? editTitle : null;
                  updatePost.mutate(
                    { postId: editingPost.id, title, body: editBody, file: editFile },
                    {
                      onSuccess: () => {
                        setEditingPost(null);
                      },
                    }
                  );
                }}
                disabled={!editBody.trim()}
              >
                Сохранить
              </Button>
            </Group>
          </Stack>
        ) : null}
      </GlassModal>

      <style>{`
        @keyframes admin-emergency-blink {
          0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(250, 140, 0, 0.4); }
          50% { opacity: 0.92; box-shadow: 0 0 0 6px rgba(250, 140, 0, 0.15); }
        }
        .admin-emergency-blink {
          animation: admin-emergency-blink 1.2s ease-in-out infinite;
        }
      `}</style>
    </Stack>
  );
}
