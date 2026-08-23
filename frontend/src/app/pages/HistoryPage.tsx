import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { useCancelPatientBooking, usePatientBookings, useClinics } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { QueryErrorAlert } from "@/shared/ui";
import { Button, Loader, Stack, Table, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

export default function HistoryPage() {
  const { t } = useTranslation("patient");
  const { accessToken, patientId } = usePatientAuth();
  const { data: clinics } = useClinics();
  const { data: bookings, isLoading, isError, error } = usePatientBookings(patientId, accessToken);
  const cancelMutation = useCancelPatientBooking(accessToken);

  if (isLoading) return <Loader />;
  if (isError) {
    return (
      <Stack>
        <Title order={3}>{t("history.title")}</Title>
        <QueryErrorAlert error={error} title={t("history.loadFailed")} />
      </Stack>
    );
  }
  if (!bookings?.length) return <EmptyStateHint title={t("history.emptyTitle")} subtitle={t("history.emptyHint")} />;

  return (
    <Stack>
      <Title order={3}>{t("history.title")}</Title>
      <Table striped>
        <Table.Thead>
          <Table.Tr>
            <Table.Th>{t("history.clinic")}</Table.Th>
            <Table.Th>{t("history.date")}</Table.Th>
            <Table.Th>{t("history.time")}</Table.Th>
            <Table.Th>{t("history.status")}</Table.Th>
            <Table.Th>{t("history.actions")}</Table.Th>
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
                    {t("history.cancel")}
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
