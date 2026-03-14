import {
  useAdminPromoPosts,
  useCreatePromoPost,
  useUpdatePromoPost,
  useDeletePromoPost,
  useAdminStories,
  useCreateStory,
  useUpdateStory,
  useDeleteStory,
  type PromoPostRead,
  type PromoPostCreate,
  type StoryRead,
  type StoryCreate,
} from "@/hooks/useAdminMarketing";
import {
  useMarketingAttributionSummary,
  useMarketingAttributionDrillDown,
  type MarketingChannelSummaryItem,
} from "@/hooks/useMarketingAttribution";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Alert,
  Badge,
  Button,
  Drawer,
  Group,
  Loader,
  Modal,
  Paper,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  Textarea,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useEffect, useState } from "react";

const POST_DRAFT_KEY = "admin_marketing_post_draft";
const STORY_DRAFT_KEY = "admin_marketing_story_draft";

function loadDraft<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}
function saveDraft(key: string, data: object) {
  try {
    sessionStorage.setItem(key, JSON.stringify(data));
  } catch {
    // ignore
  }
}
function clearDraft(key: string) {
  try {
    sessionStorage.removeItem(key);
  } catch {
    // ignore
  }
}

function PostsTab({ clinicId }: { clinicId: string }) {
  const { data: posts, isLoading, isError, error } = useAdminPromoPosts(clinicId);
  const createMut = useCreatePromoPost(clinicId);
  const updateMut = useUpdatePromoPost(clinicId);
  const deleteMut = useDeletePromoPost(clinicId);
  const [opened, { open, close }] = useDisclosure(false);
  const [editing, setEditing] = useState<PromoPostRead | null>(null);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [image_url, setImageUrl] = useState("");
  const [link, setLink] = useState("");
  const [is_published, setIsPublished] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const draft = loadDraft<{ title: string; body: string; image_url: string; link: string }>(POST_DRAFT_KEY);
    if (draft && !opened) {
      setTitle(draft.title ?? "");
      setBody(draft.body ?? "");
      setImageUrl(draft.image_url ?? "");
      setLink(draft.link ?? "");
    }
  }, []);

  const reset = () => {
    setEditing(null);
    setTitle("");
    setBody("");
    setImageUrl("");
    setLink("");
    setIsPublished(false);
    setSaveError(null);
    clearDraft(POST_DRAFT_KEY);
  };

  const handleSave = () => {
    setSaveError(null);
    const payload: PromoPostCreate = {
      title,
      body,
      image_url: image_url || null,
      link: link || null,
      is_published,
    };
    if (editing) {
      updateMut.mutate(
        { postId: editing.id, body: payload },
        {
          onSuccess: () => { close(); reset(); },
          onError: (e) => setSaveError(e.message),
        }
      );
    } else {
      createMut.mutate(payload, {
        onSuccess: () => { close(); reset(); },
        onError: (e) => setSaveError(e.message),
      });
    }
  };

  const handleOpenNew = () => {
    setSaveError(null);
    setEditing(null);
    open();
  };
  const handleClose = () => {
    saveDraft(POST_DRAFT_KEY, { title, body, image_url, link });
    close();
    setSaveError(null);
  };

  if (isLoading) return <Loader size="sm" />;
  if (isError) return <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>;

  const list = posts ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Акции и новости для ленты</Text>
        <Button size="xs" onClick={handleOpenNew}>Добавить пост</Button>
      </Group>
      {list.length === 0 ? (
        <EmptyStateHint title="Нет постов. Создайте акцию или новость." />
      ) : (
        <Table withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Заголовок</Table.Th>
              <Table.Th>Публикация</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((p) => (
              <Table.Tr key={p.id}>
                <Table.Td>{p.title}</Table.Td>
                <Table.Td>
                  <Badge color={p.is_published ? "green" : "gray"}>
                    {p.is_published ? "Опубликован" : "Черновик"}
                  </Badge>
                </Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        setEditing(p);
                        setTitle(p.title);
                        setBody(p.body);
                        setImageUrl(p.image_url ?? "");
                        setLink(p.link ?? "");
                        setIsPublished(p.is_published);
                        setSaveError(null);
                        open();
                      }}
                    >
                      Изменить
                    </Button>
                    <Button size="xs" variant="subtle" color="red" onClick={() => deleteMut.mutate(p.id)}>Удалить</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Modal opened={opened} onClose={handleClose} title={editing ? "Изменить пост" : "Новый пост"} size="md">
        <Stack>
          {saveError && (
            <Alert color="red" title="Ошибка" onClose={() => setSaveError(null)} withCloseButton>
              {saveError}
            </Alert>
          )}
          <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.target.value)} required />
          <Textarea label="Текст" value={body} onChange={(e) => setBody(e.target.value)} minRows={3} required />
          <TextInput label="URL картинки" value={image_url} onChange={(e) => setImageUrl(e.target.value)} />
          <TextInput label="Ссылка" value={link} onChange={(e) => setLink(e.target.value)} />
          <Switch label="Опубликовать" checked={is_published} onChange={(e) => setIsPublished(e.currentTarget.checked)} />
          <Button onClick={handleSave} loading={createMut.isPending || updateMut.isPending}>
            {editing ? "Сохранить" : "Создать"}
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}

