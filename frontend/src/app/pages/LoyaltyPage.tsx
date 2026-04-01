import { useNavigate } from "react-router-dom";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { usePatientLoyaltyMe, usePatientLoyaltyHistory } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import type { PatientLoyaltyMeResponse, PatientLoyaltyHistoryResponse } from "@/api/types";
import { Badge, Button, Card, Group, Loader, Progress, Stack, Table, Text, Title } from "@mantine/core";
import { ROUTE_PATHS } from "@/routePaths";
import { SEMANTIC } from "@/shared/semanticUi";
import { QueryErrorAlert } from "@/shared/ui";

export default function LoyaltyPage() {
  const { accessToken } = usePatientAuth();
  const navigate = useNavigate();
  const {
    data: loyaltyMe,
    isLoading: meLoading,
    isError: meError,
    error: meErrorObj,
  } = usePatientLoyaltyMe(accessToken);
  const {
    data: history,
    isLoading: historyLoading,
    isError: historyError,
    error: historyErrorObj,
  } = usePatientLoyaltyHistory(accessToken);

  if (meLoading || historyLoading) return <Loader />;
  if (meError)
    return (
      <Stack>
        <QueryErrorAlert error={meErrorObj} title="Не удалось загрузить данные лояльности" />
      </Stack>
    );
  if (historyError)
    return (
      <Stack>
        <QueryErrorAlert error={historyErrorObj} title="Не удалось загрузить историю" />
      </Stack>
    );

  if (!loyaltyMe || (!loyaltyMe.subscriptions.length && !loyaltyMe.wallet)) {
    return (
      <EmptyStateHint
        title="Пока нет абонементов и баллов"
        subtitle="Оформите пакет или завершите визит, чтобы получить кэшбэк."
      />
    );
  }

  const activeSubs = loyaltyMe.subscriptions.filter(
    (s: PatientLoyaltyMeResponse["subscriptions"][number]) => s.status === "active"
  );
  const expiredSubs = loyaltyMe.subscriptions.filter(
    (s: PatientLoyaltyMeResponse["subscriptions"][number]) => s.status !== "active"
  );

  const handleBookVisit = () => {
    navigate(ROUTE_PATHS.patient.booking);
  };

  const handleBookWithPoints = () => {
    navigate(`${ROUTE_PATHS.patient.booking}?use_loyalty=wallet`);
  };

  const handleUseSubscription = (subscriptionId: string) => {
    navigate(`${ROUTE_PATHS.patient.booking}?subscription_id=${encodeURIComponent(subscriptionId)}`);
  };

  return (
    <Stack>
      <Title order={3}>Мои абонементы и баллы</Title>

      {loyaltyMe.wallet && (
        <Card shadow="sm" padding="md" withBorder>
          <Group justify="space-between" align="center">
            <Stack gap={4}>
              <Text size="sm" c="dimmed">
                Баланс кошелька
              </Text>
              <Text size="lg" fw={600}>
                {loyaltyMe.wallet.balance} {loyaltyMe.wallet.currency}
              </Text>
            </Stack>
            <Group gap="xs">
              <Badge color="green" variant="light">
                Обновлено {new Date(loyaltyMe.wallet.updated_at).toLocaleString()}
              </Badge>
              <Button size="xs" variant="light" onClick={handleBookWithPoints}>
                Записаться и использовать баллы
              </Button>
            </Group>
          </Group>
        </Card>
      )}

      <Card shadow="sm" padding="md" withBorder>
        <Text size="sm" fw={500} mb="sm">
          Digital Pass — Абонементы
        </Text>
        {activeSubs.length === 0 ? (
          <Text size="sm" c="dimmed">
            Сейчас нет активных абонементов.
          </Text>
        ) : (
          <>
            <Stack gap="md">
              {activeSubs.map(
                (s: PatientLoyaltyMeResponse["subscriptions"][number]) => {
                  const totalVisits = s.remaining_visits != null ? Math.max(s.remaining_visits, 10) : 10;
                  const progressPct = totalVisits > 0 ? ((s.remaining_visits ?? 0) / totalVisits) * 100 : 0;
                  return (
                    <Card
                      key={s.id}
                      padding="md"
                      radius="lg"
                      style={{
                        background:
                          "linear-gradient(135deg, var(--mantine-color-indigo-7) 0%, var(--mantine-color-blue-7) 100%)",
                        color: "var(--text-on-primary)",
                        border: "none",
                      }}
                    >
                      <Stack gap="xs">
                        <Text size="sm" fw={600} opacity={0.95}>
                          Пакет {s.subscription_package_id.slice(0, 8)}…
                        </Text>
                        {(s.remaining_visits != null || s.remaining_amount != null) && (
                          <Group gap="lg">
                            {s.remaining_visits != null && (
                              <Text size="xs" opacity={0.9}>
                                {s.remaining_visits} из {totalVisits} визитов
                              </Text>
                            )}
                            {s.remaining_amount != null && (
                              <Text size="xs" opacity={0.9}>
                                Остаток: {s.remaining_amount} ₽
                              </Text>
                            )}
                          </Group>
                        )}
                        {s.remaining_visits != null && totalVisits > 0 && (
                          <Progress
                            value={progressPct}
                            size="sm"
                            color="white"
                            style={{ opacity: 0.8 }}
                          />
                        )}
                        {s.expires_at && (
                          <Text size="xs" opacity={0.85}>
                            Действует до: {new Date(s.expires_at).toLocaleDateString("ru-RU")}
                          </Text>
                        )}
                        <Button
                          size="sm"
                          variant="white"
                          color={SEMANTIC.action.confirm}
                          fullWidth
                          mt="xs"
                          onClick={() => handleUseSubscription(s.id)}
                        >
                          Записаться по абонементу
                        </Button>
                      </Stack>
                    </Card>
                  );
                },
              )}
            </Stack>
            <Group justify="flex-end" mt="md">
              <Button
                size="sm"
                variant="outline"
                color={SEMANTIC.action.confirm}
                onClick={handleBookVisit}
              >
                Записаться без пакета
              </Button>
            </Group>
          </>
        )}
      </Card>

      {expiredSubs.length > 0 && (
        <Card shadow="sm" padding="md" withBorder>
          <Text size="sm" fw={500} mb="sm">
            Истёкшие абонементы
          </Text>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Пакет</Table.Th>
                <Table.Th>Статус</Table.Th>
                <Table.Th>Действовал до</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {expiredSubs.map(
                (s: PatientLoyaltyMeResponse["subscriptions"][number]) => (
                <Table.Tr key={s.id}>
                  <Table.Td>{s.subscription_package_id.slice(0, 8)}…</Table.Td>
                  <Table.Td>{s.status}</Table.Td>
                  <Table.Td>{s.expires_at ?? "—"}</Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {history && history.items.length > 0 && (
        <Card shadow="sm" padding="md" withBorder>
          <Text size="sm" fw={500} mb="sm">
            История использования
          </Text>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>Дата</Table.Th>
                <Table.Th>Тип</Table.Th>
                <Table.Th>Детали</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {history.items.map(
                (
                  item: PatientLoyaltyHistoryResponse["items"][number],
                  idx: number,
                ) => (
                <Table.Tr key={idx}>
                  <Table.Td>
                    {new Date(item.happened_at).toLocaleDateString("ru-RU", {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                    })}
                  </Table.Td>
                  <Table.Td>{item.kind}</Table.Td>
                  <Table.Td>
                    {item.kind.startsWith("wallet_")
                      ? `${item.details.amount} · ${item.details.description ?? ""}`
                      : `Визитов: ${item.details.used_visits ?? "—"}, сумма: ${
                          item.details.used_amount ?? "—"
                        }`}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}
    </Stack>
  );
}

