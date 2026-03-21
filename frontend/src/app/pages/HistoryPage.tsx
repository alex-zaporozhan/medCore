import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { useCancelPatientBooking, usePatientBookings, useClinics } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { QueryErrorAlert } from "@/shared/ui";
import { Button, Loader, Stack, Table, Title } from "@mantine/core";

export default function HistoryPage() {
  const { accessToken, patientId } = usePatientAuth();
  const { data: clinics } = useClinics();
  const { data: bookings, isLoading, isError, error } = usePatientBookings(patientId, accessToken);
  const cancelMutation = useCancelPatientBooking(accessToken);

  if (isLoading) return <Loader />;
  if (isError) {
    return (
      <Stack>
        <Title order={3}>История посещений</Title>
        <QueryErrorAlert error={error} title="Не удалось загрузить записи" />
      </Stack>
    );
  }
  if (!bookings?.length) return <EmptyStateHint title="Нет записей" subtitle="Запишитесь на приём через «Быстрая запись»." />;

  return (
    <Stack>
      <Title order={3}>История посещений</Title>
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>Клиника</Table.Th>
            <Table.Th>Дата</Table.Th>
            <Table.Th>Время</Table.Th>
            <Table.Th>Статус</Table.Th>
            <Table.Th>Действия</Table.Th>
          </Table.Tr>
        </Table.Thead>
        <Table.Tbody>
          {bookings.map((b) => (
            <Table.Tr key={b.id}>
              <Table.Td>{clinics?.find((c) => c.id === b.clinic_id)?.name ?? b.clinic_id.slice(0, 8)}</Table.Td>
              <Table.Td>{b.appointment_date}</Table.Td>
              <Table.Td>{typeof b.appointment_time === "string" ? b.appointment_time.slice(0, 5) : b.appointment_time}</Table.Td>
              <Table.Td>{b.status}</Table.Td>
              <Table.Td>
                {b.status !== "cancelled" && b.status !== "completed" && patientId && (
                  <Button
                    size="xs"
                    variant="light"
                    color="red"
                    onClick={() => cancelMutation.mutate({ bookingId: b.id, patientId })}
                    loading={cancelMutation.isPending}
                  >
                    Отменить
                  </Button>
                )}
              </Table.Td>
            </Table.Tr>
          ))}
        </Table.Tbody>
      </Table>
    </Stack>
  );
}
