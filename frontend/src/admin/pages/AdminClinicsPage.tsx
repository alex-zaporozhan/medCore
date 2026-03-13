import { useClinics } from "@/hooks";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import {
  Button,
  Group,
  Modal,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";
import type { Clinic } from "@/api/types";
import { BUSINESS_TYPE_OPTIONS } from "@/api/types";
import { api } from "@/api/client";

interface ClinicFormState {
  id?: string;
  name: string;
  phone: string;
  email: string;
  address: string;
  business_type: string;
  business_type_custom_name: string;
   person_label_singular: string;
   person_label_plural: string;
   staff_label_plural: string;
}

export default function AdminClinicsPage() {
  const { data, isLoading, isError, error, refetch } = useClinics();
  const [opened, { open, close }] = useDisclosure(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState<ClinicFormState>({
    name: "",
    phone: "",
    email: "",
    address: "",
    business_type: "stomatology",
    business_type_custom_name: "",
    person_label_singular: "",
    person_label_plural: "",
    staff_label_plural: "",
  });

  const clinics = data ?? [];

  const handleEdit = (clinic: Clinic) => {
    setForm({
      id: clinic.id,
      name: clinic.name,
      phone: clinic.phone ?? "",
      email: clinic.email ?? "",
      address: clinic.address ?? "",
      business_type: clinic.business_type ?? "stomatology",
      business_type_custom_name: clinic.business_type_custom_name ?? "",
      person_label_singular: clinic.person_label_singular ?? "",
      person_label_plural: clinic.person_label_plural ?? "",
      staff_label_plural: clinic.staff_label_plural ?? "",
    });
    open();
  };

  const handleCreate = () => {
    setForm({
      name: "",
      phone: "",
      email: "",
      address: "",
      business_type: "stomatology",
      business_type_custom_name: "",
      person_label_singular: "",
      person_label_plural: "",
      staff_label_plural: "",
    });
    open();
  };

  const handleSubmit = async () => {
    if (!form.name.trim()) return;
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        phone: form.phone.trim() || null,
        email: form.email.trim() || null,
        address: form.address.trim() || null,
        business_type: form.business_type,
        business_type_custom_name: form.business_type === "other" && form.business_type_custom_name.trim()
          ? form.business_type_custom_name.trim()
          : null,
        person_label_singular: form.person_label_singular.trim() || null,
        person_label_plural: form.person_label_plural.trim() || null,
        staff_label_plural: form.staff_label_plural.trim() || null,
      };
      if (form.id) {
        await api.put(`/v1/clinics/${form.id}`, payload);
      } else {
        await api.post("/v1/clinics", payload);
      }
      await refetch();
      close();
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <Stack>
        <Title order={3}>Клиники</Title>
        <DataSkeleton card />
      </Stack>
    );
  }

  if (isError) {
    const message = error instanceof Error ? error.message : "Ошибка загрузки";
    return (
      <Stack>
        <Title order={3}>Клиники</Title>
        <Text c="red">{message}</Text>
      </Stack>
    );
  }

  return (
    <Stack gap="md">
      <Group justify="space-between">
        <Title order={3}>Клиники</Title>
        <Button onClick={handleCreate}>Добавить клинику</Button>
      </Group>

      {clinics.length === 0 ? (
        <Text size="sm" c="dimmed">
          Ещё нет ни одной клиники. Добавьте первую, чтобы начать работу с системой.
        </Text>
      ) : (
        <Table striped highlightOnHover withColumnBorders>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Название</Table.Th>
              <Table.Th>Адрес</Table.Th>
              <Table.Th>Телефон</Table.Th>
              <Table.Th>E‑mail</Table.Th>
              <Table.Th>Тип / лексика</Table.Th>
              <Table.Th w={120}></Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {clinics.map((clinic) => (
              <Table.Tr key={clinic.id}>
                <Table.Td>{clinic.name}</Table.Td>
                <Table.Td>{clinic.address ?? "—"}</Table.Td>
                <Table.Td>{clinic.phone ?? "—"}</Table.Td>
                <Table.Td>{clinic.email ?? "—"}</Table.Td>
                <Table.Td>
                  {clinic.business_lexicon
                    ? `${clinic.business_lexicon.person_label_plural} / ${clinic.business_lexicon.staff_label_plural}`
                    : "—"}
                </Table.Td>
                <Table.Td>
                  <Button
                    size="xs"
                    variant="subtle"
                    onClick={() => handleEdit(clinic)}
                  >
                    Редактировать
                  </Button>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal
        opened={opened}
        onClose={close}
        title={form.id ? "Редактирование клиники" : "Новая клиника"}
        centered
      >
        <Stack>
          <TextInput
            label="Название"
            required
            value={form.name}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, name: e.target.value }))
            }
          />
          <TextInput
            label="Телефон"
            value={form.phone}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, phone: e.target.value }))
            }
          />
          <TextInput
            label="E‑mail"
            value={form.email}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, email: e.target.value }))
            }
          />
          <TextInput
            label="Адрес"
            value={form.address}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, address: e.target.value }))
            }
          />
          <Select
            label="Тип бизнеса"
            data={BUSINESS_TYPE_OPTIONS.map((o) => ({ value: o.value, label: o.label }))}
            value={form.business_type}
            onChange={(v) =>
              setForm((prev) => ({ ...prev, business_type: v ?? "stomatology" }))
            }
          />
          {form.business_type === "other" && (
            <TextInput
              label="Свой тип бизнеса"
              placeholder="Например: Барбершоп+тату"
              value={form.business_type_custom_name}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, business_type_custom_name: e.target.value }))
              }
            />
          )}
          <TextInput
            label="Как называть клиента (ед. число)"
            placeholder="Пациент / Клиент"
            value={form.person_label_singular}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, person_label_singular: e.target.value }))
            }
          />
          <TextInput
            label="Как называть клиентов (мн. число)"
            placeholder="Пациенты / Клиенты"
            value={form.person_label_plural}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, person_label_plural: e.target.value }))
            }
          />
          <TextInput
            label="Как называть специалистов (списком)"
            placeholder="Врачи / Мастера / Специалисты"
            value={form.staff_label_plural}
            onChange={(e) =>
              setForm((prev) => ({ ...prev, staff_label_plural: e.target.value }))
            }
          />
          <Group justify="flex-end" mt="md">
            <Button variant="default" onClick={close}>
              Отмена
            </Button>
            <Button onClick={handleSubmit} loading={saving}>
              Сохранить
            </Button>
          </Group>
        </Stack>
      </Modal>
    </Stack>
  );
}

