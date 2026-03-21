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
  Group,
  Progress,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { AdminDrawer, ContextBar, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import {
  useMarketingAttributionSummary,
  useMarketingCampaigns,
  useMarketingInsights,
  useMarketingAttributionDrillDown,
  type MarketingChannelSummaryItem,
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
  const [drillDownRow, setDrillDownRow] = useState<MarketingChannelSummaryItem | null>(null);

  const { data: campaigns } = useMarketingCampaigns();
  const { data: insightsData } = useMarketingInsights(clinicId);
  const { data: drillDownData } = useMarketingAttributionDrillDown({
    dateFrom,
    dateTo,
    drillType: "leads",
    trafficSourceId: drillDownRow?.traffic_source_id ?? null,
    campaignId: drillDownRow?.campaign_id ?? null,
    enabled: !!drillDownRow,
  });

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
        <ContextBar title="Отчёты" />
        <Text size="sm" c="dimmed">
          Выберите клинику.
        </Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Отчёты и дашборд" />

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
          <QueryErrorAlert error={dashErr ?? noShowErr ?? revErr ?? attrErr ?? errMsg} />
          {isEmptyDb && (
            <Text size="sm" c="dimmed">
              {EMPTY_DB_HINT}
            </Text>
          )}
        </>
      )}

      {loading && <PageSkeleton variant="cards" cardsCount={4} />}

      {attribution?.items && attribution.items.length > 0 && (
        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md" mb="md">
          <Card shadow="sm" padding="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              Бюджет (реклама)
            </Text>
            <Text size="lg" fw={700}>
              {attribution.items.some((i) => i.ad_spend != null)
                ? attribution.items
                    .reduce((s, i) => s + (i.ad_spend ? parseFloat(i.ad_spend) : 0), 0)
                    .toFixed(0)
                : "—"}{" "}
              ₽
            </Text>
          </Card>
          <Card shadow="sm" padding="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              Выручка
            </Text>
            <Text size="lg" fw={700}>
              {ownerDashboard?.total_revenue ?? attribution.items.reduce((s, i) => s + parseFloat(i.revenue_sum || "0"), 0).toFixed(0)}{" "}
              ₽
            </Text>
          </Card>
          <Card shadow="sm" padding="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              CAC
            </Text>
            <Text size="lg" fw={700}>
              {attribution.items.find((i) => i.cac != null)?.cac != null
                ? `${attribution.items.find((i) => i.cac != null)!.cac!.toFixed(0)} ₽`
                : "—"}
            </Text>
          </Card>
          <Card shadow="sm" padding="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              ROMI
            </Text>
            <Text size="lg" fw={700}>
              {attribution.items.find((i) => i.roi != null)?.roi != null
                ? `${((attribution.items.find((i) => i.roi != null)!.roi!) * 100).toFixed(1)}%`
                : "—"}
            </Text>
          </Card>
        </SimpleGrid>
      )}

      {attribution?.items && attribution.items.length > 0 && (
        <Card shadow="sm" padding="md" withBorder mb="md">
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            Воронка конверсий
          </Text>
          <Stack gap="xs">
            <Group gap="md">
              <Text size="xs">
                Лиды {attribution.items.reduce((a, i) => a + i.leads_count, 0)}
              </Text>
              <Progress value={100} size="lg" style={{ flex: 1 }} />
            </Group>
            <Group gap="md">
              <Text size="xs">
                Записи {attribution.items.reduce((a, i) => a + i.bookings_count, 0)}
              </Text>
              <Progress
                value={
                  attribution.items.reduce((a, i) => a + i.leads_count, 0) > 0
                    ? (attribution.items.reduce((a, i) => a + i.bookings_count, 0) /
                        attribution.items.reduce((a, i) => a + i.leads_count, 0)) *
                      100
                    : 0
                }
                size="lg"
                color="blue"
                style={{ flex: 1 }}
              />
            </Group>
            <Group gap="md">
              <Text size="xs">
                Оплата {attribution.items.reduce((a, i) => a + i.completed_bookings_count, 0)}
              </Text>
              <Progress
                value={
                  attribution.items.reduce((a, i) => a + i.bookings_count, 0) > 0
                    ? (attribution.items.reduce((a, i) => a + i.completed_bookings_count, 0) /
                        attribution.items.reduce((a, i) => a + i.bookings_count, 0)) *
                      100
                    : 0
                }
                size="lg"
                color="green"
                style={{ flex: 1 }}
              />
            </Group>
          </Stack>
        </Card>
      )}

      {insightsData && (insightsData.insights?.length > 0 || true) && (
        <Card shadow="sm" padding="md" withBorder mb="md">
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            AI Marketing Advisor
          </Text>
          {insightsData.insights?.length > 0 ? (
            <Stack gap="xs">
              {insightsData.insights.map((line, i) => (
                <Text key={i} size="sm">
                  {line}
                </Text>
              ))}
            </Stack>
          ) : (
            <Text size="sm" c="dimmed">
              Пока нет персональных рекомендаций. Анализ каналов и кампаний появится после накопления данных.
            </Text>
          )}
        </Card>
      )}

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
            Маркетинг и атрибуция (клик по строке — drill-down)
          </Text>
          <Table withTableBorder withColumnBorders verticalSpacing="sm">
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
                <Table.Tr
                  key={`${row.traffic_source_code}-${row.campaign_code}-${idx}`}
                  style={{ cursor: "pointer" }}
                  onClick={() => setDrillDownRow(row)}
                >
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

      <AdminDrawer
        position="right"
        size="md"
        opened={!!drillDownRow}
        onClose={() => setDrillDownRow(null)}
        title={drillDownRow ? `По источнику: ${drillDownRow.campaign_name || drillDownRow.traffic_source_name || "—"}` : ""}
      >
        {drillDownRow && (
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              Лиды и записи по выбранному каналу за период.
            </Text>
            {drillDownData?.items && drillDownData.items.length > 0 ? (
              <Stack gap="xs">
                {drillDownData.items.slice(0, 50).map((item) => (
                  <Text key={item.id} size="sm">
                    {item.display_label ?? item.id} — {item.type}
                  </Text>
                ))}
                {drillDownData.total > 50 && (
                  <Text size="xs" c="dimmed">
                    Показано 50 из {drillDownData.total}
                  </Text>
                )}
              </Stack>
            ) : (
              <Text size="sm" c="dimmed">
                Нет данных для выбранного источника.
              </Text>
            )}
          </Stack>
        )}
      </AdminDrawer>

      {!dashboard && !noShow && !revenue && !ownerDashboard && !anyError && !loading && (
        <EmptyStateHint title="Нет данных за выбранный период" />
      )}
    </Stack>
  );
}
