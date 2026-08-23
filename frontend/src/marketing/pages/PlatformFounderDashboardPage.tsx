import { API_BASE } from "@/api/client";
import { PlatformFounderTotpSetupModal } from "@/marketing/components/PlatformFounderTotpSetupModal";
import { usePlatformFounderSession } from "@/marketing/contexts/PlatformFounderSessionContext";
import {
  FounderQueryError,
  formatPlatformFounderApiError,
  founderFailMessage,
  parseJsonArray,
} from "@/marketing/platformFounderApi";
import { ROUTE_PATHS } from "@/routePaths";
import { AreaChart } from "@mantine/charts";
import {
  Anchor,
  Badge,
  Box,
  Button,
  Container,
  Grid,
  Group,
  Paper,
  SimpleGrid,
  Skeleton,
  Stack,
  Table,
  Text,
  Title,
} from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { IconExternalLink } from "@tabler/icons-react";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useMemo, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

/** Ориентиры, если эндпоинт сводки недоступен (ошибка сети / 503). */
const MOCK_ACTIVE_ORGANIZATIONS = 12;
const MOCK_MRR_USD = 1_200;

type DashboardSummary = {
  active_organizations: number;
  mrr_rub_monthly: string;
  mrr_partial: boolean;
  currency?: string;
};

type EnterpriseLeadRow = {
  id: string;
  status: string;
};

type QueueRow = {
  intent_id: string;
  status: string;
  email: string | null;
  organization_id: string | null;
};

function KpiCard({
  title,
  value,
  footnote,
  illustrativeTrend = false,
  trendLabel,
}: {
  title: string;
  value: ReactNode;
  footnote?: ReactNode;
  illustrativeTrend?: boolean;
  trendLabel?: string;
}) {
  return (
    <Paper p="md" radius="md" shadow="xs" withBorder bg="white" style={{ borderColor: "var(--mantine-color-gray-3)" }}>
      <Text size="xs" c="dimmed" tt="uppercase" fw={600} style={{ letterSpacing: "0.04em" }}>
        {title}
      </Text>
      <Group align="flex-start" justify="space-between" wrap="nowrap" gap="sm" mt={10}>
        <Box style={{ minWidth: 0, flex: 1 }}>{value}</Box>
        {illustrativeTrend ? (
          <Badge color="green" variant="light" size="sm" style={{ flexShrink: 0 }}>
            {trendLabel}
          </Badge>
        ) : null}
      </Group>
      {footnote ? (
        <Text size="xs" c="dimmed" mt={8}>
          {footnote}
        </Text>
      ) : null}
    </Paper>
  );
}

