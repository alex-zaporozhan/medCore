import { useEffect, useState } from "react";
import {
  Badge,
  Button,
  Card,
  Group,
  Modal,
  Stack,
  Table,
  Text,
  Textarea,
  TextInput,
  Title,
  Select,
} from "@mantine/core";
import dayjs from "dayjs";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";

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
}

async function fetchTasks() {
  return api.get<Task[]>("/v1/admin/tasks");
}

async function createTaskApi(payload: {
  title: string;
  description?: string | null;
  priority?: string;
  assignee_id?: string | null;
  role_assignee?: string | null;
}) {
  return api.post<Task>("/v1/admin/tasks", payload);
}

export default function AdminTasksPage() {
  const { currentClinicId } = useAdminClinic();
  const queryClient = useQueryClient();
  const [createOpened, setCreateOpened] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<string | null>("medium");

  const { data: tasks, isLoading } = useQuery({
    queryKey: ["admin-tasks"],
    queryFn: fetchTasks,
  });

  const createTaskMutation = useMutation({
    mutationFn: createTaskApi,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-tasks"] });
      setCreateOpened(false);
      setTitle("");
      setDescription("");
      setPriority("medium");
    },
  });

  useEffect(() => {
    if (!currentClinicId) return;
  }, [currentClinicId]);

  const handleCreate = () => {
    if (!title.trim()) return;
    createTaskMutation.mutate({
      title: title.trim(),
      description: description.trim() || null,
      priority: priority ?? "medium",
    });
  };

  const rows =
    tasks?.map((t) => (
      <Table.Tr key={t.id}>
        <Table.Td>{t.title}</Table.Td>
        <Table.Td>
          {t.priority === "high" || t.priority === "urgent" ? (
            <Badge color={t.priority === "urgent" ? "red" : "orange"} size="sm">
              {t.priority}
            </Badge>
          ) : (
            <Badge size="sm" variant="light">
              {t.priority}
            </Badge>
          )}
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
          {t.due_at ? dayjs(t.due_at).format("DD.MM.YYYY") : <Text size="xs">—</Text>}
        </Table.Td>
      </Table.Tr>
    )) ?? [];

  return (
    <Stack>
      <Group justify="space-between" align="center">
        <Title order={3}>Задачи</Title>
        <Button size="xs" onClick={() => setCreateOpened(true)}>
          Новая задача
        </Button>
      </Group>

      <ThreeColumnLayout
        preset="wide-center"
        left={
          <Stack gap="sm" p="xs">
            <Text size="sm" fw={500}>
              Контекст задач
            </Text>
            <Text size="xs" c="dimmed">
              Здесь позже появятся фильтры по клинике, ответственному и срокам. Сейчас вы
              видите общий список задач по админке.
            </Text>
          </Stack>
        }
        center={
          <Card shadow="sm" padding="md" withBorder>
            {isLoading ? (
              <Text size="sm">Загрузка задач...</Text>
            ) : !tasks || tasks.length === 0 ? (
              <Text size="sm" c="dimmed">
                Пока нет задач. Создайте первую задачу для себя или команды.
              </Text>
            ) : (
              <Table highlightOnHover striped withColumnBorders>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Заголовок</Table.Th>
                    <Table.Th>Приоритет</Table.Th>
                    <Table.Th>Статус</Table.Th>
                    <Table.Th>Срок</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>{rows}</Table.Tbody>
              </Table>
            )}
          </Card>
        }
        right={
          <Card shadow="sm" padding="md" withBorder>
            <Text size="sm" fw={500} mb="xs">
              Быстрое создание задачи
            </Text>
            <Text size="xs" c="dimmed" mb="sm">
              Используйте правую панель, чтобы держать фокус на текущем списке и при этом
              быстро добавлять новые задачи из ленты внимания, чатов или финансов.
            </Text>
            <Button size="xs" onClick={() => setCreateOpened(true)}>
              Создать задачу
            </Button>
          </Card>
        }
      />

      <Modal
        opened={createOpened}
        onClose={() => setCreateOpened(false)}
        title="Новая задача"
        centered
      >
        <Stack>
          <TextInput
            label="Заголовок задачи"
            placeholder="Например: Перезвонить пациенту по отменённой записи"
            value={title}
            onChange={(e) => setTitle(e.currentTarget.value)}
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
          <Group justify="flex-end">
            <Button
              onClick={handleCreate}
              loading={createTaskMutation.isPending}
              disabled={!title.trim()}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