function StoriesTab({ clinicId }: { clinicId: string }) {
  const { data: stories, isLoading, isError, error } = useAdminStories(clinicId);
  const createMut = useCreateStory(clinicId);
  const updateMut = useUpdateStory(clinicId);
  const deleteMut = useDeleteStory(clinicId);
  const [opened, { open, close }] = useDisclosure(false);
  const [editing, setEditing] = useState<StoryRead | null>(null);
  const [media_url, setMediaUrl] = useState("");
  const [caption, setCaption] = useState("");
  const [order_index, setOrderIndex] = useState(0);
  const [saveError, setSaveError] = useState<string | null>(null);

  useEffect(() => {
    const draft = loadDraft<{ media_url: string; caption: string; order_index: number }>(STORY_DRAFT_KEY);
    if (draft && !opened) {
      setMediaUrl(draft.media_url ?? "");
      setCaption(draft.caption ?? "");
      setOrderIndex(Number(draft.order_index) || 0);
    }
  }, []);

  const reset = () => {
    setEditing(null);
    setMediaUrl("");
    setCaption("");
    setOrderIndex(0);
    setSaveError(null);
    clearDraft(STORY_DRAFT_KEY);
  };

  const handleSave = () => {
    setSaveError(null);
    const payload: StoryCreate = {
      media_url,
      caption: caption || null,
      order_index,
      media_type: "image",
    };
    if (editing) {
      updateMut.mutate(
        { storyId: editing.id, body: payload },
        {
          onSuccess: () => { close(); reset(); },
          onError: (e) => setSaveError(e.message),
        }
      );
    } else {
      createMut.mutate(payload, {
        onSuccess: () => { close(); reset(); },
        onError: (e) => setSaveError(e.message),
      });
    }
  };

  const handleCloseStories = () => {
    saveDraft(STORY_DRAFT_KEY, { media_url, caption, order_index });
    close();
    setSaveError(null);
  };

  if (isLoading) return <Loader size="sm" />;
  if (isError) return <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>;

  const list = stories ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <Text size="sm" c="dimmed">Сторис для ленты (медиа + подпись)</Text>
        <Button size="xs" onClick={() => { setSaveError(null); setEditing(null); open(); }}>Добавить сторис</Button>
      </Group>
      {list.length === 0 ? (
        <EmptyStateHint title="Нет сторис. Добавьте карточки для полосы в PWA." />
      ) : (
        <Table withTableBorder withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Порядок</Table.Th>
              <Table.Th>Медиа URL</Table.Th>
              <Table.Th>Подпись</Table.Th>
              <Table.Th />
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((s) => (
              <Table.Tr key={s.id}>
                <Table.Td>{s.order_index}</Table.Td>
                <Table.Td><Text size="xs" truncate maw={200}>{s.media_url}</Text></Table.Td>
                <Table.Td><Text size="xs" truncate maw={150}>{s.caption ?? "—"}</Text></Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => {
                        setEditing(s);
                        setMediaUrl(s.media_url);
                        setCaption(s.caption ?? "");
                        setOrderIndex(s.order_index);
                        open();
                      }}
                    >
                      Изменить
                    </Button>
                    <Button size="xs" variant="subtle" color="red" onClick={() => deleteMut.mutate(s.id)}>Удалить</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}
      <Modal opened={opened} onClose={handleCloseStories} title={editing ? "Изменить сторис" : "Новый сторис"}>
        <Stack>
          {saveError && (
            <Alert color="red" title="Ошибка" onClose={() => setSaveError(null)} withCloseButton>
              {saveError}
            </Alert>
          )}
          <TextInput label="URL медиа (картинка/видео)" value={media_url} onChange={(e) => setMediaUrl(e.target.value)} required />
          <TextInput label="Подпись" value={caption} onChange={(e) => setCaption(e.target.value)} />
          <TextInput
            label="Порядок"
            type="number"
            value={String(order_index)}
            onChange={(e) => setOrderIndex(Number(e.target.value) || 0)}
          />
          <Button onClick={handleSave} loading={createMut.isPending || updateMut.isPending} disabled={!media_url}>
            {editing ? "Сохранить" : "Создать"}
          </Button>
        </Stack>
      </Modal>
    </Stack>
  );
}

function formatDateForInput(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function AttributionTab({ clinicId }: { clinicId: string }) {
  const today = new Date();
  const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
  const [dateFrom, setDateFrom] = useState(formatDateForInput(firstDay));
  const [dateTo, setDateTo] = useState(formatDateForInput(today));
  const [selectedRow, setSelectedRow] = useState<MarketingChannelSummaryItem | null>(null);
  const [drillType, setDrillType] = useState<"leads" | "bookings" | "transactions">("leads");

  const { data: summary, isLoading, isError, error } = useMarketingAttributionSummary(
    clinicId,
    dateFrom,
    dateTo,
    null,
    null
  );

  const { data: drillDown, isLoading: drillLoading } = useMarketingAttributionDrillDown({
    dateFrom: selectedRow ? dateFrom : null,
    dateTo: selectedRow ? dateTo : null,
    drillType,
    trafficSourceId: selectedRow?.traffic_source_id ?? null,
    campaignId: selectedRow?.campaign_id ?? null,
    enabled: !!selectedRow,
  });

  const items = summary?.items ?? [];

  return (
    <Stack>
      <Group align="flex-end" gap="sm">
        <TextInput
          type="date"
          label="С"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.currentTarget.value || dateFrom)}
          size="xs"
        />
        <TextInput
          type="date"
          label="По"
          value={dateTo}
          onChange={(e) => setDateTo(e.currentTarget.value || dateTo)}
          size="xs"
        />
      </Group>
      <Text size="sm" c="dimmed">
        ROI по каналам и кампаниям. Клик по строке — детализация (лиды, записи, транзакции).
      </Text>
      <Paper withBorder radius="md" p="sm">
        {isLoading && <Loader size="sm" />}
        {isError && (
          <Text size="sm" c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>
        )}
        {!isLoading && !isError && (
          <Table striped highlightOnHover withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Источник</Table.Th>
                <Table.Th>Кампания</Table.Th>
                <Table.Th>Лиды</Table.Th>
                <Table.Th>Записи</Table.Th>
                <Table.Th>Дошли</Table.Th>
                <Table.Th>Выручка</Table.Th>
                <Table.Th>Затраты</Table.Th>
                <Table.Th>CAC</Table.Th>
                <Table.Th>ROI</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.length === 0 ? (
                <Table.Tr>
                  <Table.Td colSpan={9}>
                    <Text size="sm" c="dimmed">Нет данных за период.</Text>
                  </Table.Td>
                </Table.Tr>
              ) : (
                items.map((row, idx) => (
                  <Table.Tr
                    key={`${row.traffic_source_id ?? "ts"}-${row.campaign_id ?? "cmp"}-${idx}`}
                    style={{ cursor: "pointer" }}
                    onClick={() => setSelectedRow(row)}
                  >
                    <Table.Td>{row.traffic_source_name ?? row.traffic_source_code ?? "—"}</Table.Td>
                    <Table.Td>{row.campaign_name ?? row.campaign_code ?? "—"}</Table.Td>
                    <Table.Td>{row.leads_count}</Table.Td>
                    <Table.Td>{row.bookings_count}</Table.Td>
                    <Table.Td>{row.completed_bookings_count}</Table.Td>
                    <Table.Td>{row.revenue_sum} ₽</Table.Td>
                    <Table.Td>{row.ad_spend != null ? `${row.ad_spend} ₽` : "—"}</Table.Td>
                    <Table.Td>{row.cac != null ? row.cac.toFixed(0) : "—"}</Table.Td>
                    <Table.Td>{row.roi != null ? `${(row.roi * 100).toFixed(0)}%` : "—"}</Table.Td>
                  </Table.Tr>
                ))
              )}
            </Table.Tbody>
          </Table>
        )}
      </Paper>

      <Drawer
        opened={selectedRow !== null}
        onClose={() => setSelectedRow(null)}
        position="right"
        size="md"
        title={
          selectedRow
            ? `Детали: ${selectedRow.traffic_source_name ?? selectedRow.traffic_source_code ?? "Канал"} · ${selectedRow.campaign_name ?? selectedRow.campaign_code ?? "—"}`
            : ""
        }
      >
        {selectedRow && (
          <Stack gap="md">
            <Tabs value={drillType} onChange={(v) => setDrillType((v as "leads" | "bookings" | "transactions") || "leads")}>
              <Tabs.List>
                <Tabs.Tab value="leads">Лиды</Tabs.Tab>
                <Tabs.Tab value="bookings">Записи</Tabs.Tab>
                <Tabs.Tab value="transactions">Транзакции</Tabs.Tab>
              </Tabs.List>
              <Tabs.Panel value="leads" pt="sm">
                {drillLoading && <Loader size="xs" />}
                {drillDown && (
                  <Stack gap={4}>
                    <Text size="xs" c="dimmed">Всего: {drillDown.total}</Text>
                    {drillDown.items.map((it) => (
                      <Text key={it.id} size="sm">• {it.display_label ?? it.id}</Text>
                    ))}
                  </Stack>
                )}
              </Tabs.Panel>
              <Tabs.Panel value="bookings" pt="sm">
                {drillLoading && <Loader size="xs" />}
                {drillDown && (
                  <Stack gap={4}>
                    <Text size="xs" c="dimmed">Всего: {drillDown.total}</Text>
                    {drillDown.items.map((it) => (
                      <Text key={it.id} size="sm">• {it.display_label ?? it.id}</Text>
                    ))}
                  </Stack>
                )}
              </Tabs.Panel>
              <Tabs.Panel value="transactions" pt="sm">
                {drillLoading && <Loader size="xs" />}
                {drillDown && (
                  <Stack gap={4}>
                    <Text size="xs" c="dimmed">Всего: {drillDown.total}</Text>
                    {drillDown.items.map((it) => (
                      <Text key={it.id} size="sm">• {it.display_label ?? it.id}</Text>
                    ))}
                  </Stack>
                )}
              </Tabs.Panel>
            </Tabs>
          </Stack>
        )}
      </Drawer>
    </Stack>
  );
}

export default function AdminMarketingPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;

  if (!clinicId) {
    return (
      <Stack>
        <Title order={3}>Маркетинг</Title>
        <Text size="sm" c="dimmed">Выберите клинику.</Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <Title order={3}>Маркетинг</Title>
      <Tabs defaultValue="posts">
        <Tabs.List>
          <Tabs.Tab value="posts">Посты (лента)</Tabs.Tab>
          <Tabs.Tab value="stories">Сторис</Tabs.Tab>
          <Tabs.Tab value="attribution">Атрибуция</Tabs.Tab>
        </Tabs.List>
        <Tabs.Panel value="posts" pt="md">
          <PostsTab clinicId={clinicId} />
        </Tabs.Panel>
        <Tabs.Panel value="stories" pt="md">
          <StoriesTab clinicId={clinicId} />
        </Tabs.Panel>
        <Tabs.Panel value="attribution" pt="md">
          <AttributionTab clinicId={clinicId} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
