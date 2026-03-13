import {
  useAdminPrepaymentPolicies,
  useCreatePrepaymentPolicy,
  useDeletePrepaymentPolicy,
  useUpdatePrepaymentPolicy,
} from "@/hooks/useAdminPrepayment";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useClinics } from "@/hooks";
import { api } from "@/api/client";
import { useQueryClient } from "@tanstack/react-query";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Button,
  Group,
  Loader,
  Modal,
  NumberInput,
  Paper,
  Select,
  Stack,
  Switch,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";

const SCOPE_TYPES = [
  { value: "service", label: "Услуга" },
  { value: "doctor", label: "Врач" },
  { value: "doctor_service", label: "Врач+услуга" },
];
const MODES = [
  { value: "none", label: "Без предоплаты" },
  { value: "partial", label: "Частичная" },
  { value: "full", label: "Полная" },
];
const AMOUNT_TYPES = [
  { value: "fixed", label: "Фикс. сумма" },
  { value: "percent", label: "Процент" },
];

export default function AdminPrepaymentPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const queryClient = useQueryClient();
  const { data: clinicsData } = useClinics();
  const clinic = clinicId ? (clinicsData ?? []).find((c) => c.id === clinicId) : null;
  const prepaymentEnabled = clinic?.prepayment_enabled ?? false;
  const { data: policies, isLoading, isError, error } = useAdminPrepaymentPolicies(clinicId);
  const createMutation = useCreatePrepaymentPolicy(clinicId);
  const updateMutation = useUpdatePrepaymentPolicy(clinicId);
  const deleteMutation = useDeletePrepaymentPolicy(clinicId);
  const [savingSwitch, setSavingSwitch] = useState(false);
  const [opened, { open, close }] = useDisclosure(false);

  const handlePrepaymentToggle = async (checked: boolean) => {
    if (!clinicId) return;
    setSavingSwitch(true);
    try {
      await api.put(`/v1/clinics/${clinicId}`, { prepayment_enabled: checked });
      queryClient.invalidateQueries({ queryKey: ["clinics"] });
    } finally {
      setSavingSwitch(false);
    }
  };
  const [editingId, setEditingId] = useState<string | null>(null);
  const [scope_type, setScopeType] = useState<string | null>("service");
  const [mode, setMode] = useState<string | null>("partial");
  const [amount_type, setAmountType] = useState<string | null>("fixed");
  const [min_amount, setMinAmount] = useState<number>(0);
  const [deadline_hours, setDeadlineHours] = useState<number | undefined>(24);
  const [priority, setPriority] = useState<number>(0);
  const [enabled, setEnabled] = useState(true);

  const resetForm = () => {
    setEditingId(null);
    setScopeType("service");
    setMode("partial");
    setAmountType("fixed");
    setMinAmount(0);
    setDeadlineHours(24);
    setPriority(0);
    setEnabled(true);
  };

  const handleSave = () => {
    if (!clinicId || !scope_type || !mode || !amount_type) return;
    if (editingId) {
      updateMutation.mutate(
        {
          policyId: editingId,
          body: {
            scope_type,
            mode,
            amount_type,
            min_amount: String(min_amount),
            deadline_hours_before_visit: deadline_hours ?? null,
            priority,
            enabled,
          },
        },
        { onSuccess: () => { close(); resetForm(); } }
      );
    } else {
      createMutation.mutate(
        {
          clinic_id: clinicId,
          scope_type,
          mode,
          amount_type,
          min_amount: String(min_amount),
          deadline_hours_before_visit: deadline_hours ?? null,
          priority,
          enabled,
        },
        { onSuccess: () => { close(); resetForm(); } }
      );
    }
  };

  if (!clinicId) {
    return (
      <Stack>
        <Title order={3}>Предоплата</Title>
        <Text size="sm" c="dimmed">Выберите клинику.</Text>
      </Stack>
    );
  }
  if (isLoading) return <Loader />;
  if (isError) return <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>;

  const list = policies ?? [];

  return (
    <Stack>
      <Title order={3}>Предоплата</Title>
      <Paper p="md" withBorder>
        <Stack gap="xs">
          <Switch
            label="Предоплата включена для клиники"
            description={prepaymentEnabled ? "При записи запрашивается оплата по правилам ниже." : "При записи оплата не запрашивается, запись подтверждается сразу."}
            checked={prepaymentEnabled}
            onChange={(e) => handlePrepaymentToggle(e.currentTarget.checked)}
            disabled={savingSwitch}
          />
        </Stack>
      </Paper>
      <Group justify="space-between">
        <Text fw={500}>Правила предоплаты</Text>
        <Button onClick={() => { resetForm(); open(); }} size="sm" disabled={!prepaymentEnabled}>Добавить политику</Button>
      </Group>
      {!prepaymentEnabled && (
        <Text size="sm" c="dimmed">Включите предоплату выше, чтобы настраивать правила (без предоплаты / частичная / полная по услугам и врачам).</Text>
      )}
      {prepaymentEnabled && list.length === 0 && (
        <EmptyStateHint title="Нет политик" subtitle="Добавьте правило предоплаты для клиники." />
      )}
      {prepaymentEnabled && list.length > 0 && (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Область</Table.Th>
              <Table.Th>Режим</Table.Th>
              <Table.Th>Тип суммы</Table.Th>
              <Table.Th>Мин. сумма</Table.Th>
              <Table.Th>Приоритет</Table.Th>
              <Table.Th>Вкл.</Table.Th>
              <Table.Th>Действия</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((p) => (
              <Table.Tr key={p.id}>
                <Table.Td>{p.scope_type}</Table.Td>
                <Table.Td>{p.mode}</Table.Td>
                <Table.Td>{p.amount_type}</Table.Td>
                <Table.Td>{p.min_amount}</Table.Td>
                <Table.Td>{p.priority}</Table.Td>
                <Table.Td>{p.enabled ? "Да" : "Нет"}</Table.Td>
                <Table.Td>
                  <Group gap="xs">
                    <Button size="xs" variant="light" onClick={() => {
                      setEditingId(p.id);
                      setScopeType(p.scope_type);
                      setMode(p.mode);
                      setAmountType(p.amount_type);
                      setMinAmount(Number(p.min_amount));
                      setDeadlineHours(p.deadline_hours_before_visit ?? undefined);
                      setPriority(p.priority);
                      setEnabled(p.enabled);
                      open();
                    }}>Изменить</Button>
                    <Button size="xs" variant="light" color="red" onClick={() => deleteMutation.mutate(p.id)}>Удалить</Button>
                  </Group>
                </Table.Td>
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      )}

      <Modal opened={opened} onClose={() => { close(); resetForm(); }} title={editingId ? "Редактировать политику" : "Новая политика"}>
        <Stack>
          <Select label="Область" data={SCOPE_TYPES} value={scope_type} onChange={setScopeType} />
          <Select label="Режим" data={MODES} value={mode} onChange={setMode} />
          <Select label="Тип суммы" data={AMOUNT_TYPES} value={amount_type} onChange={setAmountType} />
          <NumberInput label="Мин. сумма, ₽" value={min_amount} onChange={(v) => setMinAmount(Number(v) || 0)} min={0} />
          <NumberInput label="Дедлайн, ч до визита" value={deadline_hours} onChange={(v) => setDeadlineHours(typeof v === "number" ? v : undefined)} min={0} />
          <NumberInput label="Приоритет" value={priority} onChange={(v) => setPriority(Number(v) || 0)} />
          <Switch label="Включена" checked={enabled} onChange={(e) => setEnabled(e.currentTarget.checked)} />
          <Button onClick={handleSave} loading={createMutation.isPending || updateMutation.isPending}>Сохранить</Button>
        </Stack>
      </Modal>
    </Stack>
  );
}
