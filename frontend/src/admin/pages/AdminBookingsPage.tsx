import { useAdminBookings, useCancelBookingAdmin, useCompleteBookingAdmin } from "@/hooks/useAdminBookings";
import { useDoctors } from "@/hooks/useDoctors";
import { usePatients } from "@/hooks/usePatients";
import { useServices } from "@/hooks/useServices";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { GlassModal } from "@/shared/ui/GlassModal";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import { Button, Group, Select, Stack, Table, Text, TextInput, Title } from "@mantine/core";
import dayjs from "dayjs";
import { useState } from "react";

const EMPTY_DB_HINT =
  "Если ошибка из-за отсутствия данных в базе — добавьте клинику, врачей или пациентов в соответствующих разделах.";

const STATUS_OPTIONS = [
  { value: "", label: "Любой" },
  { value: "pending", label: "Ожидает" },
  { value: "confirmed", label: "Подтверждено" },
  { value: "completed", label: "Оказано" },
  { value: "cancelled", label: "Отменено" },
  { value: "no_show", label: "Неявка" },
];

export default function AdminBookingsPage() {
  const [doctorId, setDoctorId] = useState<string | null>(null);
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [status, setStatus] = useState<string | null>(null);
  const [patientPhone, setPatientPhone] = useState("");
  const [pendingCancelId, setPendingCancelId] = useState<string | null>(null);

  const { data: doctors } = useDoctors({});
  const { data: patients } = usePatients({});
  const { data: services } = useServices({});
  const doctorOptions =
    doctors?.map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  const filters = {
    doctor_id: doctorId ?? undefined,
    date,
    status: status ?? undefined,
    patient_phone: patientPhone || undefined,
  };

  const { data: bookings, isLoading, isError, error } = useAdminBookings(filters);
  const cancelMutation = useCancelBookingAdmin();
  const completeMutation = useCompleteBookingAdmin();

  const errMessage = isError && error instanceof Error ? error.message : "";
  const isEmptyDb = errMessage.includes("клиник") || errMessage.includes("клиники");

  return (
    <Stack>
      <Title order={3}>Записи</Title>
      <Select
        label="Врач"
        placeholder="Выберите врача"
        data={doctorOptions}
        value={doctorId}
        onChange={setDoctorId}
        searchable
        clearable
      />
      <TextInput
        label="Дата"
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value || dayjs().format("YYYY-MM-DD"))}
      />
      <Select
        label="Статус"
        data={STATUS_OPTIONS}
        value={status ?? ""}
        onChange={(v) => setStatus(v || null)}
      />
      <TextInput
        label="Телефон пациента"
        placeholder="+7..."
        value={patientPhone}
        onChange={(e) => setPatientPhone(e.target.value)}
      />

      {isLoading && <DataSkeleton lines={8} />}
      {isError && (
        <>
          <Text c="red">{errMessage}</Text>
          {isEmptyDb && (
            <Text size="sm" c="dimmed">
              {EMPTY_DB_HINT}
            </Text>
          )}
        </>
      )}
      {!isLoading && !isError && bookings?.length === 0 && (
        <EmptyStateHint title="Нет записей по выбранным фильтрам" />
      )}
      {!isLoading && !isError && bookings && bookings.length > 0 && (
        <Table striped>
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Дата</Table.Th>
              <Table.Th>Время</Table.Th>
              <Table.Th>Врач</Table.Th>
              <Table.Th>Пациент</Table.Th>
              <Table.Th>Услуга</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Действия</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {bookings.map((b) => {
              const doctor = doctors?.find((d) => d.id === b.doctor_id);
              const patient = patients?.find((p) => p.id === b.patient_id);
              const service = services?.find((s) => s.id === b.service_id);
              const patientLabel = patient
                ? [patient.phone, patient.full_name].filter(Boolean).join(" — ") || patient.phone
                : "—";
              return (
              <Table.Tr key={b.id}>
                <Table.Td>{b.appointment_date}</Table.Td>
                <Table.Td>{typeof b.appointment_time === "string" ? b.appointment_time.slice(0, 5) : b.appointment_time}</Table.Td>
                <Table.Td>{doctor ? (doctor.display_role ? `${doctor.display_role} ${doctor.full_name}` : doctor.full_name) : "—"}</Table.Td>
                <Table.Td>{patientLabel}</Table.Td>
                <Table.Td>{service?.name ?? "—"}</Table.Td>
                <Table.Td>{b.status}</Table.Td>
                <Table.Td>
                  {b.status !== "cancelled" && b.status !== "completed" && (() => {
                    const timeStr = String(b.appointment_time).slice(0, 5);
                    const slotDt = new Date(b.appointment_date + "T" + timeStr + ":00");
                    const isPastSlot = slotDt <= new Date();
                    return (
                      <>
                        {!isPastSlot && (
                          <>
                            <Button
                              size="xs"
                              variant="light"
                              onClick={() => setPendingCancelId(b.id)}
                              loading={cancelMutation.isPending}
                            >
                              Отменить
                            </Button>{" "}
                          </>
                        )}
                        <Button
                          size="xs"
                          variant="light"
                          onClick={() => completeMutation.mutate(b.id)}
                          loading={completeMutation.isPending}
                        >
                          Завершить
                        </Button>
                      </>
                    );
                  })()}
                </Table.Td>
              </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      )}

      <GlassModal
        opened={pendingCancelId !== null}
        onClose={() => setPendingCancelId(null)}
        title="Подтверждение отмены"
      >
        <Stack gap="md">
          <Text size="sm">
            Вы действительно хотите отменить запись?
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={() => setPendingCancelId(null)}>
              Нет
            </Button>
            <Button
              color="red"
              loading={cancelMutation.isPending}
              onClick={() => {
                if (!pendingCancelId) return;
                cancelMutation.mutate(pendingCancelId, {
                  onSuccess: () => setPendingCancelId(null),
                });
              }}
            >
              Отменить запись
            </Button>
          </Group>
        </Stack>
      </GlassModal>
    </Stack>
  );
}
