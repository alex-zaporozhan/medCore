import type { AdminServiceRead } from "@/api/types";
import { AdminDrawer, QueryErrorAlert } from "@/shared/ui";
import {
  Button,
  Group,
  Menu,
  ActionIcon,
  Stack,
  Tabs,
  Text,
  TextInput,
  NumberInput,
  Select,
  Switch,
  MultiSelect,
  Table,
  Skeleton,
} from "@mantine/core";
import { IconDotsVertical, IconPrinter, IconCopy, IconTrash } from "@tabler/icons-react";
import { useServiceConsumables } from "@/hooks/useErpInventory";
import { useCreateAdminClinicService, useUpdateAdminClinicService } from "@/hooks";
import { useDoctors } from "@/hooks/useDoctors";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useState, useEffect } from "react";

const CATEGORIES = [
  { value: "therapy", label: "Терапия" },
  { value: "surgery", label: "Хирургия" },
  { value: "orthodontics", label: "Ортодонтия" },
  { value: "hygiene", label: "Профгигиена" },
  { value: "other", label: "Другое" },
];

export interface ServiceEntityDrawerProps {
  opened: boolean;
  onClose: () => void;
  /** Null for create mode */
  item: AdminServiceRead | null;
  mode: "create" | "edit" | "view";
  onSaved?: () => void;
}

