import { ApiErrorWithCode } from "@/api/client";
import {
  useAdminRagKbDocument,
  useAdminRagKbDocuments,
  useCreateRagKbDocumentMutation,
  useDeleteRagKbDocumentMutation,
  useUpdateRagKbDocumentMutation,
} from "@/hooks/useAdminRagKb";
import { useAdminSession } from "@/hooks/useAdminSession";
import { AdminSettingsSectionCard, ContextBar } from "@/shared/ui";
import {
  Alert,
  Button,
  Group,
  Loader,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
} from "@mantine/core";
import { useEffect, useState } from "react";

export default function AdminRagKbPage() {
  const { data: session } = useAdminSession();
  const orgReady = Boolean(session?.organization_id);
  const listQ = useAdminRagKbDocuments(orgReady);
  const createMut = useCreateRagKbDocumentMutation();
  const delMut = useDeleteRagKbDocumentMutation();
  const updateMut = useUpdateRagKbDocumentMutation();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [editId, setEditId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editBody, setEditBody] = useState("");
  const editDetailQ = useAdminRagKbDocument(editId, orgReady && editId !== null);

  useEffect(() => {
    setEditTitle("");
    setEditBody("");
  }, [editId]);

  useEffect(() => {
    if (editDetailQ.data && editId && editDetailQ.data.id === editId) {
      setEditTitle(editDetailQ.data.title);
      setEditBody(editDetailQ.data.body);
    }
  }, [editDetailQ.data, editId]);

  const err =
    listQ.error instanceof ApiErrorWithCode
      ? listQ.error
      : createMut.error instanceof ApiErrorWithCode
        ? createMut.error
        : updateMut.error instanceof ApiErrorWithCode
          ? updateMut.error
          : null;

  return (
    <Stack p="md">
      <ContextBar title="База знаний (RAG, per-org)" />
      {!orgReady ? (
        <Alert color="gray">Нужна привязка к организации и опция тарифа ai.rag.org_kb.</Alert>
      ) : (
        <>
          <Modal
            opened={editId !== null}
            onClose={() => setEditId(null)}
            title="Редактировать фрагмент"
            size="lg"
          >
            {editDetailQ.isLoading ? (
              <Loader />
            ) : editDetailQ.error ? (
              <Alert color="red">Не удалось загрузить документ</Alert>
            ) : (
              <Stack gap="sm">
                <TextInput
                  label="Заголовок"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.currentTarget.value)}
                />
                <Textarea
                  label="Текст"
                  minRows={6}
                  value={editBody}
                  onChange={(e) => setEditBody(e.currentTarget.value)}
                />
                <Group justify="flex-end">
                  <Button variant="default" onClick={() => setEditId(null)}>
                    Отмена
                  </Button>
                  <Button
                    disabled={!editTitle.trim() || !editBody.trim()}
                    loading={updateMut.isPending}
                    onClick={() => {
                      if (!editId) return;
                      updateMut.mutate(
                        {
                          id: editId,
                          payload: { title: editTitle.trim(), body: editBody.trim() },
                        },
                        { onSuccess: () => setEditId(null) },
                      );
                    }}
                  >
                    Сохранить
                  </Button>
                </Group>
              </Stack>
            )}
          </Modal>
          {err?.code === "entitlement_required" ? (
            <Alert color="yellow">Требуется опция тарифа ai.rag.org_kb для организации.</Alert>
          ) : null}
          {listQ.error && err?.code !== "entitlement_required" ? (
            <Alert color="red">Не удалось загрузить документы</Alert>
          ) : null}

          <AdminSettingsSectionCard title="Новый фрагмент">
            <Stack gap="sm">
              <TextInput label="Заголовок" value={title} onChange={(e) => setTitle(e.currentTarget.value)} />
              <Textarea label="Текст" minRows={4} value={body} onChange={(e) => setBody(e.currentTarget.value)} />
              <Button
                disabled={!title.trim() || !body.trim()}
                loading={createMut.isPending}
                onClick={() =>
                  createMut.mutate(
                    { title: title.trim(), body: body.trim() },
                    {
                      onSuccess: () => {
                        setTitle("");
                        setBody("");
                      },
                    }
                  )
                }
              >
                Добавить
              </Button>
            </Stack>
          </AdminSettingsSectionCard>

          <AdminSettingsSectionCard title="Документы">
            {!listQ.data?.items.length ? (
              <Text size="sm" c="dimmed">
                Пока пусто
              </Text>
            ) : (
              <Table striped highlightOnHover>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Заголовок</Table.Th>
                    <Table.Th>Обновлён</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {listQ.data.items.map((row) => (
                    <Table.Tr key={row.id}>
                      <Table.Td>{row.title}</Table.Td>
                      <Table.Td>
                        <Text size="xs" c="dimmed">
                          {row.updated_at}
                        </Text>
                      </Table.Td>
                      <Table.Td>
                        <Group justify="flex-end">
                          <Button size="xs" variant="light" onClick={() => setEditId(row.id)}>
                            Изменить
                          </Button>
                          <Button
                            size="xs"
                            color="red"
                            variant="subtle"
                            loading={delMut.isPending}
                            onClick={() => delMut.mutate(row.id)}
                          >
                            Удалить
                          </Button>
                        </Group>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </AdminSettingsSectionCard>
        </>
      )}
    </Stack>
  );
}
