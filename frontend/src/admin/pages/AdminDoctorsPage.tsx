import { useCreateDoctor, useDeleteDoctor, useDoctors, useUpdateDoctor } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Button,
  Group,
  Loader,
  Modal,
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
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { SPECIALIST_ROLE_OPTIONS } from "@/api/types";

export default function AdminDoctorsPage() {
  const { currentClinicId } = useAdminClinic();
  const { data: doctors, isLoading, isError, error } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
  });
  const createMutation = useCreateDoctor();
  const updateMutation = useUpdateDoctor();
  const deleteMutation = useDeleteDoctor();
  const [opened, { open, close }] = useDisclosure(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [fullName, setFullName] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [rating, setRating] = useState<number | undefined>(undefined);
  const [experienceYears, setExperienceYears] = useState<number | undefined>(undefined);
  const [isActive, setIsActive] = useState(true);
  const [specialistRole, setSpecialistRole] = useState<string>("doctor");
  const [specialistRoleCustomName, setSpecialistRoleCustomName] = useState("");

  const resetForm = () => {
    setEditingId(null);
    setFullName("");
    setSpecialization("");
    setPhotoUrl("");
    setRating(undefined);
    setExperienceYears(undefined);
    setIsActive(true);
    setSpecialistRole("doctor");
    setSpecialistRoleCustomName("");
  };

  const handleSave = () => {
    const rolePayload = {
      specialist_role: specialistRole,
      specialist_role_custom_name: specialistRole === "other" && specialistRoleCustomName.trim()
        ? specialistRoleCustomName.trim()
        : null,
    };
    if (editingId) {
      updateMutation.mutate(
        {
          id: editingId,
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
        { onSuccess: () => { close(); resetForm(); } }
      );
    } else {
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
        { onSuccess: () => { close(); resetForm(); } }
      );
    }
  };

  const openCreate = () => {
    resetForm();
    open();
  };

  const openEdit = (
    id: string,
    name: string,
    spec: string,
    active: boolean,
    photo?: string | null,
    ratingValue?: string,
    exp?: number | null,
    role?: string,
    roleCustomName?: string | null
  ) => {
    setEditingId(id);
    setFullName(name);
    setSpecialization(spec);
    setPhotoUrl(photo ?? "");
    setRating(ratingValue ? Number(ratingValue) : undefined);
    setExperienceYears(exp ?? undefined);
    setIsActive(active);
    setSpecialistRole(role ?? "doctor");
    setSpecialistRoleCustomName(roleCustomName ?? "");
    open();
  };

  if (isLoading) return <Loader />;
  if (isError) return <Stack><Title order={3}>Врачи</Title><span style={{ color: 'red' }}>{error instanceof Error ? error.message : "Ошибка"}</span></Stack>;

  return (
    <Stack>
      <Group justify="space-between">
        <div>
          <Title order={3}>Врачи</Title>
          <Text size="sm" c="dimmed">
            Управление специалистами клиники: ФИО, специализация, рейтинг, стаж.
          </Text>
        </div>
        <Button onClick={openCreate} size="sm">
          Добавить врача
        </Button>
      </Group>

      {doctors?.length === 0 && (
        <EmptyStateHint title="Нет врачей" subtitle="Добавьте первого врача." />
      )}

      {doctors && doctors.length > 0 && (
        <Table striped>
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
                <Table.Td>{d.full_name}</Table.Td>
                <Table.Td>{d.display_role ?? "Специалист"}</Table.Td>
                <Table.Td>{d.specialization}</Table.Td>
                <Table.Td>{d.rating}</Table.Td>
                <Table.Td>{d.experience_years ?? "—"}</Table.Td>
                <Table.Td>{d.is_active ? "Да" : "Нет"}</Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    variant="light"
                    onClick={() =>
                      openEdit(
                        d.id,
                        d.full_name,
                        d.specialization,
                        d.is_active,
                        d.photo_url,
                        d.rating,
                        d.experience_years,
                        d.specialist_role,
                        d.specialist_role_custom_name
                      )
                    }
                  >
                    Изменить
                  </Button>{" "}
                  <Button
                    size="xs"
                    variant="light"
                    color="red"
                    onClick={() => deleteMutation.mutate(d.id)}
                    loading={deleteMutation.isPending}
                  >
                    Удалить
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={opened} onClose={() => { close(); resetForm(); }} title={editingId ? "Редактировать врача" : "Новый врач"}>
        <Stack>
          <TextInput
            label="ФИО"
            placeholder="Иванов Иван Иванович"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            required
          />
          <TextInput
            label="Специализация"
            placeholder="Терапевт, хирург, ортодонт..."
            value={specialization}
            onChange={(e) => setSpecialization(e.target.value)}
            required
          />
          <TextInput
            label="Фото (URL)"
            placeholder="https://пример.ру/doctor.jpg"
            value={photoUrl}
            onChange={(e) => setPhotoUrl(e.target.value)}
          />
          <Group grow>
            <NumberInput
              label="Рейтинг"
              placeholder="4.8"
              min={0}
              max={5}
              step={0.1}
              value={rating}
              decimalScale={1}
              onChange={(value) => setRating(typeof value === "number" ? value : undefined)}
            />
            <NumberInput
              label="Стаж (лет)"
              placeholder="5"
              min={0}
              max={60}
              value={experienceYears}
              onChange={(value) => setExperienceYears(typeof value === "number" ? value : undefined)}
            />
          </Group>
          <Select
            label="Роль специалиста"
            data={SPECIALIST_ROLE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
            value={specialistRole}
            onChange={(v) => setSpecialistRole(v ?? "doctor")}
          />
          {specialistRole === "other" && (
            <TextInput
              label="Своя роль специалиста"
              placeholder="Например: Ассистент"
              value={specialistRoleCustomName}
              onChange={(e) => setSpecialistRoleCustomName(e.target.value)}
            />
          )}
          <Switch
            label="Врач активен и доступен для записи"
            checked={isActive}
            onChange={(e) => setIsActive(e.currentTarget.checked)}
          />
          <Button onClick={handleSave} loading={createMutation.isPending || updateMutation.isPending}>
            Сохранить
          </Button>
          {(createMutation.isError || updateMutation.isError) && (
            <span style={{ color: "red" }}>
              {createMutation.error instanceof Error ? createMutation.error.message : updateMutation.error instanceof Error ? updateMutation.error.message : "Ошибка"}
            </span>
          )}
        </Stack>
      </Modal>
    </Stack>
  );
}
