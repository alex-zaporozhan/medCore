import type { Doctor } from "@/api/types";
import {
  Avatar,
  Button,
  Drawer,
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
  Table,
  Skeleton,
} from "@mantine/core";
import { IconDotsVertical, IconPrinter, IconCopy, IconTrash } from "@tabler/icons-react";
import { useWorkingHours, useAbsence } from "@/hooks/useDoctorScheduleConfig";
import { usePayrollPolicies, useSalaryTransactions } from "@/hooks/useErpPayroll";
import { useAdminClinicServices } from "@/hooks/useAdminClinicServices";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useCreateDoctor, useUpdateDoctor } from "@/hooks";
import { SPECIALIST_ROLE_OPTIONS } from "@/api/types";
import { useState, useEffect } from "react";

const WEEKDAY_LABELS: Record<number, string> = {
  0: "Вс",
  1: "Пн",
  2: "Вт",
  3: "Ср",
  4: "Чт",
  5: "Пт",
  6: "Сб",
};

export interface DoctorEntityDrawerProps {
  opened: boolean;
  onClose: () => void;
  doctor: Doctor | null;
  mode: "view" | "create" | "edit";
  onSaved?: () => void;
}

export function DoctorEntityDrawer({
  opened,
  onClose,
  doctor,
  mode,
  onSaved,
}: DoctorEntityDrawerProps) {
  const { currentClinicId } = useAdminClinic();
  const [activeTab, setActiveTab] = useState<string | null>("profile");

  const [fullName, setFullName] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [rating, setRating] = useState<number | undefined>(undefined);
  const [experienceYears, setExperienceYears] = useState<number | undefined>(undefined);
  const [isActive, setIsActive] = useState(true);
  const [specialistRole, setSpecialistRole] = useState<string>("doctor");
  const [specialistRoleCustomName, setSpecialistRoleCustomName] = useState("");

  const { data: workingHours } = useWorkingHours(doctor?.id ?? null);
  const { data: absences } = useAbsence(doctor?.id ?? null);
  const { data: payrollPolicies } = usePayrollPolicies(currentClinicId);
  const { data: salaryTransactions } = useSalaryTransactions(
    currentClinicId,
    doctor?.id ?? null,
    null,
    null
  );
  const { data: adminServices } = useAdminClinicServices(currentClinicId ?? null);
  const createMutation = useCreateDoctor();
  const updateMutation = useUpdateDoctor();

  const doctorPolicy = payrollPolicies?.find(
    (p) => p.doctor_id === doctor?.id
  );
  const servicesWithThisDoctor =
    adminServices?.filter((item) =>
      item.doctors.some((d) => d.doctor_id === doctor?.id)
    ) ?? [];

  useEffect(() => {
    if (doctor) {
      setFullName(doctor.full_name);
      setSpecialization(doctor.specialization);
      setPhotoUrl(doctor.photo_url ?? "");
      setRating(doctor.rating ? Number(doctor.rating) : undefined);
      setExperienceYears(doctor.experience_years ?? undefined);
      setIsActive(doctor.is_active);
      setSpecialistRole(doctor.specialist_role ?? "doctor");
      setSpecialistRoleCustomName(doctor.specialist_role_custom_name ?? "");
    } else {
      setFullName("");
      setSpecialization("");
      setPhotoUrl("");
      setRating(undefined);
      setExperienceYears(undefined);
      setIsActive(true);
      setSpecialistRole("doctor");
      setSpecialistRoleCustomName("");
    }
  }, [doctor]);

  const handleSave = () => {
    const rolePayload = {
      specialist_role: specialistRole,
      specialist_role_custom_name:
        specialistRole === "other" && specialistRoleCustomName.trim()
          ? specialistRoleCustomName.trim()
          : null,
    };
    if (mode === "edit" && doctor) {
      updateMutation.mutate(
        {
          id: doctor.id,
          body: {
            full_name: fullName,
            specialization,
            photo_url: photoUrl || null,
            rating: rating ?? undefined,
            experience_years: experienceYears ?? undefined,
            is_active: isActive,
            ...rolePayload,
          },
        },
        { onSuccess: () => { onSaved?.(); onClose(); } }
      );
    } else if (mode === "create") {
      createMutation.mutate(
        {
          full_name: fullName,
          specialization,
          photo_url: photoUrl || null,
          rating: rating ?? undefined,
          experience_years: experienceYears ?? undefined,
          is_active: isActive,
          ...rolePayload,
        },
        { onSuccess: () => { onSaved?.(); onClose(); } }
      );
    }
  };

  const title =
    mode === "create"
      ? "Новый врач"
      : mode === "edit"
        ? "Редактировать врача"
        : doctor?.full_name ?? "";

  return (
    <Drawer
      position="right"
      size="lg"
      opened={opened}
      onClose={onClose}
      title={title}
      styles={{ body: { paddingTop: 0 } }}
    >
      {doctor && (mode === "view" || mode === "edit") && (
        <Stack gap="md" mb="md">
          <Group justify="space-between">
            <Group>
              <Avatar
                src={doctor.photo_url}
                radius="xl"
                size="lg"
                color="teal"
              >
                {doctor.full_name.slice(0, 2).toUpperCase()}
              </Avatar>
              <Stack gap={2}>
                <Text fw={600} size="lg">
                  {doctor.full_name}
                </Text>
                <Text size="sm" c="dimmed">
                  {doctor.display_role ?? "Специалист"} · {doctor.specialization}
                </Text>
              </Stack>
            </Group>
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
          <Tabs.Tab value="profile">Профиль</Tabs.Tab>
          <Tabs.Tab value="schedule">Расписание</Tabs.Tab>
          <Tabs.Tab value="payroll">Зарплата</Tabs.Tab>
          <Tabs.Tab value="services">Услуги</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="profile" pt="md">
          <Stack gap="sm">
            <TextInput
              label="ФИО"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              required
              disabled={mode === "view"}
            />
            <TextInput
              label="Специализация"
              value={specialization}
              onChange={(e) => setSpecialization(e.target.value)}
              disabled={mode === "view"}
            />
            <TextInput
              label="Фото (URL)"
              value={photoUrl}
              onChange={(e) => setPhotoUrl(e.target.value)}
              disabled={mode === "view"}
            />
            <Group grow>
              <NumberInput
                label="Рейтинг"
                min={0}
                max={5}
                step={0.1}
                value={rating}
                decimalScale={1}
                onChange={(v) => setRating(typeof v === "number" ? v : undefined)}
                disabled={mode === "view"}
              />
              <NumberInput
                label="Стаж (лет)"
                min={0}
                max={60}
                value={experienceYears}
                onChange={(v) => setExperienceYears(typeof v === "number" ? v : undefined)}
                disabled={mode === "view"}
              />
            </Group>
            <Select
              label="Роль специалиста"
              data={SPECIALIST_ROLE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
              value={specialistRole}
              onChange={(v) => setSpecialistRole(v ?? "doctor")}
              disabled={mode === "view"}
            />
            {specialistRole === "other" && (
              <TextInput
                label="Своя роль"
                value={specialistRoleCustomName}
                onChange={(e) => setSpecialistRoleCustomName(e.target.value)}
                disabled={mode === "view"}
              />
            )}
            <Switch
              label="Активен и доступен для записи"
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
              <Text size="sm" c="red">
                {createMutation.error instanceof Error
                  ? createMutation.error.message
                  : updateMutation.error instanceof Error
                    ? updateMutation.error.message
                    : "Ошибка"}
              </Text>
            )}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="schedule" pt="md">
          {!doctor ? (
            <Text size="sm" c="dimmed">
              Сохраните врача для настройки расписания.
            </Text>
          ) : (
            <Stack gap="md">
              <Text size="sm" fw={500}>
                Рабочие часы
              </Text>
              {!workingHours ? (
                <Skeleton height={80} />
              ) : workingHours.length === 0 ? (
                <Text size="sm" c="dimmed">
                  График не задан. Настройте в разделе «Расписание врачей».
                </Text>
              ) : (
                <Table striped verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>День</Table.Th>
                      <Table.Th>Начало</Table.Th>
                      <Table.Th>Конец</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {workingHours.map((wh) => (
                      <Table.Tr key={wh.id}>
                        <Table.Td>{WEEKDAY_LABELS[wh.weekday] ?? wh.weekday}</Table.Td>
                        <Table.Td>{String(wh.start_time).slice(0, 5)}</Table.Td>
                        <Table.Td>{String(wh.end_time).slice(0, 5)}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
              <Text size="sm" fw={500}>
                Отсутствия
              </Text>
              {!absences ? (
                <Skeleton height={40} />
              ) : absences.length === 0 ? (
                <Text size="sm" c="dimmed">
                  Нет запланированных отсутствий.
                </Text>
              ) : (
                <Table striped verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>С</Table.Th>
                      <Table.Th>По</Table.Th>
                      <Table.Th>Причина</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {absences.map((a) => (
                      <Table.Tr key={a.id}>
                        <Table.Td>{a.date_from}</Table.Td>
                        <Table.Td>{a.date_to}</Table.Td>
                        <Table.Td>{a.reason ?? "—"}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Stack>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="payroll" pt="md">
          {!doctor ? (
            <Text size="sm" c="dimmed">
              Сохраните врача для просмотра зарплаты.
            </Text>
          ) : !doctorPolicy ? (
            <Text size="sm" c="dimmed">
              Схема мотивации не задана (ставка за выход, % от услуг).
            </Text>
          ) : (
            <Stack gap="sm">
              <Text size="sm">
                Ставка за выход: {doctorPolicy.fixed_per_shift}
              </Text>
              <Text size="sm">
                % от услуг: {doctorPolicy.percent_from_services}
              </Text>
              <Text size="sm">
                % от товаров: {doctorPolicy.percent_from_products}
              </Text>
              {salaryTransactions && salaryTransactions.length > 0 && (
                <Text size="sm" mt="md">
                  Начислений: {salaryTransactions.length}
                </Text>
              )}
            </Stack>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="services" pt="md">
          {!doctor ? (
            <Text size="sm" c="dimmed">
              Сохраните врача для привязки услуг.
            </Text>
          ) : servicesWithThisDoctor.length === 0 ? (
            <Text size="sm" c="dimmed">
              Услуги назначаются в карточке услуги (вкладка «Исполнители»).
            </Text>
          ) : (
            <Table striped verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Услуга</Table.Th>
                  <Table.Th>Категория</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {servicesWithThisDoctor.map((item) => (
                  <Table.Tr key={item.service.id}>
                    <Table.Td>{item.service.name}</Table.Td>
                    <Table.Td>{item.service.category}</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Tabs.Panel>
      </Tabs>
    </Drawer>
  );
}
