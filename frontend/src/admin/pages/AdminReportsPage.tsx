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
import {
  AdminDrawer,
  AdminDataTableSurface,
  ADMIN_TABLE_PROPS,
  ContextBar,
  PageSkeleton,
  QueryErrorAlert,
  AdminDataTableToolbar,
} from "@/shared/ui";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import {
  useMarketingAttributionSummary,
  useMarketingCampaigns,
  useMarketingInsights,
  useMarketingAttributionDrillDown,
  type MarketingChannelSummaryItem,
} from "@/hooks/useMarketingAttribution";
import { isBoxEdition } from "@/config/edition";
import { useTranslation } from "react-i18next";
import { reportsDrillItemTypeLabel } from "@/shared/reportsI18n";

export default function AdminReportsPage() {
  const { t } = useTranslation("reports");
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const showEnterpriseMarketingAnalytics = !isBoxEdition();

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
  const isEmptyDb =
    /клиник/i.test(errMsg) || /no clinics in the database/i.test(errMsg);
  const loading = dashLoading || noShowLoading || revLoading || ownerLoading || attrLoading;

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title={t("title")} />
        <Text size="sm" c="dimmed">
          {t("pickClinic")}
        </Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title={t("titleFull")} />
      {dateFrom > dateTo ? (
        <Text size="sm" c="red">
          {t("dateOrder")}
        </Text>
      ) : null}
      <AdminDataTableToolbar>
        <Grid>
          <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
            <TextInput
              label={t("dateFrom")}
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </Grid.Col>
          <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
            <TextInput
              label={t("dateTo")}
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </Grid.Col>
          {showEnterpriseMarketingAnalytics && (
            <>
              <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
                <Select
                  label={t("trafficSource")}
                  placeholder={t("allSources")}
                  data={trafficSourceOptions}
                  value={selectedTrafficSourceId}
                  onChange={setSelectedTrafficSourceId}
                  clearable
                  searchable
                />
              </Grid.Col>
              <Grid.Col span={{ base: 12, sm: 6, lg: 3 }}>
                <Select
                  label={t("campaign")}
                  placeholder={t("allCampaigns")}
                  data={campaignOptions}
                  value={selectedCampaignId}
                  onChange={setSelectedCampaignId}
                  clearable
                  searchable
                />
              </Grid.Col>
            </>
          )}
        </Grid>
      </AdminDataTableToolbar>

      {anyError && (
        <>
          <QueryErrorAlert error={dashErr ?? noShowErr ?? revErr ?? attrErr ?? errMsg} />
          {isEmptyDb && (
            <Text size="sm" c="dimmed">
              {t("emptyDbHint")}
            </Text>
          )}
        </>
      )}

      {loading && <PageSkeleton variant="cards" cardsCount={4} />}

      {showEnterpriseMarketingAnalytics && attribution?.items && attribution.items.length > 0 && (
        <SimpleGrid cols={{ base: 2, sm: 4 }} spacing="md" mb="md">
          <Card shadow="sm" padding="md" withBorder>
            <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
              {t("adBudget")}
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
              {t("revenue")}
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

      {showEnterpriseMarketingAnalytics && attribution?.items && attribution.items.length > 0 && (
        <Card shadow="sm" padding="md" withBorder mb="md">
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            {t("funnel")}
          </Text>
          <Stack gap="xs">
            <Group gap="md">
              <Text size="xs">
                {t("funnelLeads", { count: attribution.items.reduce((a, i) => a + i.leads_count, 0) })}
              </Text>
              <Progress value={100} size="lg" style={{ flex: 1 }} />
            </Group>
            <Group gap="md">
              <Text size="xs">
                {t("funnelBookings", { count: attribution.items.reduce((a, i) => a + i.bookings_count, 0) })}
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
                {t("funnelPaid", { count: attribution.items.reduce((a, i) => a + i.completed_bookings_count, 0) })}
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

      {showEnterpriseMarketingAnalytics && insightsData && (
        <Card shadow="sm" padding="md" withBorder mb="md">
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            {t("advisorTitle")}
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
              {t("advisorEmpty")}
            </Text>
          )}
        </Card>
      )}

      {ownerDashboard && (
        <Card shadow="sm" padding="md" withBorder>
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            {t("periodSummary")}
          </Text>
          <Grid>
            <Grid.Col span={4}>
              <Text size="xs">{t("revenueLine", { amount: ownerDashboard.total_revenue })}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">{t("noShowRateLine", { rate: (ownerDashboard.no_show_rate * 100).toFixed(1) })}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">{t("prepaymentsLine", { count: ownerDashboard.prepayment_transactions_count })}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">{t("waitlistLine", { count: ownerDashboard.waitlist_entries_count })}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">{t("recallLine", { count: ownerDashboard.recall_campaigns_count })}</Text>
            </Grid.Col>
          </Grid>
        </Card>
      )}

      {dashboard && (
        <Card shadow="sm" padding="md">
          <Text size="sm" c="dimmed">
            {t("dayDashboard", { date: dateTo })}
          </Text>
          <Grid mt="xs">
            <Grid.Col span={4}>
              <Text size="xs">{t("pendingLine", { count: dashboard.bookings_pending })}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">{t("confirmedLine", { count: dashboard.bookings_confirmed })}</Text>
            </Grid.Col>
            <Grid.Col span={4}>
              <Text size="xs">{t("revenueLine", { amount: dashboard.revenue })}</Text>
            </Grid.Col>
          </Grid>
        </Card>
      )}

      {noShow && (
        <Card shadow="sm" padding="md">
          <Text size="sm" c="dimmed">
            {t("noShowPeriod")}
          </Text>
          <Text>
            {t("noShowStats", {
              total: noShow.total,
              count: noShow.no_show_count,
              rate: (noShow.no_show_rate * 100).toFixed(1),
            })}
          </Text>
        </Card>
      )}

      {revenue && (
        <Card shadow="sm" padding="md">
          <Text size="sm" c="dimmed">
            {t("revenuePeriod")}
          </Text>
          <Text>{t("revenueTotal", { amount: revenue.total_revenue })}</Text>
        </Card>
      )}

      {showEnterpriseMarketingAnalytics && attribution && attribution.items.length > 0 && (
        <AdminDataTableSurface>
          <Text size="sm" fw={500} c="dimmed" mb="xs">
            {t("attributionTitle")}
          </Text>
          <Table withTableBorder {...ADMIN_TABLE_PROPS}>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("colChannel")}</Table.Th>
                <Table.Th>{t("colLeads")}</Table.Th>
                <Table.Th>{t("colBookings")}</Table.Th>
                <Table.Th>{t("colCompleted")}</Table.Th>
                <Table.Th>{t("colPatients")}</Table.Th>
                <Table.Th>{t("colRevenue")}</Table.Th>
                <Table.Th>{t("colAvgCheck")}</Table.Th>
                <Table.Th>{t("colRoi")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {attribution.items.map((row, idx) => (
                <Table.Tr
                  key={`${row.traffic_source_code}-${row.campaign_code}-${idx}`}
                  className="data-table-clickable-row"
                  onClick={() => setDrillDownRow(row)}
                >
                  <Table.Td>
                    <Text size="xs">
                      {row.campaign_name || row.traffic_source_name || t("noCampaign")}
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
        </AdminDataTableSurface>
      )}

      {showEnterpriseMarketingAnalytics && (
        <AdminDrawer
          position="right"
          size="md"
          opened={!!drillDownRow}
          onClose={() => setDrillDownRow(null)}
          title={
            drillDownRow
              ? t("drillTitle", {
                  name: drillDownRow.campaign_name || drillDownRow.traffic_source_name || t("unnamedDrill"),
                })
              : ""
          }
        >
          {drillDownRow && (
            <Stack gap="sm">
              <Text size="sm" c="dimmed">
                {t("drillHint")}
              </Text>
              {drillDownData?.items && drillDownData.items.length > 0 ? (
                <Stack gap="xs">
                  {drillDownData.items.slice(0, 50).map((item) => (
                    <Text key={item.id} size="sm">
                      {item.display_label ?? t("unnamedDrill")} — {reportsDrillItemTypeLabel(item.type)}
                    </Text>
                  ))}
                  {drillDownData.total > 50 && (
                    <Text size="xs" c="dimmed">
                      {t("shownOf", { total: drillDownData.total })}
                    </Text>
                  )}
                </Stack>
              ) : (
                <Text size="sm" c="dimmed">
                  {t("drillEmpty")}
                </Text>
              )}
            </Stack>
          )}
        </AdminDrawer>
      )}

      {!dashboard && !noShow && !revenue && !ownerDashboard && !anyError && !loading && (
        <EmptyStateHint title={t("emptyPeriod")} />
      )}
    </Stack>
  );
}
