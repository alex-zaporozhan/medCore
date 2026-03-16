import { useDoctors } from "@/hooks/useDoctors";
import {
  useWorkingHours,
  useCreateOrUpdateWorkingHours,
  useDeleteWorkingHours,
  useAbsence,
  useCreateAbsence,
  useDeleteAbsence,
  type WorkingHoursRead,
  type AbsenceRead,
} from "@/hooks/useDoctorScheduleConfig";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import {
  Button,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Group,
  ActionIcon,
  Paper,
} from "@mantine/core";
import { ContextBar } from "@/shared/ui/ContextBar";
import { useDisclosure } from "@mantine/hooks";
import { useState } from "react";
import { GlassModal } from "@/shared/ui/GlassModal";

const WEEKDAY_LABELS: Record<number, string> = {
  0: "Пн",
  1: "Вт",
  2: "Ср",
  3: "Чт",
  4: "Пт",
  5: "Сб",
  6: "Вс",
};

function timeStr(t: string): string {
  return String(t).slice(0, 5);
}

export default function AdminDoctorSchedulePage() {
  const { currentClinicId } = useAdminClinic();
  const { data: doctors, isLoading: doctorsLoading } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
  });
  const [doctorId, setDoctorId] = useState<string | null>(null);

  const { data: workingHours, isLoading: whLoading } = useWorkingHours(doctorId);
  const { data: absences, isLoading: absLoading } = useAbsence(doctorId);
  const createWh = useCreateOrUpdateWorkingHours(doctorId ?? "");
  const deleteWh = useDeleteWorkingHours(doctorId ?? "");
  const createAbsence = useCreateAbsence(doctorId ?? "");
  const deleteAbsence = useDeleteAbsence(doctorId ?? "");

  const [whModalOpen, { open: openWhModal, close: closeWhModal }] =
    useDisclosure(false);
  const [absenceModalOpen, { open: openAbsenceModal, close: closeAbsenceModal }] =
    useDisclosure(false);
  const [whWeekday, setWhWeekday] = useState<number>(0);
  const [whStart, setWhStart] = useState("09:00");
  const [whEnd, setWhEnd] = useState("18:00");
  const [absFrom, setAbsFrom] = useState("");
  const [absTo, setAbsTo] = useState("");
  const [absReason, setAbsReason] = useState("");

  const doctorOptions =
    doctors?.map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  const handleSaveWh = () => {
    if (!doctorId) return;
    const start = whStart.length === 5 ? `${whStart}:00` : whStart;
    const end = whEnd.length === 5 ? `${whEnd}:00` : whEnd;
    createWh.mutate(
      { weekday: whWeekday, start_time: start, end_time: end },
      {
        onSuccess: () => {
          closeWhModal();
          setWhStart("09:00");
          setWhEnd("18:00");
          setWhWeekday(0);
        },
      }
    );
  };

  const handleSaveAbsence = () => {
    if (!doctorId || !absFrom || !absTo) return;
    createAbsence.mutate(
      {
        date_from: absFrom,
        date_to: absTo,
        reason: absReason || undefined,
      },
      {
        onSuccess: () => {
          closeAbsenceModal();
          setAbsFrom("");
          setAbsTo("");
          setAbsReason("");
        },
      }
    );
  };

  return (
    <Stack>
      <ContextBar title="График врачей" />
      <Text size="sm" c="dimmed">
        Настройте рабочие дни и часы, а также отпуска для каждого врача.
      </Text>

      <Select
        label="Врач"
        placeholder="Выберите врача"
        data={doctorOptions}
        value={doctorId}
        onChange={(v) => setDoctorId(v)}
        clearable
      />

      {doctorsLoading && <DataSkeleton lines={2} />}
      {!doctorId && (
        <EmptyStateHint
          title="Выберите врача"
          subtitle="Выберите врача из списка, чтобы настроить рабочие часы и отпуска."
        />
      )}

      {doctorId && (
        <>
          <Paper p="md" withBorder radius="md">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Рабочие часы (по дням недели)</Text>
              <Button
                size="xs"
                onClick={() => {
                  setWhWeekday(0);
                  setWhStart("09:00");
                  setWhEnd("18:00");
                  openWhModal();
                }}
              >
                Добавить день
              </Button>
            </Group>
            {whLoading && <DataSkeleton lines={3} />}
            {workingHours && workingHours.length === 0 && (
              <Text size="sm" c="dimmed">
                Нет настроенных рабочих часов. Добавьте дни — слоты появятся в расписании.
              </Text>
            )}
            {workingHours && workingHours.length > 0 && (
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>День</Table.Th>
                    <Table.Th>Начало</Table.Th>
                    <Table.Th>Конец</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {workingHours.map((row: WorkingHoursRead) => (
                    <Table.Tr key={row.id}>
                      <Table.Td>{WEEKDAY_LABELS[row.weekday] ?? row.weekday}</Table.Td>
                      <Table.Td>{timeStr(row.start_time)}</Table.Td>
                      <Table.Td>{timeStr(row.end_time)}</Table.Td>
                      <Table.Td>
                        <ActionIcon
                          color="red"
                          variant="subtle"
                          onClick={() =>
                            deleteWh.mutate(row.id)
                          }
                          title="Удалить"
                        >
                          ✕
                        </ActionIcon>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Paper>

          <Paper p="md" withBorder radius="md">
            <Group justify="space-between" mb="sm">
              <Text fw={600}>Отпуска и нерабочие периоды</Text>
              <Button
                size="xs"
                onClick={() => {
                  openAbsenceModal();
                }}
              >
                Добавить период
              </Button>
            </Group>
            {absLoading && <DataSkeleton lines={2} />}
            {absences && absences.length === 0 && (
              <Text size="sm" c="dimmed">
                Нет запланированных отпусков.
              </Text>
            )}
            {absences && absences.length > 0 && (
              <Table>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>С</Table.Th>
                    <Table.Th>По</Table.Th>
                    <Table.Th>Причина</Table.Th>
                    <Table.Th />
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {absences.map((row: AbsenceRead) => (
                    <Table.Tr key={row.id}>
                      <Table.Td>{row.date_from}</Table.Td>
                      <Table.Td>{row.date_to}</Table.Td>
                      <Table.Td>{row.reason ?? "—"}</Table.Td>
                      <Table.Td>
                        <ActionIcon
                          color="red"
                          variant="subtle"
                          onClick={() => deleteAbsence.mutate(row.id)}
                          title="Удалить"
                        >
                          ✕
                        </ActionIcon>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Paper>
        </>
      )}

      <GlassModal
        opened={whModalOpen}
        onClose={closeWhModal}
        title="Рабочий день"
      >
        <Stack>
          <Select
            label="День недели"
            data={[0, 1, 2, 3, 4, 5, 6].map((w) => ({
              value: String(w),
              label: WEEKDAY_LABELS[w] ?? `День ${w}`,
            }))}
            value={String(whWeekday)}
            onChange={(v) => setWhWeekday(Number(v ?? 0))}
          />
          <TextInput
            label="Начало (ЧЧ:ММ)"
            placeholder="09:00"
            value={whStart}
            onChange={(e) => setWhStart(e.target.value)}
          />
          <TextInput
            label="Конец (ЧЧ:ММ)"
            placeholder="18:00"
            value={whEnd}
            onChange={(e) => setWhEnd(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={closeWhModal}>
              Отмена
            </Button>
            <Button onClick={handleSaveWh} loading={createWh.isPending}>
              Сохранить
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        opened={absenceModalOpen}
        onClose={closeAbsenceModal}
        title="Отпуск / нерабочий период"
      >
        <Stack>
          <TextInput
            label="Дата начала"
            type="date"
            value={absFrom}
            onChange={(e) => setAbsFrom(e.target.value)}
          />
          <TextInput
            label="Дата окончания"
            type="date"
            value={absTo}
            onChange={(e) => setAbsTo(e.target.value)}
          />
          <TextInput
            label="Причина (необязательно)"
            placeholder="Отпуск, больничный..."
            value={absReason}
            onChange={(e) => setAbsReason(e.target.value)}
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={closeAbsenceModal}>
              Отмена
            </Button>
            <Button
              onClick={handleSaveAbsence}
              loading={createAbsence.isPending}
              disabled={!absFrom || !absTo}
            >
              Добавить
            </Button>
          </Group>
        </Stack>
      </GlassModal>
    </Stack>
  );
}
