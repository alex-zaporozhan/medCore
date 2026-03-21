import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useAdminDiscounts,
  useCreateAdminDiscountMutation,
  useUpdateAdminDiscountMutation,
  useDeleteAdminDiscountMutation,
} from "@/hooks/useAdminDiscounts";
import type { DiscountRead, DiscountCreate } from "@/hooks/useAdminDiscounts";
import { useAdminClinicServices } from "@/hooks/useAdminClinicServices";
import { useDoctors } from "@/hooks/useDoctors";
import { AdminDrawer, DataSkeleton, QueryErrorAlert } from "@/shared/ui";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Alert,
  Badge,
  Button,
  Group,
  NumberInput,
  Paper,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";

const discountTypeLabels: Record<string, string> = {
  first_visit: "Первый визит",
  service: "По услуге",
  doctor: "По врачу",
  period: "По периоду",
};

const DISCOUNT_TYPE_OPTIONS = [
  { value: "first_visit", label: "Первый визит" },
  { value: "service", label: "По услуге" },
  { value: "doctor", label: "По врачу" },
  { value: "period", label: "По периоду" },
];

function AdminDiscountsPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const [opened, { open, close }] = useDisclosure(false);
  const [editing, setEditing] = useState<DiscountRead | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [discount_type, setDiscountType] = useState<"first_visit" | "service" | "doctor" | "period">("first_visit");
  const [service_id, setServiceId] = useState<string | null>(null);
  const [doctor_id, setDoctorId] = useState<string | null>(null);
  const [valid_from, setValidFrom] = useState("");
  const [valid_until, setValidUntil] = useState("");
  const [percent_off, setPercentOff] = useState<string | number>("");
  const [amount_off, setAmountOff] = useState<string | number>("");
  const [is_active, setIsActive] = useState(true);

  const { data: discounts, isLoading, isError, error } = useAdminDiscounts(clinicId);

  const { data: services } = useAdminClinicServices(clinicId);
  const { data: doctorsData } = useDoctors({ clinic_id: clinicId ?? undefined, is_active: true });
  const doctors = doctorsData ?? [];

  const createMut = useCreateAdminDiscountMutation(clinicId);
  const updateMut = useUpdateAdminDiscountMutation(clinicId);
  const deleteMut = useDeleteAdminDiscountMutation(clinicId);

  const resetForm = () => {
    setEditing(null);
    setSaveError(null);
    setName("");
    setDiscountType("first_visit");
    setServiceId(null);
    setDoctorId(null);
    setValidFrom("");
    setValidUntil("");
    setPercentOff("");
    setAmountOff("");
    setIsActive(true);
  };

  const handleOpenNew = () => {
    resetForm();
    setSaveError(null);
    open();
  };

  const handleOpenEdit = (d: DiscountRead) => {
    setEditing(d);
    setSaveError(null);
    setName(d.name);
    setDiscountType(d.discount_type as "first_visit" | "service" | "doctor" | "period");
    setServiceId(d.service_id);
    setDoctorId(d.doctor_id);
    setValidFrom(d.valid_from ?? "");
    setValidUntil(d.valid_until ?? "");
    setPercentOff(d.percent_off ?? "");
    setAmountOff(d.amount_off ?? "");
    setIsActive(d.is_active);
    open();
  };

  const handleCloseModal = () => {
    close();
    resetForm();
  };

  const buildPayload = (): DiscountCreate => {
    const payload: DiscountCreate = {
      name: name.trim(),
      discount_type,
      is_active,
    };
    if (discount_type === "service" && service_id) payload.service_id = service_id;
    else if (discount_type === "doctor" && doctor_id) payload.doctor_id = doctor_id;
    if (valid_from) payload.valid_from = valid_from;
    if (valid_until) payload.valid_until = valid_until;
    const pct = percent_off === "" || percent_off === null ? null : Number(percent_off);
    const amt = amount_off === "" || amount_off === null ? null : Number(amount_off);
    if (pct != null && !Number.isNaN(pct)) payload.percent_off = pct;
    if (amt != null && !Number.isNaN(amt)) payload.amount_off = amt;
    return payload;
  };

  const handleSave = () => {
    setSaveError(null);
    const payload = buildPayload();
    const onErr = (e: Error) => setSaveError(e.message);
    if (editing) {
      updateMut.mutate(
        { id: editing.id, body: payload },
        { onSuccess: () => handleCloseModal(), onError: onErr }
      );
    } else {
      createMut.mutate(payload, {
        onSuccess: () => handleCloseModal(),
        onError: onErr,
      });
    }
  };

  const serviceOptions = (services ?? []).map((s) => ({
    value: s.service.id,
    label: s.service.name,
  }));
  const doctorOptions = doctors.map((d) => ({ value: d.id, label: d.full_name ?? d.id }));

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Скидки и акции" />
        <Text c="dimmed">Выберите клинику.</Text>
      </Stack>
    );
  }
  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Скидки и акции" />
        <DataSkeleton lines={5} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack>
        <ContextBar title="Скидки и акции" />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  const items = discounts ?? [];

  return (
    <Stack gap="md">
      <ContextBar title="Скидки и акции" actions={<Button size="sm" onClick={handleOpenNew}>Добавить скидку</Button>} />
      <Text size="sm" c="dimmed" mb="sm">
        Создание и редактирование скидок. При оплате скидка применяется автоматически.
      </Text>
      <Paper p="md" radius="md" withBorder>
        {items.length === 0 ? (
          <EmptyStateHint
            title="Нет скидок"
            subtitle="Нажмите «Добавить скидку», чтобы создать первую."
          />
        ) : (
          <Table striped verticalSpacing="sm">
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Название</Table.Th>
                <Table.Th>Тип</Table.Th>
                <Table.Th>Скидка</Table.Th>
                <Table.Th>Период</Table.Th>
                <Table.Th>Активна</Table.Th>
                <Table.Th />
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {items.map((d) => (
                <Table.Tr key={d.id}>
                  <Table.Td>{d.name}</Table.Td>
                  <Table.Td>{discountTypeLabels[d.discount_type] ?? d.discount_type}</Table.Td>
                  <Table.Td>
                    {d.percent_off != null ? `${d.percent_off}%` : d.amount_off != null ? `${d.amount_off} ₽` : "—"}
                  </Table.Td>
                  <Table.Td>
                    {d.valid_from ?? "—"} … {d.valid_until ?? "—"}
                  </Table.Td>
                  <Table.Td>
                    <Badge color={d.is_active ? "green" : "gray"}>
                      {d.is_active ? "Да" : "Нет"}
                    </Badge>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs">
                      <Button size="xs" variant="light" onClick={() => handleOpenEdit(d)}>
                        Изменить
                      </Button>
                      <Button
                        size="xs"
                        variant="subtle"
                        color="red"
                        onClick={() => deleteMut.mutate(d.id)}
                        loading={deleteMut.isPending}
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
      </Paper>

      <AdminDrawer
        position="right"
        size="md"
        opened={opened}
        onClose={handleCloseModal}
        title={editing ? "Изменить скидку" : "Новая скидка"}
      >
        <Stack>
          {saveError && (
            <Alert color="red" title="Ошибка" onClose={() => setSaveError(null)} withCloseButton>
              {saveError}
            </Alert>
          )}
          <TextInput
            label="Название"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            placeholder="Например: Скидка 20% на первый визит"
          />
          <Select
            label="Тип скидки"
            data={DISCOUNT_TYPE_OPTIONS}
            value={discount_type}
            onChange={(v) => {
              setDiscountType((v as "first_visit" | "service" | "doctor" | "period") ?? "first_visit");
              if (v !== "service") setServiceId(null);
              if (v !== "doctor") setDoctorId(null);
            }}
          />
          {discount_type === "service" && (
            <Select
              label="Услуга"
              data={serviceOptions}
              value={service_id}
              onChange={setServiceId}
              clearable
              placeholder="Выберите услугу"
            />
          )}
          {discount_type === "doctor" && (
            <Select
              label="Врач"
              data={doctorOptions}
              value={doctor_id}
              onChange={setDoctorId}
              clearable
              placeholder="Выберите врача"
            />
          )}
          <Group grow>
            <TextInput
              label="Действует с"
              type="date"
              value={valid_from}
              onChange={(e) => setValidFrom(e.target.value)}
            />
            <TextInput
              label="Действует по"
              type="date"
              value={valid_until}
              onChange={(e) => setValidUntil(e.target.value)}
            />
          </Group>
          <Group grow>
            <NumberInput
              label="Скидка, %"
              min={0}
              max={100}
              value={percent_off}
              onChange={setPercentOff}
              placeholder="0–100"
            />
            <NumberInput
              label="Скидка, ₽"
              min={0}
              value={amount_off}
              onChange={setAmountOff}
              placeholder="Сумма"
            />
          </Group>
          <Text size="xs" c="dimmed">
            Укажите либо процент, либо сумму скидки.
          </Text>
          <Switch
            label="Активна"
            checked={is_active}
            onChange={(e) => setIsActive(e.currentTarget.checked)}
          />
          <Button
            onClick={handleSave}
            loading={createMut.isPending || updateMut.isPending}
            disabled={!name.trim()}
          >
            {editing ? "Сохранить" : "Создать"}
          </Button>
        </Stack>
      </AdminDrawer>
    </Stack>
  );
}

export default AdminDiscountsPage;