function formatUsd(n: number) {
  return `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
}

function kpiNumber(n: number, locale: string) {
  return (
    <Text fz={28} fw={700} lh={1.2} style={{ color: "#0f172a" }}>
      {n.toLocaleString(locale.startsWith("ru") ? "ru-RU" : "en-US")}
    </Text>
  );
}

function parseSummaryAmount(s: string): number {
  const n = Number.parseFloat(s.replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

export default function PlatformFounderDashboardPage() {
  const { t, i18n } = useTranslation("founder");
  const { token } = usePlatformFounderSession();
  const tokenReady = Boolean(token?.trim());
  const [totpModalOpen, totpModalHandlers] = useDisclosure(false);

  const summaryQ = useQuery({
    queryKey: ["platform-founder", "dashboard-summary", token],
    enabled: tokenReady,
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/dashboard-summary`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 401 || r.status === 403) {
        throw new FounderQueryError("session");
      }
      if (r.status === 503) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("unavailable", { apiDetail: apiDetail || undefined });
      }
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
      const raw: unknown = await r.json();
      return raw as DashboardSummary;
    },
  });

  const queueQ = useQuery({
    queryKey: ["platform-founder", "provision-queue", token],
    enabled: tokenReady,
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/provision-queue`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 401 || r.status === 403) {
        throw new FounderQueryError("session");
      }
      if (r.status === 503) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("unavailable", { apiDetail: apiDetail || undefined });
      }
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
      const raw: unknown = await r.json();
      return parseJsonArray<QueueRow>(raw);
    },
  });

  const leadsQ = useQuery({
    queryKey: ["platform-founder", "enterprise-leads", token],
    enabled: tokenReady,
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/enterprise-leads`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 401 || r.status === 403) {
        throw new FounderQueryError("session");
      }
      if (r.status === 503) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("unavailable", { apiDetail: apiDetail || undefined });
      }
      if (!r.ok) {
        const apiDetail = await formatPlatformFounderApiError(r, "");
        throw new FounderQueryError("http", { httpStatus: r.status, apiDetail: apiDetail || undefined });
      }
      const raw: unknown = await r.json();
      return parseJsonArray<EnterpriseLeadRow>(raw);
    },
  });

  const newEnterpriseCount = useMemo(() => {
    const rows = leadsQ.data ?? [];
    return rows.filter((l) => l.status === "NEW").length;
  }, [leadsQ.data]);

  const chartData = useMemo(() => {
    const end = dayjs().startOf("day");
    return Array.from({ length: 30 }, (_, i) => {
      const d = end.subtract(29 - i, "day");
      const wave = Math.sin(i / 4.2) * 6 + Math.cos(i / 7) * 3;
      return {
        day: d.format("DD.MM"),
        registrations: Math.max(2, Math.round(8 + wave + i * 0.25)),
      };
    });
  }, []);

  const queueRows = queueQ.data ?? [];
  const previewRows = queueRows.slice(0, 8);

  const grafanaUrl = import.meta.env.VITE_GRAFANA_URL ?? "http://127.0.0.1:3001";

  return (
    <Box style={{ background: "var(--mantine-color-gray-0)" }} pb="xl" pt="md">
      <Container size="xl" px="md">
        <Stack gap="xl">
          <Stack gap={6}>
            <Title order={2} style={{ color: "#0f172a" }}>
              {t("dashboard.title")}
            </Title>
            <Text size="sm" c="dimmed" maw={720}>
              {t("dashboard.lead")}
            </Text>
          </Stack>

          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
            <KpiCard
              title={t("dashboard.kpiOrgs")}
              illustrativeTrend={Boolean(summaryQ.error && !summaryQ.isLoading)}
              trendLabel={t("dashboard.trend")}
              value={
                summaryQ.isLoading ? (
                  <Skeleton height={36} width={72} radius="sm" />
                ) : summaryQ.error ? (
                  kpiNumber(MOCK_ACTIVE_ORGANIZATIONS, i18n.language)
                ) : (
                  kpiNumber(summaryQ.data?.active_organizations ?? 0, i18n.language)
                )
              }
              footnote={
                summaryQ.error ? (
                  <Text span c="red" size="xs">
                    {t("errors.mockShown", { message: founderFailMessage(summaryQ.error, t) })}
                  </Text>
                ) : !summaryQ.isLoading ? (
                  t("dashboard.kpiOrgsHint")
                ) : null
              }
            />
            <KpiCard
              title={t("dashboard.kpiLeads")}
              value={
                leadsQ.isLoading ? (
                  <Skeleton height={36} width={56} radius="sm" />
                ) : leadsQ.error ? (
                  <Text fz={28} fw={700} c="dimmed">
                    —
                  </Text>
                ) : (
                  kpiNumber(newEnterpriseCount, i18n.language)
                )
              }
              footnote={
                leadsQ.error ? (
                  <Text span c="red" size="xs">
                    {founderFailMessage(leadsQ.error, t)}
                  </Text>
                ) : !leadsQ.isLoading ? (
                  t("dashboard.kpiLeadsHint")
                ) : null
              }
            />
            <KpiCard
              title={t("dashboard.kpiQueue")}
              value={
                queueQ.isLoading ? (
                  <Skeleton height={36} width={56} radius="sm" />
                ) : queueQ.error ? (
                  <Text fz={28} fw={700} c="dimmed">
                    —
                  </Text>
                ) : (
                  kpiNumber(queueRows.length, i18n.language)
                )
              }
              footnote={
                queueQ.error ? (
                  <Text span c="red" size="xs">
                    {founderFailMessage(queueQ.error, t)}
                  </Text>
                ) : (
                  t("dashboard.kpiQueueHint")
                )
              }
            />
            <KpiCard
              title={t("dashboard.kpiMrr")}
              illustrativeTrend={Boolean(summaryQ.error && !summaryQ.isLoading)}
              trendLabel={t("dashboard.trend")}
              value={
                summaryQ.isLoading ? (
                  <Skeleton height={36} width={120} radius="sm" />
                ) : summaryQ.error ? (
                  <Text fz={28} fw={700} lh={1.2} style={{ color: "#0f172a" }}>
                    {formatUsd(MOCK_MRR_USD)}
                  </Text>
                ) : (
                  <Text fz={28} fw={700} lh={1.2} style={{ color: "#0f172a" }}>
                    {formatUsd(parseSummaryAmount(summaryQ.data?.mrr_rub_monthly ?? "0"))}
                  </Text>
                )
              }
              footnote={
                summaryQ.error ? (
                  <Text span c="red" size="xs">
                    {t("errors.mockShown", { message: founderFailMessage(summaryQ.error, t) })}
                  </Text>
                ) : !summaryQ.isLoading && summaryQ.data?.mrr_partial ? (
                  t("dashboard.kpiMrrPartial")
                ) : !summaryQ.isLoading ? (
                  t("dashboard.kpiMrrHint")
                ) : null
              }
            />
          </SimpleGrid>

          <Grid gutter="lg">
            <Grid.Col span={{ base: 12, md: 7 }}>
              <Paper
                p="lg"
                radius="md"
                shadow="xs"
                withBorder
                bg="white"
                style={{ borderColor: "var(--mantine-color-gray-3)" }}
              >
                <Text fw={600} size="sm" mb="md" style={{ color: "#0f172a" }}>
                  {t("dashboard.chartTitle")}
                </Text>
                <Box
                  role="figure"
                  aria-label={t("dashboard.chartAria")}
                >
                  <AreaChart
                    h={280}
                    data={chartData}
                    dataKey="day"
                    series={[{ name: "registrations", color: "slate.7", label: t("dashboard.chartSeries") }]}
                    curveType="natural"
                    gridColor="gray.3"
                    textColor="dimmed"
                    strokeWidth={2}
                    fillOpacity={0.15}
                    withGradient
                    withDots={false}
                    tooltipAnimationDuration={200}
                    xAxisProps={{ tick: { fontSize: 11 }, interval: 3 }}
                    yAxisProps={{ tick: { fontSize: 11 }, width: 32 }}
                  />
                </Box>
                <Text size="xs" c="dimmed" mt="sm">
                  {t("dashboard.chartHint")}
                </Text>
              </Paper>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 5 }}>
              <Paper
                p="lg"
                radius="md"
                shadow="xs"
                withBorder
                bg="white"
                style={{ borderColor: "var(--mantine-color-gray-3)", height: "100%" }}
              >
                <Group justify="space-between" mb="md" wrap="nowrap">
                  <Text fw={600} size="sm" style={{ color: "#0f172a" }}>
                    {t("dashboard.queuePreview")}
                  </Text>
                  <Anchor component={Link} to={ROUTE_PATHS.platform.provisionQueue} size="xs">
                    {t("dashboard.queueAll")}
                  </Anchor>
                </Group>
                {queueQ.isLoading ? (
                  <Text size="sm" c="dimmed">
                    {t("dashboard.loading")}
                  </Text>
                ) : queueQ.error ? (
                  <Text size="sm" c="red">
                    {founderFailMessage(queueQ.error, t)}
                  </Text>
                ) : previewRows.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    {t("dashboard.queueEmpty")}
                  </Text>
                ) : (
                  <Table.ScrollContainer minWidth={280}>
                    <Table
                      verticalSpacing="xs"
                      horizontalSpacing="sm"
                      highlightOnHover
                      aria-label={t("dashboard.queueTableAria")}
                    >
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>{t("dashboard.colEmail")}</Table.Th>
                          <Table.Th>{t("dashboard.colStatus")}</Table.Th>
                          <Table.Th>{t("dashboard.colOrg")}</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {previewRows.map((row) => (
                          <Table.Tr key={row.intent_id}>
                            <Table.Td>
                              <Text size="xs" lineClamp={1}>
                                {row.email ?? "—"}
                              </Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="xs">{row.status}</Text>
                            </Table.Td>
                            <Table.Td>
                              <Text size="xs" c={row.organization_id ? undefined : "dimmed"}>
                                {row.organization_id ? t("dashboard.yes") : t("dashboard.no")}
                              </Text>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </Table.ScrollContainer>
                )}
              </Paper>
            </Grid.Col>
          </Grid>

          <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
            <Paper p="lg" radius="md" shadow="xs" withBorder bg="white" style={{ borderColor: "var(--mantine-color-gray-3)" }}>
              <Title order={5} mb="xs" style={{ color: "#0f172a" }}>
                {t("dashboard.sessionTitle")}
              </Title>
              <Text size="sm" c="dimmed" mb="md">
                {t("dashboard.sessionBody")}
              </Text>
              <Button variant="light" color="slate" onClick={totpModalHandlers.open}>
                {t("dashboard.bindTotp")}
              </Button>
            </Paper>

            <Paper p="lg" radius="md" shadow="xs" withBorder bg="white" style={{ borderColor: "var(--mantine-color-gray-3)" }}>
              <Title order={5} mb="xs" style={{ color: "#0f172a" }}>
                {t("dashboard.infraTitle")}
              </Title>
              <Text size="sm" c="dimmed" mb="md">
                {t("dashboard.infraBody")}
              </Text>
              <Button
                component="a"
                href={grafanaUrl}
                target="_blank"
                rel="noopener noreferrer"
                variant="default"
                leftSection={<IconExternalLink size={16} aria-hidden />}
              >
                {t("dashboard.openGrafana")}
              </Button>
            </Paper>
          </SimpleGrid>

          <PlatformFounderTotpSetupModal opened={totpModalOpen} onClose={totpModalHandlers.close} />
        </Stack>
      </Container>
    </Box>
  );
}
