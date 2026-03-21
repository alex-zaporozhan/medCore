import { useAdminClinicServices, useDeleteAdminClinicService, useDoctors } from "@/hooks";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { ContextBar } from "@/shared/ui/ContextBar";
import { EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { ActionIcon, Button, Menu, Stack, Table, Text } from "@mantine/core";
import { IconClipboardList, IconDotsVertical, IconEdit, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { ServiceEntityDrawer } from "@/admin/components/entity/ServiceEntityDrawer";
import type { AdminServiceRead } from "@/api/types";
import { useQueryClient } from "@tanstack/react-query";

export default function AdminServicesPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? undefined;

  const { data: adminServices, isLoading, isError, error } = useAdminClinicServices(clinicId ?? null);
  const { data: doctors } = useDoctors({ clinic_id: clinicId, is_active: true });
  const deleteMutation = useDeleteAdminClinicService(clinicId ?? null);
  const queryClient = useQueryClient();
  const [serviceDrawer, setServiceDrawer] = useState<{
    mode: "create" | "edit" | "view";
    item: AdminServiceRead | null;
  } | null>(null);

  const openCreate = () => setServiceDrawer({ mode: "create", item: null });
  const openEdit = (row: AdminServiceRead) => setServiceDrawer({ mode: "edit", item: row });
  const openView = (row: AdminServiceRead) => setServiceDrawer({ mode: "view", item: row });

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Услуги" />
        <Text size="sm" c="dimmed">
          Сначала создайте клинику и выберите её в шапке, чтобы управлять услугами.
        </Text>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Услуги" />
        <PageSkeleton variant="table" rows={8} />
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <ContextBar title="Услуги" />
        <QueryErrorAlert error={error} title="Не удалось загрузить услуги" />
      </Stack>
    );
  }

  const services = adminServices ?? [];

  return (
    <Stack>
      <ContextBar title="Услуги" actions={<Button onClick={openCreate} size="sm">Добавить услугу</Button>} />
      <Text size="sm" c="dimmed" mb="sm">
        Управляйте перечнем услуг клиники и врачами, которые их выполняют.
      </Text>

      {services.length === 0 && (
        <EmptyState
          title="Услуг ещё нет"
          description="Добавьте первую услугу и назначьте врачей."
          icon={<IconClipboardList size={64} stroke={1} color="var(--mantine-color-gray-4)" />}
          action={{ label: "Добавить услугу", onClick: openCreate }}
        />
      )}

      {services.length > 0 && (
        <Table striped highlightOnHover verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Категория</Table.Th>
              <Table.Th>Цена</Table.Th>
              <Table.Th>Длительность</Table.Th>
              <Table.Th>Врачи</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th w={160}>Действия</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {services.map((item) => (
              <Table.Tr
                key={item.service.id}
                style={{ cursor: "pointer" }}
                onClick={() => openView(item)}
              >
                <Table.Td>{item.service.name}</Table.Td>
                <Table.Td>{item.service.category}</Table.Td>
                <Table.Td>
                  {item.service.has_active_discount && item.service.base_price && item.service.effective_price ? (
                    <>
                      <Text span td="line-through" mr="xs">
                        {item.service.base_price} ₽
                      </Text>
                      <Text span fw={500}>
                        {item.service.effective_price} ₽
                      </Text>
                    </>
                  ) : (
                    `${item.service.effective_price ?? item.service.price} ₽`
                  )}
                </Table.Td>
                <Table.Td>{item.service.duration_minutes ?? 0} мин</Table.Td>
                <Table.Td>
                  {item.doctors.length === 0
                    ? "—"
                    : item.doctors
                        .map(
                          (d) =>
                            doctors?.find((doc) => doc.id === d.doctor_id)
                              ?.full_name ?? "—"
                        )
                        .join(", ")}
                </Table.Td>
                <Table.Td>{item.service.is_active ? "Активна" : "Скрыта"}</Table.Td>
                <Table.Td onClick={(e) => e.stopPropagation()}>
                  <Menu position="bottom-end" shadow="sm">
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => openEdit(item)}>
                        Редактировать
                      </Menu.Item>
                      <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => openView(item)}>
                        Открыть карточку
                      </Menu.Item>
                      <Menu.Item
                        leftSection={<IconTrash size={14} />}
                        color="red"
                        onClick={() => deleteMutation.mutate(item.service.id)}
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

      <ServiceEntityDrawer
        opened={serviceDrawer !== null}
        onClose={() => setServiceDrawer(null)}
        item={serviceDrawer?.item ?? null}
        mode={serviceDrawer?.mode ?? "view"}
        onSaved={() =>
          queryClient.invalidateQueries({
            queryKey: ["admin", "clinics", clinicId, "services"],
          })
        }
      />
    </Stack>
  );
}