export function ServiceEntityDrawer({
  opened,
  onClose,
  item,
  mode,
  onSaved,
}: ServiceEntityDrawerProps) {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? undefined;
  const service = item?.service;
  const serviceId = service?.id ?? null;

  const [activeTab, setActiveTab] = useState<string | null>("description");
  const [name, setName] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [description, setDescription] = useState("");
  const [price, setPrice] = useState<number | undefined>(undefined);
  const [duration, setDuration] = useState<number | undefined>(30);
  const [isActive, setIsActive] = useState(true);
  const [doctorIds, setDoctorIds] = useState<string[]>([]);
  const [onlineBookable, setOnlineBookable] = useState(false);
  const [onlineDescription, setOnlineDescription] = useState("");
  const [prepaymentRequired, setPrepaymentRequired] = useState(false);

  const { data: consumables } = useServiceConsumables(
    currentClinicId,
    serviceId
  );
  const { data: doctors } = useDoctors({ clinic_id: clinicId, is_active: true });
  const createMutation = useCreateAdminClinicService(clinicId ?? null);
  const updateMutation = useUpdateAdminClinicService(clinicId ?? null);

  const doctorOptions =
    doctors?.map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  useEffect(() => {
    if (service) {
      setName(service.name);
      setCategory(service.category);
      setDescription(service.description ?? "");
      setPrice(Number(service.price));
      setDuration(service.duration_minutes ?? 30);
      setIsActive(service.is_active);
      setDoctorIds(item!.doctors.map((d) => d.doctor_id));
    } else {
      setName("");
      setCategory(null);
      setDescription("");
      setPrice(undefined);
      setDuration(30);
      setIsActive(true);
      setDoctorIds([]);
      setOnlineBookable(false);
      setOnlineDescription("");
      setPrepaymentRequired(false);
    }
  }, [service?.id, item]);

  const handleSave = () => {
    if (!clinicId || !name.trim() || !category || price === undefined || duration == null) return;
    const doctorsPayload = doctorIds.map((id) => ({
      doctor_id: id,
      is_active: true,
    }));
    if (mode === "edit" && serviceId) {
      updateMutation.mutate(
        {
          serviceId,
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
        { onSuccess: () => { onSaved?.(); onClose(); } }
      );
    } else if (mode === "create") {
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
        { onSuccess: () => { onSaved?.(); onClose(); } }
      );
    }
  };

  const title =
    mode === "create"
      ? "Новая услуга"
      : mode === "edit"
        ? "Редактировать услугу"
        : service?.name ?? "";

  return (
    <AdminDrawer
      position="right"
      size="lg"
      opened={opened}
      onClose={onClose}
      title={title}
      styles={{ body: { paddingTop: 0 } }}
    >
      {service && (mode === "view" || mode === "edit") && (
        <Stack gap="xs" mb="md">
          <Group justify="flex-end">
            <Menu position="bottom-end">
              <Menu.Target>
                <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                  <IconDotsVertical size={16} />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item leftSection={<IconPrinter size={14} />}>Печать</Menu.Item>
                <Menu.Item leftSection={<IconCopy size={14} />}>Скопировать</Menu.Item>
                <Menu.Item leftSection={<IconTrash size={14} />} color="red">
                  Удалить
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Stack>
      )}

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="description">Описание</Tabs.Tab>
          <Tabs.Tab value="executors">Исполнители</Tabs.Tab>
          <Tabs.Tab value="technocard">Техкарта</Tabs.Tab>
          <Tabs.Tab value="online">Онлайн-запись</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="description" pt="md">
          <Stack gap="sm">
            <TextInput
              label="Название"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              disabled={mode === "view"}
            />
            <Select
              label="Категория"
              data={CATEGORIES}
              value={category}
              onChange={setCategory}
              searchable
              disabled={mode === "view"}
            />
            <TextInput
              label="Описание"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              disabled={mode === "view"}
            />
            <Group grow>
              <NumberInput
                label="Цена, ₽"
                min={0}
                value={price}
                onChange={(v) => setPrice(typeof v === "number" ? v : undefined)}
                disabled={mode === "view"}
              />
              <NumberInput
                label="Длительность, мин"
                min={1}
                max={600}
                value={duration}
                onChange={(v) => setDuration(typeof v === "number" ? v : undefined)}
                disabled={mode === "view"}
              />
            </Group>
            <Switch
              label="Услуга активна"
              checked={isActive}
              onChange={(e) => setIsActive(e.currentTarget.checked)}
              disabled={mode === "view"}
            />
            <Text size="xs" c="dimmed">
              Цвет в календаре — при наличии API.
            </Text>
            {mode !== "view" && (
              <Group mt="sm">
                <Button
                  onClick={handleSave}
                  loading={createMutation.isPending || updateMutation.isPending}
                >
                  Сохранить
                </Button>
                <Button variant="subtle" onClick={onClose}>
                  Отмена
                </Button>
              </Group>
            )}
            {(createMutation.isError || updateMutation.isError) && (
              <QueryErrorAlert
                error={
                  createMutation.isError ? createMutation.error : updateMutation.error
                }
                title="Не удалось сохранить услугу"
              />
            )}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="executors" pt="md">
          {!service ? (
            <Text size="sm" c="dimmed">
              Сохраните услугу, чтобы назначить исполнителей.
            </Text>
          ) : (
            <Stack gap="sm">
              {mode === "view" ? (
                <Text size="sm">
                  {item?.doctors.length
                    ? item.doctors
                        .map(
                          (d) =>
                            doctors?.find((x) => x.id === d.doctor_id)?.full_name ?? d.doctor_id
                        )
                        .join(", ")
                    : "Не назначены"}
                </Text>
              ) : (
                <MultiSelect
                  label="Врачи, выполняющие услугу"
                  data={doctorOptions}
                  value={doctorIds}
                  onChange={setDoctorIds}
                  searchable
                  placeholder="Выберите врачей"
                />
              )}
            </Stack>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="technocard" pt="md">
          {!service ? (
            <Text size="sm" c="dimmed">
              Сохраните услугу для настройки техкарты.
            </Text>
          ) : !consumables ? (
            <Skeleton height={80} />
          ) : consumables.length === 0 ? (
            <Text size="sm" c="dimmed">
              Расходники не заданы. Product + Amount (CRUD) — при расширении API.
            </Text>
          ) : (
            <Table striped verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Материал</Table.Th>
                  <Table.Th>Кол-во</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {consumables.map((c) => (
                  <Table.Tr key={c.id}>
                    <Table.Td>{c.product_id}</Table.Td>
                    <Table.Td>
                      {c.quantity_per_service} {c.unit}
                    </Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="online" pt="md">
          {!service ? (
            <Text size="sm" c="dimmed">
              Сохраните услугу для настройки онлайн-записи.
            </Text>
          ) : (
            <Stack gap="sm">
              <Switch
                label="Доступна для онлайн-записи"
                checked={onlineBookable}
                onChange={(e) => setOnlineBookable(e.currentTarget.checked)}
                disabled={mode === "view"}
              />
              <TextInput
                label="Описание для клиента"
                value={onlineDescription}
                onChange={(e) => setOnlineDescription(e.target.value)}
                placeholder="Краткое описание при выборе услуги"
                disabled={mode === "view"}
              />
              <Switch
                label="Обязательна предоплата"
                checked={prepaymentRequired}
                onChange={(e) => setPrepaymentRequired(e.currentTarget.checked)}
                disabled={mode === "view"}
              />
              <Text size="xs" c="dimmed">
                Сохранение настроек онлайн-записи — при наличии API.
              </Text>
            </Stack>
          )}
        </Tabs.Panel>
      </Tabs>
    </AdminDrawer>
  );
}
