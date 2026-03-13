import {
  useAdminClinicServices,
  useCreateAdminClinicService,
  useUpdateAdminClinicService,
  useDeleteAdminClinicService,
  useDoctors,
} from "@/hooks";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Button,
  Group,
  Loader,
  Modal,
  MultiSelect,
  NumberInput,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";

const CATEGORIES = [
  { value: "therapy", label: "Терапия" },
  { value: "surgery", label: "Хирургия" },
  { value: "orthodontics", label: "Ортодонтия" },
  { value: "hygiene", label: "Профгигиена" },
  { value: "other", label: "Другое" },
];

export default function AdminServicesPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? undefined;

  const { data: adminServices, isLoading, isError, error } = useAdminClinicServices(clinicId ?? null);
  const { data: doctors } = useDoctors({ clinic_id: clinicId, is_active: true });
  const createMutation = useCreateAdminClinicService(clinicId ?? null);
  const updateMutation = useUpdateAdminClinicService(clinicId ?? null);
  const deleteMutation = useDeleteAdminClinicService(clinicId ?? null);

  const [opened, { open, close }] = useDisclosure(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState<number | undefined>(undefined);
  const [duration, setDuration] = useState<number | undefined>(30);
  const [isActive, setIsActive] = useState(true);
  const [doctorIds, setDoctorIds] = useState<string[]>([]);

  const doctorOptions =
    doctors?.map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  const resetForm = () => {
    setEditingId(null);
    setName("");
    setCategory(null);
    setDescription("");
    setPrice(undefined);
    setDuration(30);
    setIsActive(true);
    setDoctorIds([]);
  };

  const openCreate = () => {
    resetForm();
    open();
  };

  const openEdit = (item: { service: { id: string; name: string; category: string; description?: string | null; price: string; duration_minutes?: number; is_active: boolean }; doctors: { doctor_id: string }[] }) => {
    setEditingId(item.service.id);
    setName(item.service.name);
    setCategory(item.service.category);
    setDescription(item.service.description ?? "");
    setPrice(Number(item.service.price));
    setDuration(item.service.duration_minutes ?? 30);
    setIsActive(item.service.is_active);
    setDoctorIds(item.doctors.map((d) => d.doctor_id));
    open();
  };

  const handleSave = () => {
    if (!clinicId || !name.trim() || !category || price === undefined || !duration) return;

    const doctorsPayload = doctorIds.map((id) => ({
      doctor_id: id,
      is_active: true,
    }));

    if (editingId) {
      updateMutation.mutate(
        {
          serviceId: editingId,
          body: {
            service: {
              name,
              category,
              description: description || null,
              price,
              duration_minutes: duration,
              is_active: isActive,
            },
            doctors: doctorsPayload,
          },
        },
        {
          onSuccess: () => {
            close();
            resetForm();
          },
        }
      );
    } else {
      createMutation.mutate(
        {
          service: {
            clinic_id: clinicId,
            name,
            category,
            description: description || null,
            price,
            duration_minutes: duration,
            is_active: isActive,
          },
          doctors: doctorsPayload,
        },
        {
          onSuccess: () => {
            close();
            resetForm();
          },
        }
      );
    }
  };

  if (!clinicId) {
    return (
      <Stack>
        <Title order={3}>Услуги</Title>
        <Text size="sm" c="dimmed">
          Сначала создайте клинику и выберите её в шапке, чтобы управлять услугами.
        </Text>
      </Stack>
    );
  }

  if (isLoading) {
    return (
      <Stack>
        <Title order={3}>Услуги</Title>
        <Loader />
      </Stack>
    );
  }

  if (isError) {
    return (
      <Stack>
        <Title order={3}>Услуги</Title>
        <Text c="red">
          {error instanceof Error ? error.message : "Ошибка загрузки услуг"}
        </Text>
      </Stack>
    );
  }

  const services = adminServices ?? [];

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={3}>Услуги</Title>
          <Text size="sm" c="dimmed">
            Управляйте перечнем услуг клиники и врачами, которые их выполняют.
          </Text>
        </div>
        <Button onClick={openCreate} size="sm">
          Добавить услугу
        </Button>
      </Group>

      {services.length === 0 && (
        <EmptyStateHint
          title="Услуг ещё нет"
          subtitle="Добавьте первую услугу и назначьте врачей."
        />
      )}

      {services.length > 0 && (
        <Table striped highlightOnHover>
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
              <Table.Tr key={item.service.id}>
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
                <Table.Td>
                  <Group gap="xs">
                    <Button
                      size="xs"
                      variant="light"
                      onClick={() => openEdit(item)}
                    >
                      Изменить
                    </Button>
                    <Button
                      size="xs"
                      variant="light"
                      color="red"
                      onClick={() => deleteMutation.mutate(item.service.id)}
                      loading={deleteMutation.isPending}
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

      <Modal
        opened={opened}
        onClose={() => {
          close();
          resetForm();
        }}
        title={editingId ? "Редактировать услугу" : "Новая услуга"}
        centered
      >
        <Stack>
          <TextInput
            label="Название"
            placeholder="Например, Профессиональная гигиена"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Select
            label="Категория"
            placeholder="Выберите категорию"
            data={CATEGORIES}
            value={category}
            onChange={setCategory}
            searchable
          />
          <TextInput
            label="Описание"
            placeholder="Краткое описание услуги"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Group grow>
            <NumberInput
              label="Цена, ₽"
              placeholder="Например, 3000"
              min={0}
              value={price}
              onChange={(value) =>
                setPrice(typeof value === "number" ? value : undefined)
              }
            />
            <NumberInput
              label="Длительность, мин"
              min={1}
              max={600}
              value={duration}
              onChange={(value) =>
                setDuration(typeof value === "number" ? value : undefined)
              }
            />
          </Group>
          <MultiSelect
            label="Врачи, выполняющие услугу"
            placeholder="Выберите врачей"
            data={doctorOptions}
            value={doctorIds}
            onChange={setDoctorIds}
            searchable
          />
          <Switch
            label="Услуга активна и доступна для записи"
            checked={isActive}
            onChange={(e) => setIsActive(e.currentTarget.checked)}
          />
          <Button
            onClick={handleSave}
            loading={createMutation.isPending || updateMutation.isPending}
          >
            Сохранить
          </Button>
          {(createMutation.isError || updateMutation.isError) && (
            <Text c="red" size="sm">
              {createMutation.error instanceof Error
                ? createMutation.error.message
                : updateMutation.error instanceof Error
                  ? updateMutation.error.message
                  : "Ошибка"}
            </Text>
          )}
        </Stack>
      </Modal>
    </Stack>
  );
}
