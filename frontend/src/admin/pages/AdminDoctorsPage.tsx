import { useDeleteDoctor, useDoctors } from "@/hooks";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyState, PageSkeleton } from "@/shared/ui";
import { ActionIcon, Button, HoverCard, Menu, Stack, Table, Text } from "@mantine/core";
import { IconDotsVertical, IconEdit, IconStethoscope, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { DoctorEntityDrawer } from "@/admin/components/entity/DoctorEntityDrawer";
import type { Doctor } from "@/api/types";
import { useQueryClient } from "@tanstack/react-query";

export default function AdminDoctorsPage() {
  const { currentClinicId } = useAdminClinic();
  const { data: doctors, isLoading, isError, error } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
  });
  const deleteMutation = useDeleteDoctor();
  const queryClient = useQueryClient();
  const [doctorDrawer, setDoctorDrawer] = useState<{
    mode: "create" | "edit" | "view";
    doctor: Doctor | null;
  } | null>(null);

  const openCreate = () => setDoctorDrawer({ mode: "create", doctor: null });
  const openEdit = (d: Doctor) => setDoctorDrawer({ mode: "edit", doctor: d });
  const openView = (d: Doctor) => setDoctorDrawer({ mode: "view", doctor: d });

  if (isLoading) return <PageSkeleton variant="table" rows={8} />;
  if (isError) return <Stack><ContextBar title="Врачи" /><span style={{ color: 'red' }}>{error instanceof Error ? error.message : "Ошибка"}</span></Stack>;

  return (
    <Stack>
      <ContextBar title="Врачи" actions={<Button onClick={openCreate} size="sm">Добавить врача</Button>} />
      <Text size="sm" c="dimmed" mb="sm">
        Управление специалистами клиники: ФИО, специализация, рейтинг, стаж.
      </Text>

      {doctors?.length === 0 && (
        <EmptyState
          title="Нет врачей"
          description="Добавьте первого специалиста клиники."
          icon={<IconStethoscope size={64} stroke={1} color="var(--mantine-color-gray-4)" />}
          action={{ label: "Добавить врача", onClick: openCreate }}
        />
      )}

      {doctors && doctors.length > 0 && (
        <Table striped verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>ФИО</Table.Th>
              <Table.Th>Роль</Table.Th>
              <Table.Th>Специализация</Table.Th>
              <Table.Th>Рейтинг</Table.Th>
              <Table.Th>Стаж (лет)</Table.Th>
              <Table.Th>Активен</Table.Th>
              <Table.Th>Действия</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {doctors.map((d) => (
              <Table.Tr key={d.id}>
                <Table.Td>
                  <HoverCard openDelay={300} width={240} shadow="md">
                    <HoverCard.Target>
                      <Text
                        span
                        style={{ cursor: "pointer" }}
                        onClick={() => openView(d)}
                      >
                        {d.full_name}
                      </Text>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                      <Stack gap={4}>
                        <Text size="sm" fw={500}>{d.full_name}</Text>
                        <Text size="xs" c="dimmed">Специализация: {d.specialization}</Text>
                        {d.experience_years != null && (
                          <Text size="xs" c="dimmed">Стаж: {d.experience_years} лет</Text>
                        )}
                      </Stack>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </Table.Td>
                <Table.Td>{d.display_role ?? "Специалист"}</Table.Td>
                <Table.Td>{d.specialization}</Table.Td>
                <Table.Td>{d.rating}</Table.Td>
                <Table.Td>{d.experience_years ?? "—"}</Table.Td>
                <Table.Td>{d.is_active ? "Да" : "Нет"}</Table.Td>
                <Table.Td onClick={(e) => e.stopPropagation()}>
                  <Menu position="bottom-end" shadow="sm">
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => openEdit(d)}>
                        Редактировать
                      </Menu.Item>
                      <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => openView(d)}>
                        Открыть карточку
                      </Menu.Item>
                      <Menu.Item
                        leftSection={<IconTrash size={14} />}
                        color="red"
                        onClick={() => deleteMutation.mutate(d.id)}
                      >
                        Удалить
                      </Menu.Item>
                    </Menu.Dropdown>
                  </Menu>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <DoctorEntityDrawer
        opened={doctorDrawer !== null}
        onClose={() => setDoctorDrawer(null)}
        doctor={doctorDrawer?.doctor ?? null}
        mode={doctorDrawer?.mode ?? "view"}
        onSaved={() => queryClient.invalidateQueries({ queryKey: ["doctors"] })}
      />
    </Stack>
  );
}
