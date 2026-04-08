import { API_BASE } from "@/api/client";
import { PlatformFounderTotpSetupModal } from "@/marketing/components/PlatformFounderTotpSetupModal";
import { usePlatformFounderSession } from "@/marketing/contexts/PlatformFounderSessionContext";
import { ROUTE_PATHS } from "@/routePaths";
import { Anchor, Button, Container, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { useDisclosure } from "@mantine/hooks";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";

/**
 * Минимальный дашборд §7.1: health JWT + сводка по очереди провижининга (данные тех же API, что и в таблице).
 */
export default function PlatformFounderDashboardPage() {
  const { token } = usePlatformFounderSession();
  const [totpModalOpen, totpModalHandlers] = useDisclosure(false);

  const healthQ = useQuery({
    queryKey: ["platform-founder", "health", token],
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/health`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        throw new Error(await r.text().catch(() => `HTTP ${r.status}`));
      }
      return r.json() as Promise<{ scope: string; status: string }>;
    },
  });

  const queueQ = useQuery({
    queryKey: ["platform-founder", "provision-queue", token],
    queryFn: async () => {
      const r = await fetch(`${API_BASE}/v1/platform/internal/provision-queue`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) {
        throw new Error(await r.text().catch(() => `HTTP ${r.status}`));
      }
      return r.json() as Promise<Array<{ status: string; email: string | null; organization_id: string | null }>>;
    },
  });

  const statusCounts = (queueQ.data ?? []).reduce<Record<string, number>>((acc, row) => {
    const k = row.status || "unknown";
    acc[k] = (acc[k] ?? 0) + 1;
    return acc;
  }, {});

  const withOrg = (queueQ.data ?? []).filter((r) => r.organization_id).length;

  return (
    <Container size="lg" py="xl">
      <Stack gap="lg">
        <div>
          <Title order={2}>Обзор</Title>
          <Text size="sm" c="dimmed" mt={4}>
            JWT проверен через <Text span ff="monospace">GET /api/v1/platform/internal/health</Text>; список намерений —
            общий с разделом очереди (§7.2 — владельцы в контексте org из строк очереди).
          </Text>
        </div>

        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between" mb="sm" wrap="wrap">
            <Title order={4}>Состояние сессии</Title>
            <Button size="xs" variant="light" onClick={totpModalHandlers.open}>
              Привязать TOTP / Google Authenticator
            </Button>
          </Group>
          {healthQ.isLoading ? <Text size="sm">Загрузка…</Text> : null}
          {healthQ.error ? (
            <Text size="sm" c="red">
              {(healthQ.error as Error).message}
            </Text>
          ) : null}
          {healthQ.data ? (
            <Text size="sm">
              scope: <Text span ff="monospace">{healthQ.data.scope}</Text>, status:{" "}
              <Text span ff="monospace">{healthQ.data.status}</Text>
            </Text>
          ) : null}
        </Paper>

        <Paper p="md" radius="md" withBorder>
          <Group justify="space-between" mb="sm">
            <Title order={4}>Очередь signup / провижининг</Title>
            <Anchor component={Link} to={ROUTE_PATHS.platform.provisionQueue} size="sm">
              Открыть таблицу →
            </Anchor>
          </Group>
          {queueQ.isLoading ? <Text size="sm">Загрузка…</Text> : null}
          {queueQ.error ? (
            <Text size="sm" c="red">
              {(queueQ.error as Error).message}
            </Text>
          ) : null}
          {queueQ.data ? (
            <Stack gap="xs">
              <Text size="sm">
                Всего записей: <strong>{queueQ.data.length}</strong>, с привязанной организацией:{" "}
                <strong>{withOrg}</strong>
              </Text>
              {Object.keys(statusCounts).length ? (
                <Text size="sm" c="dimmed">
                  По статусам:{" "}
                  {Object.entries(statusCounts)
                    .map(([k, n]) => `${k}: ${n}`)
                    .join("; ")}
                </Text>
              ) : (
                <Text size="sm" c="dimmed">
                  Пока нет строк в очереди.
                </Text>
              )}
            </Stack>
          ) : null}
        </Paper>

        <PlatformFounderTotpSetupModal opened={totpModalOpen} onClose={totpModalHandlers.close} />
      </Stack>
    </Container>
  );
}
