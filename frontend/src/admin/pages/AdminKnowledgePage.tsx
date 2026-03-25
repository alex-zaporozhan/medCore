import { useEffect, useState } from "react";
import {
  Accordion,
  Badge,
  Button,
  Group,
  Modal,
  MultiSelect,
  Stack,
  Text,
  TextInput,
  Textarea,
} from "@mantine/core";
import { ContextBar, EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { useCreateKnowledgeDocument, useKnowledgeDocuments, useUpdateKnowledgeDocument } from "@/hooks/useStaffCollab";
import dayjs from "dayjs";

const ROLE_OPTIONS = [
  { value: "owner", label: "Владелец" },
  { value: "manager", label: "Менеджер" },
  { value: "admin", label: "Администратор" },
  { value: "doctor", label: "Врач / мастер" },
];

export default function AdminKnowledgePage() {
  const { data: docs, isLoading, isError, error } = useKnowledgeDocuments();
  const createMut = useCreateKnowledgeDocument();

  const [createOpen, setCreateOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [bodyMd, setBodyMd] = useState("");
  const [folder, setFolder] = useState("general");
  const [visible, setVisible] = useState<string[]>(["owner", "manager", "admin", "doctor"]);

  const [editId, setEditId] = useState<string | null>(null);

  const onCreate = () => {
    if (!title.trim() || !bodyMd.trim()) return;
    createMut.mutate(
      {
        title: title.trim(),
        body_md: bodyMd.trim(),
        folder_key: folder.trim() || "general",
        visible_roles: visible,
      },
      {
        onSuccess: () => {
          setCreateOpen(false);
          setTitle("");
          setBodyMd("");
          setFolder("general");
          setVisible(["owner", "manager", "admin", "doctor"]);
        },
      }
    );
  };

  const grouped = (docs ?? []).reduce<Record<string, typeof docs>>((acc, d) => {
    const k = d.folder_key || "general";
    if (!acc[k]) acc[k] = [];
    acc[k]!.push(d);
    return acc;
  }, {});

  return (
    <Stack gap="md">
      <ContextBar title="База знаний" />
      <Text size="sm" c="dimmed">
        Статьи по ролям; видимость настраивается при создании.
      </Text>
      <Group justify="flex-end">
        <Button onClick={() => setCreateOpen(true)}>Новая статья</Button>
      </Group>

      {isLoading ? (
        <PageSkeleton variant="table" rows={4} />
      ) : isError ? (
        <QueryErrorAlert error={error} />
      ) : !docs?.length ? (
        <EmptyState title="Пока пусто" description="Добавьте регламенты и инструкции для команды." />
      ) : (
        <Accordion variant="separated" radius="md">
          {Object.entries(grouped).map(([folderKey, items]) => (
            <Accordion.Item key={folderKey} value={folderKey}>
              <Accordion.Control>
                <Text fw={600}>{folderKey}</Text>
              </Accordion.Control>
              <Accordion.Panel>
                <Stack gap="md">
                  {(items ?? []).map((d) => (
                    <Stack
                      key={d.id}
                      gap={6}
                      p="sm"
                      style={{
                        border: "1px solid var(--mantine-color-gray-3)",
                        borderRadius: 8,
                        background: "var(--mantine-color-body)",
                      }}
                    >
                      <Group justify="space-between">
                        <Text fw={600}>{d.title}</Text>
                        <Button size="xs" variant="light" onClick={() => setEditId(d.id)}>
                          Редактировать
                        </Button>
                      </Group>
                      <Group gap="xs">
                        {d.visible_roles.map((r) => (
                          <Badge key={r} size="xs" variant="outline">
                            {r}
                          </Badge>
                        ))}
                      </Group>
                      <Text size="xs" c="dimmed">
                        Обновлено {dayjs(d.updated_at).format("DD.MM.YYYY HH:mm")} ·{" "}
                        {d.created_by.full_name?.trim() || "автор"}
                      </Text>
                      <Text size="sm" component="pre" style={{ whiteSpace: "pre-wrap", fontFamily: "inherit" }}>
                        {d.body_md}
                      </Text>
                    </Stack>
                  ))}
                </Stack>
              </Accordion.Panel>
            </Accordion.Item>
          ))}
        </Accordion>
      )}

      <Modal opened={createOpen} onClose={() => setCreateOpen(false)} title="Новая статья" size="lg" centered>
        <Stack gap="sm">
          <TextInput label="Папка (ключ)" value={folder} onChange={(e) => setFolder(e.currentTarget.value)} />
          <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
          <MultiSelect
            label="Видимость для ролей"
            data={ROLE_OPTIONS}
            value={visible}
            onChange={setVisible}
          />
          <Textarea
            label="Текст (Markdown)"
            value={bodyMd}
            onChange={(e) => setBodyMd(e.currentTarget.value)}
            minRows={8}
          />
          <Group justify="flex-end">
            <Button variant="default" onClick={() => setCreateOpen(false)}>
              Отмена
            </Button>
            <Button onClick={onCreate} loading={createMut.isPending}>
              Сохранить
            </Button>
          </Group>
        </Stack>
      </Modal>

      <Modal
        opened={!!editId}
        onClose={() => setEditId(null)}
        title="Редактировать статью"
        size="lg"
        centered
      >
        {editId ? (
          <EditDocForm key={editId} docId={editId} onClose={() => setEditId(null)} />
        ) : null}
      </Modal>
    </Stack>
  );
}

function EditDocForm({ docId, onClose }: { docId: string; onClose: () => void }) {
  const { data: docs } = useKnowledgeDocuments();
  const doc = docs?.find((d) => d.id === docId);
  const updateMut = useUpdateKnowledgeDocument(docId);
  const [title, setTitle] = useState("");
  const [bodyMd, setBodyMd] = useState("");
  const [folder, setFolder] = useState("general");
  const [visible, setVisible] = useState<string[]>([]);

  useEffect(() => {
    if (!doc) return;
    setTitle(doc.title);
    setBodyMd(doc.body_md);
    setFolder(doc.folder_key);
    setVisible(doc.visible_roles);
  }, [doc]);

  if (!doc) {
    return (
      <Text size="sm" c="dimmed">
        Загрузка…
      </Text>
    );
  }

  const save = () => {
    updateMut.mutate(
      {
        title: title.trim(),
        body_md: bodyMd.trim(),
        folder_key: folder.trim() || "general",
        visible_roles: visible,
      },
      { onSuccess: () => onClose() }
    );
  };

  return (
    <Stack gap="sm">
      <TextInput label="Папка" value={folder} onChange={(e) => setFolder(e.currentTarget.value)} />
      <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
      <MultiSelect
        label="Видимость"
        data={ROLE_OPTIONS}
        value={visible}
        onChange={setVisible}
      />
      <Textarea label="Текст" value={bodyMd} onChange={(e) => setBodyMd(e.currentTarget.value)} minRows={8} />
      <Group justify="flex-end">
        <Button variant="default" onClick={onClose}>
          Отмена
        </Button>
        <Button onClick={save} loading={updateMut.isPending}>
          Сохранить
        </Button>
      </Group>
    </Stack>
  );
}
