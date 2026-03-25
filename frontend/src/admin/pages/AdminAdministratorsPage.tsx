import {
  useAdminAdmins,
  useCreateAdminMutation,
  usePatchAdminEmploymentMutation,
} from "@/hooks";
import {
  ActionIcon,
  Alert,
  Badge,
  Button,
  Menu,
  Paper,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { IconDotsVertical } from "@tabler/icons-react";
import { getAdminId } from "@/api/client";
import { ContextBar } from "@/shared/ui/ContextBar";
import { PageSkeleton } from "@/shared/ui/PageSkeleton";
import { QueryErrorAlert } from "@/shared/ui";
import { useState } from "react";

const MIN_PASSWORD_LENGTH = 8;

export default function AdminAdministratorsPage() {
  const { data: admins, isLoading, isError, error } = useAdminAdmins();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [employmentError, setEmploymentError] = useState<string | null>(null);
  const createMut = useCreateAdminMutation();
  const patchEmployment = usePatchAdminEmploymentMutation();
  const currentAdminId = getAdminId();

  const handleAdd = () => {
    if (password.length < MIN_PASSWORD_LENGTH) {
      setSubmitError(`Пароль не менее ${MIN_PASSWORD_LENGTH} символов`);
      return;
    }
    setSubmitError(null);
    createMut.mutate(
      {
        email: email.trim(),
        password,
        full_name: fullName.trim() || null,
        birth_date: birthDate.trim() || null,
      },
      {
        onSuccess: () => {
          setEmail("");
          setPassword("");
          setFullName("");
          setBirthDate("");
          setSubmitError(null);
        },
        onError: (e) => setSubmitError(e instanceof Error ? e.message : "Ошибка"),
      }
    );
  };

  const list = admins ?? [];

  return (
    <Stack gap="md">
      <ContextBar title="Администраторы" />
      <Text size="sm" c="dimmed">
        Список администраторов клиники. В чате сохраняется, какой администратор отправил сообщение. Добавьте учётные записи с ФИО и датой рождения для логирования.
      </Text>

      <Paper p="md" withBorder>
        <Stack gap="md">
          <Text fw={600} size="sm">Добавить администратора</Text>
          {submitError && (
            <Alert color="red" onClose={() => setSubmitError(null)} withCloseButton>
              {submitError}
            </Alert>
          )}
          <TextInput
            label="Email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.currentTarget.value)}
            placeholder="admin2@example.com"
            required
          />
          <TextInput
            label="Пароль"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.currentTarget.value)}
            placeholder="••••••••"
            required
            minLength={MIN_PASSWORD_LENGTH}
            description={`Не менее ${MIN_PASSWORD_LENGTH} символов`}
          />
          <TextInput
            label="ФИО"
            value={fullName}
            onChange={(e) => setFullName(e.currentTarget.value)}
            placeholder="Иванов Иван Иванович"
          />
          <TextInput
            label="Дата рождения"
            type="date"
            value={birthDate}
            onChange={(e) => setBirthDate(e.currentTarget.value)}
          />
          <Button onClick={handleAdd} loading={createMut.isPending}>
            Добавить
          </Button>
        </Stack>
      </Paper>

      <Paper p="md" withBorder>
        <Text fw={600} size="sm" mb="xs">Список</Text>
        {employmentError && (
          <Alert color="red" mb="sm" onClose={() => setEmploymentError(null)} withCloseButton>
            {employmentError}
          </Alert>
        )}
        {isLoading && <PageSkeleton variant="table" rows={4} />}
        {isError && <QueryErrorAlert error={error} />}
        {!isLoading && !isError && list.length === 0 && (
          <Text size="sm" c="dimmed">Нет администраторов. Добавьте первого выше.</Text>
        )}
        {list.length > 0 && (
          <Table withTableBorder withColumnBorders verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Email</Table.Th>
                <Table.Th>ФИО</Table.Th>
                <Table.Th>Дата рождения</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th style={{ width: 52 }} />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {list.map((a) => {
                const isSelf = Boolean(currentAdminId && a.id === currentAdminId);
                const isTerminated = a.employment_status === "terminated";
                const rowPatching =
                  patchEmployment.isPending && patchEmployment.variables?.adminId === a.id;
                return (
                <Table.Tr key={a.id}>
                  <Table.Td>{a.email}</Table.Td>
                  <Table.Td>{a.full_name ?? "—"}</Table.Td>
                  <Table.Td>{a.birth_date ?? "—"}</Table.Td>
                  <Table.Td>
                    <Badge
                      size="sm"
                      variant="light"
                      color={isTerminated ? "gray" : "green"}
                    >
                      {isTerminated ? "Уволен" : "Активен"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    {isSelf ? (
                      <Text size="xs" c="dimmed" title="Увольнение себя недоступно">
                        —
                      </Text>
                    ) : (
                    <Menu position="bottom-end" withArrow>
                      <Menu.Target>
                        <ActionIcon
                          variant="subtle"
                          size="sm"
                          aria-label="Действия"
                          loading={rowPatching}
                          disabled={rowPatching}
                        >
                          <IconDotsVertical size={16} />
                        </ActionIcon>
                      </Menu.Target>
                      <Menu.Dropdown>
                        {!isTerminated ? (
                          <Menu.Item
                            color="red"
                            onClick={() => {
                              setEmploymentError(null);
                              patchEmployment.mutate(
                                { adminId: a.id, employment_status: "terminated" },
                                {
                                  onError: (e) =>
                                    setEmploymentError(
                                      e instanceof Error ? e.message : "Не удалось уволить"
                                    ),
                                }
                              );
                            }}
                          >
                            Уволить
                          </Menu.Item>
                        ) : (
                          <Menu.Item
                            onClick={() => {
                              setEmploymentError(null);
                              patchEmployment.mutate(
                                { adminId: a.id, employment_status: "active" },
                                {
                                  onError: (e) =>
                                    setEmploymentError(
                                      e instanceof Error ? e.message : "Не удалось восстановить"
                                    ),
                                }
                              );
                            }}
                          >
                            Восстановить
                          </Menu.Item>
                        )}
                      </Menu.Dropdown>
                    </Menu>
                    )}
                  </Table.Td>
                </Table.Tr>
              );
              })}
            </Table.Tbody>
          </Table>
        )}
      </Paper>
    </Stack>
  );
}
