import {
  useAdminReportsDashboard,
  useAdminReportsNoShow,
  useAdminReportsRevenue,
  useOwnerDashboard,
} from "@/hooks/useAdminReports";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { Card, Grid, Loader, Stack, Text, TextInput, Title } from "@mantine/core";
import dayjs from "dayjs";
import { useState } from "react";

const EMPTY_DB_HINT =
  "Если ошибка из-за отсутствия данных в базе — добавьте клинику, врачей или пациентов в соответствующих разделах.";

export default function AdminReportsPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;

  const [dateFrom, setDateFrom] = useState(dayjs().subtract(7, "day").format("YYYY-MM-DD"));
  const [dateTo, setDateTo] = useState(dayjs().format("YYYY-MM-DD"));

  const { data: ownerDashboard, isLoading: ownerLoading } = useOwnerDashboard(
    clinicId,
    dateTo,
    dateFrom,
    dateTo
  );
  const { data: dashboard, isLoading: dashLoading, isError: dashError, error: dashErr } =
    useAdminReportsDashboard(clinicId, dateTo, "day");
  const { data: noShow, isLoading: noShowLoading, isError: noShowError, error: noShowErr } =
    useAdminReportsNoShow(clinicId, dateFrom, dateTo);
  const { data: revenue, isLoading: revLoading, isError: revError, error: revErr } =
    useAdminReportsRevenue(clinicId, dateFrom, dateTo);

  const anyError = dashError || noShowError || revError;
  const errMsg =
    (dashErr instanceof Error ? dashErr.message : null) ||
    (noShowErr instanceof Error ? noShowErr.message : null) ||
    (revErr instanceof Error ? revErr.message : null) ||
    "";
  const isEmptyDb = errMsg.includes("клиник") || errMsg.includes("клиники");
  const loading = dashLoading || noShowLoading || revLoading || ownerLoading;

  if (!clinicId) {
    return (
      <Stack>
        <Title order={3}>Отчёты</Title>
        <Text size="sm" c="dimmed">
          Выберите клинику.
        </Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <Title order={3}>Отчёты и дашборд</Title>

      <TextInput
        label="Дата с"
        type="date"
        value={dateFrom}
        onChange={(e) => setDateFrom(e.target.value)}
      />
      <TextInput
        label="Дата по"
        type="date"
        value={dateTo}
        onChange={(e) => setDateTo(e.target.value)}
      />

      {anyError && (
        <>
          <Text c="red">{errMsg}</Text>
          {isEmptyDb && (
            <Text size="sm" c="dimmed">
              {EMPTY_DB_HINT}
            </Text>
          )}
        </>
      )}

      {loading && <Loader size="sm" />}

      {ownerDashboard && (
        <Card shadow="sm" padding="md" withBorder>
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            Сводка за период
          </Text>
          <Grid>
            <Grid.Col span={4}>
              <Text size="xs">Выручка: {ownerDashboard.total_revenue} ₽</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">No-show: {(ownerDashboard.no_show_rate * 100).toFixed(1)}%</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">Предоплат: {ownerDashboard.prepayment_transactions_count}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">В очереди: {ownerDashboard.waitlist_entries_count}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">Кампаний recall: {ownerDashboard.recall_campaigns_count}</Text>
            </Grid.Col>
          </Grid>
        </Card>
      )}

      {dashboard && (
        <Card shadow="sm" padding="md">
          <Text size="sm" c="dimmed">
            Дашборд за день ({dateTo})
          </Text>
          <Grid mt="xs">
            <Grid.Col span={4}>
              <Text size="xs">Ожидают: {dashboard.bookings_pending}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">Подтверждено: {dashboard.bookings_confirmed}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">Выручка: {dashboard.revenue} ₽</Text>
            </Grid.Col>
          </Grid>
        </Card>
      )}

      {noShow && (
        <Card shadow="sm" padding="md">
          <Text size="sm" c="dimmed">
            No-show за период
          </Text>
          <Text>
            Всего: {noShow.total}, неявок: {noShow.no_show_count}, доля:{(noShow.no_show_rate * 100).toFixed(1)}%
          </Text>
        </Card>
      )}

      {revenue && (
        <Card shadow="sm" padding="md">
          <Text size="sm" c="dimmed">
            Выручка за период
          </Text>
          <Text>Итого: {revenue.total_revenue} ₽</Text>
        </Card>
      )}

      {!dashboard && !noShow && !revenue && !ownerDashboard && !anyError && !loading && (
        <EmptyStateHint title="Нет данных за выбранный период" />
      )}
    </Stack>
  );
}
