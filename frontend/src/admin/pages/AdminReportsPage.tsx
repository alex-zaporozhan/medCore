import {
  useAdminReportsDashboard,
  useAdminReportsNoShow,
  useAdminReportsRevenue,
  useOwnerDashboard,
} from "@/hooks/useAdminReports";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import {
  Card,
  Grid,
  Loader,
  Select,
  Stack,
  Table,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import {
  useMarketingAttributionSummary,
  useMarketingCampaigns,
} from "@/hooks/useMarketingAttribution";

const EMPTY_DB_HINT =
  "Если ошибка из-за отсутствия данных в базе — добавьте клинику, врачей или пациентов в соответствующих разделах.";

export default function AdminReportsPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;

  const [dateFrom, setDateFrom] = useState(dayjs().subtract(7, "day").format("YYYY-MM-DD"));
  const [dateTo, setDateTo] = useState(dayjs().format("YYYY-MM-DD"));
  const [selectedTrafficSourceId, setSelectedTrafficSourceId] = useState<string | null>(null);
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);

  const { data: campaigns } = useMarketingCampaigns();

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
  const {
    data: attribution,
    isLoading: attrLoading,
    isError: attrError,
    error: attrErr,
  } = useMarketingAttributionSummary(
    clinicId,
    dateFrom,
    dateTo,
    selectedTrafficSourceId,
    selectedCampaignId
  );

  const trafficSourceOptions = useMemo(() => {
    if (!attribution?.items) return [];
    const map = new Map<string, string>();
    attribution.items.forEach((item) => {
      if (item.traffic_source_code || item.traffic_source_name) {
        const key = item.traffic_source_code || item.traffic_source_name || "";
        const label = item.traffic_source_name || item.traffic_source_code || "";
        if (key && !map.has(key)) {
          map.set(key, label || key);
        }
      }
    });
    return Array.from(map.entries()).map(([value, label]) => ({
      value,
      label,
    }));
  }, [attribution]);

  const campaignOptions = useMemo(() => {
    if (!campaigns) return [];
    return campaigns.map((c) => ({
      value: c.id,
      label: c.name,
    }));
  }, [campaigns]);

  const anyError = dashError || noShowError || revError || attrError;
  const errMsg =
    (dashErr instanceof Error ? dashErr.message : null) ||
    (noShowErr instanceof Error ? noShowErr.message : null) ||
    (revErr instanceof Error ? revErr.message : null) ||
    (attrErr instanceof Error ? attrErr.message : null) ||
    "";
  const isEmptyDb = errMsg.includes("клиник") || errMsg.includes("клиники");
  const loading = dashLoading || noShowLoading || revLoading || ownerLoading || attrLoading;

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
      <Grid>
        <Grid.Col span={{ base: 12, sm: 6 }}>
          <Select
            label="Источник трафика"
            placeholder="Все источники"
            data={trafficSourceOptions}
            value={selectedTrafficSourceId}
            onChange={setSelectedTrafficSourceId}
            clearable
            searchable
          />
        </Grid.Col>
        <Grid.Col span={{ base: 12, sm: 6 }}>
          <Select
            label="Кампания"
            placeholder="Все кампании"
            data={campaignOptions}
            value={selectedCampaignId}
            onChange={setSelectedCampaignId}
            clearable
            searchable
          />
        </Grid.Col>
      </Grid>

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

      {attribution && attribution.items.length > 0 && (
        <Card shadow="sm" padding="md" withBorder>
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            Маркетинг и атрибуция
          </Text>
          <Table withTableBorder withColumnBorders>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Канал / кампания</Table.Th>
                <Table.Th>Лиды</Table.Th>
                <Table.Th>Записи</Table.Th>
                <Table.Th>Дошли</Table.Th>
                <Table.Th>Пациенты</Table.Th>
                <Table.Th>Выручка</Table.Th>
                <Table.Th>Средний чек</Table.Th>
                <Table.Th>ROI</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {attribution.items.map((row, idx) => (
                <Table.Tr key={`${row.traffic_source_code}-${row.campaign_code}-${idx}`}>
                  <Table.Td>
                    <Text size="xs">
                      {row.campaign_name || row.traffic_source_name || "Без кампании"}
                    </Text>
                    <Text size="xs" c="dimmed">
                      {row.traffic_source_code || row.campaign_code || "—"}
                    </Text>
                  </Table.Td>
                  <Table.Td>{row.leads_count}</Table.Td>
                  <Table.Td>{row.bookings_count}</Table.Td>
                  <Table.Td>{row.completed_bookings_count}</Table.Td>
                  <Table.Td>{row.unique_patients_count}</Table.Td>
                  <Table.Td>{row.revenue_sum} ₽</Table.Td>
                  <Table.Td>{row.avg_check} ₽</Table.Td>
                  <Table.Td>
                    {row.roi != null ? `${(row.roi * 100).toFixed(1)}%` : "—"}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {!dashboard && !noShow && !revenue && !ownerDashboard && !anyError && !loading && (
        <EmptyStateHint title="Нет данных за выбранный период" />
      )}
    </Stack>
  );
}
