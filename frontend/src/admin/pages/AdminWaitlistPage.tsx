import {
  useAdminWaitlistEntries,
  useAdminQueuePolicy,
  useCreateWaitlistEntry,
  useDeleteWaitlistEntry,
  useUpdateWaitlistEntry,
  useUpsertQueuePolicy,
  useDoctors,
  usePatients,
  type WaitlistEntryRead,
} from "@/hooks";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { ContextBar } from "@/shared/ui/ContextBar";
import { ClinicSelector } from "@/admin/components/ClinicSelector";
import { AdminDrawer, EmptyState, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import {
  ActionIcon,
  Button,
  Group,
  Menu,
  NumberInput,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { IconDotsVertical, IconEdit, IconTrash } from "@tabler/icons-react";
import { IconListSearch } from "@tabler/icons-react";
import { useDisclosure } from "@mantine/hooks";
import { useEffect, useState } from "react";

function formatDate(s: string | null): string {
  if (!s) return "—";
  return s.slice(0, 10);
}
function formatTime(s: string | null): string {
  if (!s) return "—";
  return s.slice(0, 5);
}

interface EditWaitlistEntryFormProps {
  entry: WaitlistEntryRead;
  patientOptions: { value: string; label: string }[];
  doctorOptions: { value: string; label: string }[];
  statusOptions: { value: string; label: string }[];
  onSave: (body: {
    patient_id?: string;
    doctor_id?: string | null;
    preferred_date?: string | null;
    preferred_time?: string | null;
    priority?: number;
    status?: string;
  }) => void;
  onCancel: () => void;
  isLoading: boolean;
}

function EditWaitlistEntryForm({
  entry,
  patientOptions,
  doctorOptions,
  statusOptions,
  onSave,
  onCancel,
  isLoading,
}: EditWaitlistEntryFormProps) {
  const [patientId, setPatientId] = useState(entry.patient_id);
  const [doctorId, setDoctorId] = useState<string | null>(entry.doctor_id ?? null);
  const [priority, setPriority] = useState(entry.priority);
  const [status, setStatus] = useState(entry.status);
  const [preferredDate, setPreferredDate] = useState(formatDate(entry.preferred_date) || "");
  const [preferredTime, setPreferredTime] = useState(formatTime(entry.preferred_time) || "");
  const handleSubmit = () => {
    const timeForApi = preferredTime ? (preferredTime.length === 5 ? `${preferredTime}:00` : preferredTime) : undefined;
    onSave({
      patient_id: patientId,
      doctor_id: doctorId ?? undefined,
      priority,
      status,
      preferred_date: preferredDate || undefined,
      preferred_time: timeForApi,
    });
  };
  return (
    <Stack>
      <Select label="Пациент" data={patientOptions} value={patientId} onChange={(v) => setPatientId(v ?? "")} searchable />
      <Select label="Врач" data={doctorOptions} value={doctorId} onChange={setDoctorId} clearable placeholder="Любой" />
      <TextInput label="Дата" type="date" value={preferredDate} onChange={(e) => setPreferredDate(e.target.value || "")} />
      <TextInput label="Время" type="time" value={preferredTime} onChange={(e) => setPreferredTime(e.target.value || "")} />
      <NumberInput label="Приоритет" value={priority} onChange={(v) => setPriority(Number(v) || 0)} />
      <Select label="Статус" data={statusOptions} value={status} onChange={(v) => setStatus(v ?? "waiting")} />
      <Group justify="flex-end" mt="md">
        <Button variant="subtle" onClick={onCancel}>Отмена</Button>
        <Button onClick={handleSubmit} loading={isLoading}>Сохранить</Button>
      </Group>
    </Stack>
  );
}

export default function AdminWaitlistPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const { data: entries, isLoading, isError, error } = useAdminWaitlistEntries(clinicId);
  const { data: queuePolicy } = useAdminQueuePolicy(clinicId);
  const createEntryMutation = useCreateWaitlistEntry(clinicId);
  const updateEntryMutation = useUpdateWaitlistEntry(clinicId);
  const deleteEntryMutation = useDeleteWaitlistEntry(clinicId);
  const upsertPolicyMutation = useUpsertQueuePolicy(clinicId);
  const { data: doctors } = useDoctors({ clinic_id: clinicId ?? undefined });
  const { data: patients } = usePatients({ clinic_id: clinicId ?? undefined });
  const [opened, { open, close }] = useDisclosure(false);
  const [editEntry, setEditEntry] = useState<WaitlistEntryRead | null>(null);
  const [patientId, setPatientId] = useState("");
  const [doctorId, setDoctorId] = useState<string | null>(null);
  const [priority, setPriority] = useState(0);
  const [preferredDate, setPreferredDate] = useState("");
  const [preferredTime, setPreferredTime] = useState("");
  const [policyMode, setPolicyMode] = useState("sequential");
  const [broadcastSize, setBroadcastSize] = useState(5);
  const [timeoutMins, setTimeoutMins] = useState(60);
  useEffect(() => {
    if (queuePolicy) {
      setPolicyMode(queuePolicy.mode);
      setBroadcastSize(queuePolicy.broadcast_size);
      setTimeoutMins(queuePolicy.response_timeout_minutes);
    }
  }, [queuePolicy]);

  const handleAddEntry = () => {
    if (!clinicId || !patientId || !preferredDate) return;
    const timeForApi = preferredTime ? (preferredTime.length === 5 ? `${preferredTime}:00` : preferredTime) : undefined;
    createEntryMutation.mutate(
      {
        clinic_id: clinicId,
        patient_id: patientId,
        doctor_id: doctorId ?? undefined,
        priority,
        preferred_date: preferredDate,
        preferred_time: timeForApi ?? undefined,
      },
      {
        onSuccess: () => {
          close();
          setPatientId("");
          setDoctorId(null);
          setPriority(0);
          setPreferredDate("");
          setPreferredTime("");
        },
      }
    );
  };

  const handleSavePolicy = () => {
    if (!clinicId) return;
    upsertPolicyMutation.mutate({
      mode: policyMode,
      broadcast_size: broadcastSize,
      response_timeout_minutes: timeoutMins,
    });
  };

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar
          title="Очередь ожидания"
          breadcrumbs={<ClinicSelector variant="compact" />}
        />
        <Text size="sm" c="dimmed">Выберите клинику.</Text>
      </Stack>
    );
  }
  if (isLoading) {
    return (
      <Stack>
        <ContextBar title="Очередь ожидания" breadcrumbs={<ClinicSelector variant="compact" />} />
        <PageSkeleton variant="table" rows={8} />
      </Stack>
    );
  }
  if (isError) {
    return (
      <Stack>
        <ContextBar title="Очередь ожидания" breadcrumbs={<ClinicSelector variant="compact" />} />
        <QueryErrorAlert error={error} />
      </Stack>
    );
  }

  const list = entries ?? [];
  const patientOptions = patients?.map((p) => ({ value: p.id, label: p.full_name ? `${p.phone} — ${p.full_name}` : p.phone })) ?? [];
  const doctorOptions = doctors?.map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  return (
    <Stack>
      <ContextBar
        title="Очередь ожидания"
        breadcrumbs={<ClinicSelector variant="compact" />}
        actions={<Button onClick={open} size="sm">Добавить в очередь</Button>}
      />

      <Stack gap="xs">
        <Text size="sm" fw={500}>Политика очереди</Text>
        <Group align="flex-end">
          <Select
            label="Режим"
            data={[
              { value: "sequential", label: "По одному" },
              { value: "broadcast", label: "Нескольким" },
            ]}
            value={policyMode}
            onChange={(v) => setPolicyMode(v ?? "sequential")}
            w={160}
          />
          <NumberInput label="Размер рассылки" value={broadcastSize} onChange={(v) => setBroadcastSize(Number(v) || 5)} min={1} w={120} />
          <NumberInput label="Таймаут, мин" value={timeoutMins} onChange={(v) => setTimeoutMins(Number(v) || 60)} min={1} w={120} />
          <Button onClick={handleSavePolicy} loading={upsertPolicyMutation.isPending}>Сохранить</Button>
        </Group>
      </Stack>

      <Text size="sm" c="dimmed" mb="xs">Записи в очереди</Text>
      {list.length === 0 && (
        <EmptyState
          title="Очередь пуста"
          description="Добавьте пациента в очередь ожидания."
          icon={<IconListSearch size={64} stroke={1} color="var(--mantine-color-gray-4)" />}
          action={{ label: "Добавить в очередь", onClick: open }}
        />
      )}
      {list.length > 0 && (
        <Table striped verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Пациент</Table.Th>
              <Table.Th>Врач</Table.Th>
              <Table.Th>Дата</Table.Th>
              <Table.Th>Время</Table.Th>
              <Table.Th>Приоритет</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Действия</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {list.map((e) => (
              <Table.Tr key={e.id}>
                <Table.Td>{patientOptions.find((p) => p.value === e.patient_id)?.label ?? "—"}</Table.Td>
                <Table.Td>{e.doctor_id ? doctorOptions.find((d) => d.value === e.doctor_id)?.label ?? "—" : "—"}</Table.Td>
                <Table.Td>{formatDate(e.preferred_date)}</Table.Td>
                <Table.Td>{formatTime(e.preferred_time)}</Table.Td>
                <Table.Td>{e.priority}</Table.Td>
                <Table.Td>{e.status}</Table.Td>
                <Table.Td>
                  <Menu position="bottom-end" shadow="sm">
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item leftSection={<IconEdit size={14} />} onClick={() => setEditEntry(e)}>
                        Редактировать
                      </Menu.Item>
                      <Menu.Item leftSection={<IconTrash size={14} />} color="red" onClick={() => deleteEntryMutation.mutate(e.id)}>
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

      <AdminDrawer position="right" size="md" opened={opened} onClose={close} title="Добавить в очередь">
        <Stack>
          <Select label="Пациент" data={patientOptions} value={patientId} onChange={(v) => setPatientId(v ?? "")} searchable placeholder="Выберите пациента" />
          <TextInput label="Дата" type="date" value={preferredDate} onChange={(e) => setPreferredDate(e.target.value || "")} required />
          <TextInput label="Время (необяз.)" type="time" value={preferredTime} onChange={(e) => setPreferredTime(e.target.value || "")} />
          <Select label="Врач (необяз.)" data={doctorOptions} value={doctorId} onChange={setDoctorId} clearable placeholder="Любой" />
          <NumberInput label="Приоритет" value={priority} onChange={(v) => setPriority(Number(v) || 0)} />
          <Button onClick={handleAddEntry} loading={createEntryMutation.isPending} disabled={!patientId || !preferredDate}>Добавить</Button>
        </Stack>
      </AdminDrawer>

      <AdminDrawer position="right" size="md" opened={editEntry !== null} onClose={() => setEditEntry(null)} title="Редактировать запись очереди">
        {editEntry && (
          <EditWaitlistEntryForm
            entry={editEntry}
            patientOptions={patientOptions}
            doctorOptions={doctorOptions}
            statusOptions={[
              { value: "waiting", label: "Ожидание" },
              { value: "notified", label: "Уведомлён" },
              { value: "expired", label: "Истёк" },
              { value: "cancelled", label: "Отменён" },
            ]}
            onSave={(body) => {
              updateEntryMutation.mutate(
                { entryId: editEntry.id, body },
                { onSuccess: () => setEditEntry(null) }
              );
            }}
            onCancel={() => setEditEntry(null)}
            isLoading={updateEntryMutation.isPending}
          />
        )}
      </AdminDrawer>
    </Stack>
  );
}
