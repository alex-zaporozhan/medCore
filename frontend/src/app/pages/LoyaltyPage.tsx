import { useNavigate } from "react-router-dom";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { usePatientLoyaltyMe, usePatientLoyaltyHistory } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import type { PatientLoyaltyMeResponse, PatientLoyaltyHistoryResponse } from "@/api/types";
import { Badge, Button, Card, Group, Loader, Progress, Stack, Table, Text, Title } from "@mantine/core";
import { ROUTE_PATHS } from "@/routePaths";
import { SEMANTIC } from "@/shared/semanticUi";
import { QueryErrorAlert } from "@/shared/ui";
import { useTranslation } from "react-i18next";

function membershipLabel(
  s: PatientLoyaltyMeResponse["subscriptions"][number],
  fallback: string,
): string {
  const note = s.notes?.trim();
  if (note) return note;
  return fallback;
}

export default function LoyaltyPage() {
  const { t, i18n } = useTranslation("patient");
  const dateLocale = i18n.language?.startsWith("ru") ? "ru-RU" : "en-GB";
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
        <QueryErrorAlert error={meErrorObj} title={t("loyalty.loadFailed")} />
      </Stack>
    );
  if (historyError)
    return (
      <Stack>
        <QueryErrorAlert error={historyErrorObj} title={t("loyalty.historyFailed")} />
      </Stack>
    );

  if (!loyaltyMe || (!loyaltyMe.subscriptions.length && !loyaltyMe.wallet)) {
    return (
      <EmptyStateHint
        title={t("loyalty.emptyTitle")}
        subtitle={t("loyalty.emptyHint")}
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
      <Title order={3}>{t("loyalty.title")}</Title>

      {loyaltyMe.wallet && (
        <Card shadow="sm" padding="md" withBorder>
          <Group justify="space-between" align="center">
            <Stack gap={4}>
              <Text size="sm" c="dimmed">
                {t("loyalty.wallet")}
              </Text>
              <Text size="lg" fw={600}>
                {loyaltyMe.wallet.balance} {loyaltyMe.wallet.currency}
              </Text>
            </Stack>
            <Group gap="xs">
              <Badge color="green" variant="light">
                {t("loyalty.updated", {
                  when: new Date(loyaltyMe.wallet.updated_at).toLocaleString(dateLocale),
                })}
              </Badge>
              <Button size="xs" variant="light" onClick={handleBookWithPoints}>
                {t("loyalty.bookWithPoints")}
              </Button>
            </Group>
          </Group>
        </Card>
      )}

      <Card shadow="sm" padding="md" withBorder>
        <Text size="sm" fw={500} mb="sm">
          {t("loyalty.passes")}
        </Text>
        {activeSubs.length === 0 ? (
          <Text size="sm" c="dimmed">
            {t("loyalty.noActive")}
          </Text>
        ) : (
          <>
            <Stack gap="md">
              {activeSubs.map(
                (s: PatientLoyaltyMeResponse["subscriptions"][number]) => {
                  const totalVisits = s.remaining_visits != null ? Math.max(s.remaining_visits, 10) : 10;
                  const progressPct = totalVisits > 0 ? ((s.remaining_visits ?? 0) / totalVisits) * 100 : 0;
                  return (
                    <Card key={s.id} padding="md" radius="md" withBorder>
                      <Stack gap="xs">
                        <Text size="sm" fw={600}>
                          {membershipLabel(s, t("loyalty.membership"))}
                        </Text>
                        {(s.remaining_visits != null || s.remaining_amount != null) && (
                          <Group gap="lg">
                            {s.remaining_visits != null && (
                              <Text size="xs" c="dimmed">
                                {t("loyalty.visitsLeft", {
                                  remaining: s.remaining_visits,
                                  total: totalVisits,
                                })}
                              </Text>
                            )}
                            {s.remaining_amount != null && (
                              <Text size="xs" c="dimmed">
                                {t("loyalty.amountLeft", { amount: s.remaining_amount })}
                              </Text>
                            )}
                          </Group>
                        )}
                        {s.remaining_visits != null && totalVisits > 0 && (
                          <Progress value={progressPct} size="sm" />
                        )}
                        {s.expires_at && (
                          <Text size="xs" c="dimmed">
                            {t("loyalty.validUntil", {
                              date: new Date(s.expires_at).toLocaleDateString(dateLocale),
                            })}
                          </Text>
                        )}
                        <Button
                          size="sm"
                          color={SEMANTIC.action.confirm}
                          fullWidth
                          mt="xs"
                          onClick={() => handleUseSubscription(s.id)}
                        >
                          {t("loyalty.bookWithPass")}
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
                {t("loyalty.bookWithout")}
              </Button>
            </Group>
          </>
        )}
      </Card>

      {expiredSubs.length > 0 && (
        <Card shadow="sm" padding="md" withBorder>
          <Text size="sm" fw={500} mb="sm">
            {t("loyalty.expired")}
          </Text>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("loyalty.colPackage")}</Table.Th>
                <Table.Th>{t("loyalty.colStatus")}</Table.Th>
                <Table.Th>{t("loyalty.colUntil")}</Table.Th>
              </Table.Tr>
            </Table.Thead>
            <Table.Tbody>
              {expiredSubs.map(
                (s: PatientLoyaltyMeResponse["subscriptions"][number]) => (
                <Table.Tr key={s.id}>
                  <Table.Td>{membershipLabel(s, t("loyalty.membership"))}</Table.Td>
                  <Table.Td>{s.status}</Table.Td>
                  <Table.Td>
                    {s.expires_at
                      ? new Date(s.expires_at).toLocaleDateString(dateLocale)
                      : "—"}
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        </Card>
      )}

      {history && history.items.length > 0 && (
        <Card shadow="sm" padding="md" withBorder>
          <Text size="sm" fw={500} mb="sm">
            {t("loyalty.history")}
          </Text>
          <Table striped>
            <Table.Thead>
              <Table.Tr>
                <Table.Th>{t("loyalty.colDate")}</Table.Th>
                <Table.Th>{t("loyalty.colType")}</Table.Th>
                <Table.Th>{t("loyalty.colDetails")}</Table.Th>
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
                    {new Date(item.happened_at).toLocaleDateString(dateLocale, {
                      day: "2-digit",
                      month: "2-digit",
                      year: "numeric",
                    })}
                  </Table.Td>
                  <Table.Td>{item.kind}</Table.Td>
                  <Table.Td>
                    {item.kind.startsWith("wallet_")
                      ? t("loyalty.historyWallet", {
                          amount: String(item.details.amount ?? "—"),
                          description: String(item.details.description ?? ""),
                        })
                      : t("loyalty.historyVisits", {
                          visits: String(item.details.used_visits ?? "—"),
                          amount: String(item.details.used_amount ?? "—"),
                        })}
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
