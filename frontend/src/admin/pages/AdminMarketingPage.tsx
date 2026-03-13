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
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Alert,
  Badge,
  Button,
  Group,
  Loader,
  Modal,
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
        </Tabs.List>
        <Tabs.Panel value="posts" pt="md">
          <PostsTab clinicId={clinicId} />
        </Tabs.Panel>
        <Tabs.Panel value="stories" pt="md">
          <StoriesTab clinicId={clinicId} />
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}
