import { useNavigate } from "react-router-dom";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { usePatientLoyaltyMe, usePatientLoyaltyHistory } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import type { PatientLoyaltyMeResponse, PatientLoyaltyHistoryResponse } from "@/api/types";
import { Badge, Button, Card, Group, Loader, Stack, Table, Text, Title } from "@mantine/core";

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
      <Text c="red">
        {meErrorObj instanceof Error ? meErrorObj.message : "Ошибка загрузки лояльности"}
      </Text>
    );
  if (historyError)
    return (
      <Text c="red">
        {historyErrorObj instanceof Error
          ? historyErrorObj.message
          : "Ошибка загрузки истории"}
      </Text>
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
    navigate("/app/booking");
  };

  const handleBookWithPoints = () => {
    navigate("/app/booking?use_loyalty=wallet");
  };

  const handleUseSubscription = (subscriptionId: string) => {
    navigate(`/app/booking?subscription_id=${encodeURIComponent(subscriptionId)}`);
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
          Активные абонементы
        </Text>
        {activeSubs.length === 0 ? (
          <Text size="sm" c="dimmed">
            Сейчас нет активных абонементов.
          </Text>
        ) : (
          <>
            <Table striped>
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Пакет</Table.Th>
                  <Table.Th>Остаток визитов</Table.Th>
                  <Table.Th>Остаток суммы</Table.Th>
                  <Table.Th>Действует до</Table.Th>
                  <Table.Th />
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {activeSubs.map(
                  (s: PatientLoyaltyMeResponse["subscriptions"][number]) => (
                    <Table.Tr key={s.id}>
                      <Table.Td>{s.subscription_package_id.slice(0, 8)}…</Table.Td>
                      <Table.Td>{s.remaining_visits ?? "—"}</Table.Td>
                      <Table.Td>{s.remaining_amount ?? "—"}</Table.Td>
                      <Table.Td>{s.expires_at ?? "—"}</Table.Td>
                      <Table.Td>
                        <Button
                          size="xs"
                          variant="light"
                          onClick={() => handleUseSubscription(s.id)}
                        >
                          Записаться и использовать пакет
                        </Button>
                      </Table.Td>
                    </Table.Tr>
                  ),
                )}
              </Table.Tbody>
            </Table>
            <Group justify="flex-end" mt="sm">
              <Button size="sm" variant="outline" onClick={handleBookVisit}>
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

