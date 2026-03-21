import {
  useAdminPrepaymentPolicies,
  useCreatePrepaymentPolicy,
  useDeletePrepaymentPolicy,
  useUpdatePrepaymentPolicy,
} from "@/hooks/useAdminPrepayment";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useClinics, useUpdateClinicMutation } from "@/hooks";
import { AdminDrawer, EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import {
  ActionIcon,
  Button,
  Menu,
  NumberInput,
  Paper,
  Select,
  Stack,
  Switch,
  Table,
  Text,
} from "@mantine/core";
import { IconDotsVertical, IconEdit, IconTrash } from "@tabler/icons-react";
import { IconReceipt } from "@tabler/icons-react";
import { ContextBar } from "@/shared/ui/ContextBar";
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
  const updateClinic = useUpdateClinicMutation();
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
      await updateClinic.mutateAsync({
        clinicId,
        body: { prepayment_enabled: checked },
      });
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
        <ContextBar title="Предоплата" />
        <Text size="sm" c="dimmed">Выберите клинику.</Text>
      </Stack>
    );
  }
  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Предоплата" />
        <PageSkeleton variant="table" rows={6} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack>
        <ContextBar title="Предоплата" />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  const list = policies ?? [];

  return (
    <Stack>
      <ContextBar title="Предоплата" actions={<Button size="sm" onClick={() => { resetForm(); open(); }} disabled={!prepaymentEnabled}>Добавить политику</Button>} />
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
      <Text fw={500} mb="xs">Правила предоплаты</Text>
      {!prepaymentEnabled && (
        <Text size="sm" c="dimmed">Включите предоплату выше, чтобы настраивать правила (без предоплаты / частичная / полная по услугам и врачам).</Text>
      )}
      {prepaymentEnabled && list.length === 0 && (
        <EmptyState
          title="Нет политик"
          description="Добавьте правило предоплаты для клиники."
          icon={<IconReceipt size={64} stroke={1} color="var(--mantine-color-gray-4)" />}
          action={{ label: "Добавить политику", onClick: () => { resetForm(); open(); } }}
        />
      )}
      {prepaymentEnabled && list.length > 0 && (
        <Table striped verticalSpacing="sm">
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
                  <Menu position="bottom-end" shadow="sm">
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item
                        leftSection={<IconEdit size={14} />}
                        onClick={() => {
                          setEditingId(p.id);
                          setScopeType(p.scope_type);
                          setMode(p.mode);
                          setAmountType(p.amount_type);
                          setMinAmount(Number(p.min_amount));
                          setDeadlineHours(p.deadline_hours_before_visit ?? undefined);
                          setPriority(p.priority);
                          setEnabled(p.enabled);
                          open();
                        }}
                      >
                        Редактировать
                      </Menu.Item>
                      <Menu.Item leftSection={<IconTrash size={14} />} color="red" onClick={() => deleteMutation.mutate(p.id)}>
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

      <AdminDrawer position="right" size="md" opened={opened} onClose={() => { close(); resetForm(); }} title={editingId ? "Редактировать политику" : "Новая политика"}>
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
      </AdminDrawer>
    </Stack>
  );
}
