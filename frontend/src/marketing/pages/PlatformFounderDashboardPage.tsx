import { API_BASE } from "@/api/client";
import { PlatformFounderTotpSetupModal } from "@/marketing/components/PlatformFounderTotpSetupModal";
import { usePlatformFounderSession } from "@/marketing/contexts/PlatformFounderSessionContext";
import {
  formatPlatformFounderApiError,
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
import { Link } from "react-router-dom";

/** Ориентиры, если эндпоинт сводки недоступен (ошибка сети / 503). */
const MOCK_ACTIVE_ORGANIZATIONS = 12;
const MOCK_MRR_RUB = 350_000;

const ILLUSTRATIVE_TREND = "+15% к прошлому месяцу";

type DashboardSummary = {
  active_organizations: number;
  mrr_rub_monthly: string;
  mrr_partial: boolean;
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
  /** Только для ориентировочных KPI (мок); на метриках из API не показываем — иначе вводит в заблуждение. */
  illustrativeTrend = false,
}: {
  title: string;
  value: ReactNode;
  footnote?: ReactNode;
  illustrativeTrend?: boolean;
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
            {ILLUSTRATIVE_TREND}
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

function formatRub(n: number) {
  return `${n.toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽`;
}

function parseSummaryRub(s: string): number {
  const n = Number.parseFloat(s.replace(",", "."));
  return Number.isFinite(n) ? n : 0;
}

function kpiNumber(n: number) {
  return (
    <Text fz={28} fw={700} lh={1.2} style={{ color: "#0f172a" }}>
      {n.toLocaleString("ru-RU")}
    </Text>
  );
}

export default function PlatformFounderDashboardPage() {
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
        throw new Error("Сессия недействительна. Выйдите и войдите снова.");
      }
      if (r.status === 503) {
        throw new Error(
          await formatPlatformFounderApiError(
            r,
            "Сервис основателя недоступен (проверьте конфигурацию секрета в среде).",
          ),
        );
      }
      if (!r.ok) {
        throw new Error(await formatPlatformFounderApiError(r, `Ошибка ${r.status}`));
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
        throw new Error("Сессия недействительна. Выйдите и войдите снова.");
      }
      if (r.status === 503) {
        throw new Error(
          await formatPlatformFounderApiError(
            r,
            "Сервис основателя недоступен (проверьте конфигурацию секрета в среде).",
          ),
        );
      }
      if (!r.ok) {
        throw new Error(await formatPlatformFounderApiError(r, `Ошибка ${r.status}`));
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
        throw new Error("Сессия недействительна. Выйдите и войдите снова.");
      }
      if (r.status === 503) {
        throw new Error(
          await formatPlatformFounderApiError(
            r,
            "Сервис основателя недоступен (проверьте конфигурацию секрета в среде).",
          ),
        );
      }
      if (!r.ok) {
        throw new Error(await formatPlatformFounderApiError(r, `Ошибка ${r.status}`));
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
              Обзор
            </Title>
            <Text size="sm" c="dimmed" maw={720}>
              Сводка по организациям, заявкам и очереди внедрения. Показатели ниже отражают текущее состояние
              платформы в удобном для решений виде.
            </Text>
          </Stack>

          <SimpleGrid cols={{ base: 1, sm: 2, lg: 4 }} spacing="md">
            <KpiCard
              title="Активные организации"
              illustrativeTrend={Boolean(summaryQ.error && !summaryQ.isLoading)}
              value={
                summaryQ.isLoading ? (
                  <Skeleton height={36} width={72} radius="sm" />
                ) : summaryQ.error ? (
                  kpiNumber(MOCK_ACTIVE_ORGANIZATIONS)
                ) : (
                  kpiNumber(summaryQ.data?.active_organizations ?? 0)
                )
              }
              footnote={
                summaryQ.error ? (
                  <Text span c="red" size="xs">
                    {(summaryQ.error as Error).message}. Показан ориентир для макета.
                  </Text>
                ) : !summaryQ.isLoading ? (
                  "Организации с активной подпиской SaaS (снимок на сервере)"
                ) : null
              }
            />
            <KpiCard
              title="Заявки Enterprise"
              value={
                leadsQ.isLoading ? (
                  <Skeleton height={36} width={56} radius="sm" />
                ) : leadsQ.error ? (
                  <Text fz={28} fw={700} c="dimmed">
                    —
                  </Text>
                ) : (
                  kpiNumber(newEnterpriseCount)
                )
              }
              footnote={
                leadsQ.error ? (
                  <Text span c="red" size="xs">
                    {(leadsQ.error as Error).message}
                  </Text>
                ) : !leadsQ.isLoading ? (
                  "В статусе «Новая»"
                ) : null
              }
            />
            <KpiCard
              title="Очередь провижининга"
              value={
                queueQ.isLoading ? (
                  <Skeleton height={36} width={56} radius="sm" />
                ) : queueQ.error ? (
                  <Text fz={28} fw={700} c="dimmed">
                    —
                  </Text>
                ) : (
                  kpiNumber(queueRows.length)
                )
              }
              footnote={
                queueQ.error ? (
                  <Text span c="red" size="xs">
                    {(queueQ.error as Error).message}
                  </Text>
                ) : (
                  "Записей в очереди обработки"
                )
              }
            />
            <KpiCard
              title="MRR (Регулярная выручка)"
              illustrativeTrend={Boolean(summaryQ.error && !summaryQ.isLoading)}
              value={
                summaryQ.isLoading ? (
                  <Skeleton height={36} width={120} radius="sm" />
                ) : summaryQ.error ? (
                  <Text fz={28} fw={700} lh={1.2} style={{ color: "#0f172a" }}>
                    {formatRub(MOCK_MRR_RUB)}
                  </Text>
                ) : (
                  <Text fz={28} fw={700} lh={1.2} style={{ color: "#0f172a" }}>
                    {formatRub(parseSummaryRub(summaryQ.data?.mrr_rub_monthly ?? "0"))}
                  </Text>
                )
              }
              footnote={
                summaryQ.error ? (
                  <Text span c="red" size="xs">
                    {(summaryQ.error as Error).message}. Показан ориентир для макета.
                  </Text>
                ) : !summaryQ.isLoading && summaryQ.data?.mrr_partial ? (
                  "Часть активных организаций без полного тарифного снимка — сумма оценочная (каталог)."
                ) : !summaryQ.isLoading ? (
                  "Оценка по тарифным снимкам и каталогу (ежемесячный эквивалент)."
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
                  Регистрации за 30 дней
                </Text>
                <Box
                  role="figure"
                  aria-label="Демонстрационный график регистраций за 30 дней; данные не из продакшн-учёта"
                >
                  <AreaChart
                    h={280}
                    data={chartData}
                    dataKey="day"
                    series={[{ name: "registrations", color: "slate.7", label: "Регистрации" }]}
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
                  Ориентировочная кривая для интерфейса; после подключения учёта регистраций график заменится на
                  фактические значения.
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
                    Очередь signup / провижининг
                  </Text>
                  <Anchor component={Link} to={ROUTE_PATHS.platform.provisionQueue} size="xs">
                    Вся очередь
                  </Anchor>
                </Group>
                {queueQ.isLoading ? (
                  <Text size="sm" c="dimmed">
                    Загрузка…
                  </Text>
                ) : queueQ.error ? (
                  <Text size="sm" c="red">
                    {(queueQ.error as Error).message}
                  </Text>
                ) : previewRows.length === 0 ? (
                  <Text size="sm" c="dimmed">
                    Нет записей в очереди.
                  </Text>
                ) : (
                  <Table.ScrollContainer minWidth={280}>
                    <Table
                      verticalSpacing="xs"
                      horizontalSpacing="sm"
                      highlightOnHover
                      aria-label="Сокращённый список очереди провижининга"
                    >
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Почта</Table.Th>
                          <Table.Th>Статус</Table.Th>
                          <Table.Th>Организация</Table.Th>
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
                                {row.organization_id ? "Да" : "Нет"}
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
                Безопасность сессии
              </Title>
              <Text size="sm" c="dimmed" mb="md">
                Двухфакторная аутентификация снижает риск несанкционированного входа в кабинет основателя.
              </Text>
              <Button variant="light" color="slate" onClick={totpModalHandlers.open}>
                Привязать TOTP / Google Authenticator
              </Button>
            </Paper>

            <Paper p="lg" radius="md" shadow="xs" withBorder bg="white" style={{ borderColor: "var(--mantine-color-gray-3)" }}>
              <Title order={5} mb="xs" style={{ color: "#0f172a" }}>
                Мониторинг инфраструктуры
              </Title>
              <Text size="sm" c="dimmed" mb="md">
                Prometheus метрики и дашборды собираются в реальном времени.
              </Text>
              <Button
                component="a"
                href={grafanaUrl}
                target="_blank"
                rel="noopener noreferrer"
                variant="default"
                leftSection={<IconExternalLink size={16} aria-hidden />}
              >
                Открыть Grafana
              </Button>
            </Paper>
          </SimpleGrid>

          <PlatformFounderTotpSetupModal opened={totpModalOpen} onClose={totpModalHandlers.close} />
        </Stack>
      </Container>
    </Box>
  );
}
