import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useLoyaltyPackages,
  useCustomerSubscriptions,
  useWallets,
  useWalletTransactions,
} from "@/hooks";
import {
  Card,
  Group,
  Loader,
  Stack,
  Table,
  Tabs,
  Text,
  Title,
  TextInput,
} from "@mantine/core";

export default function AdminLoyaltyPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const [searchParams] = useSearchParams();
  const initialPatientId = searchParams.get("patient_id") ?? "";
  const [patientIdFilter, setPatientIdFilter] = useState<string>(initialPatientId);
  const [selectedWalletId, setSelectedWalletId] = useState<string | null>(null);

  const { data: packages, isLoading: packagesLoading } = useLoyaltyPackages();
  const { data: subs, isLoading: subsLoading } = useCustomerSubscriptions(
    patientIdFilter || null,
    false,
  );
  const { data: wallets, isLoading: walletsLoading } = useWallets(
    patientIdFilter || null,
  );
  const {
    data: walletTxs,
    isLoading: walletTxsLoading,
  } = useWalletTransactions(selectedWalletId);

  const loading =
    packagesLoading || subsLoading || walletsLoading || walletTxsLoading;

  if (!clinicId) {
    return (
      <Stack>
        <Title order={3}>Лояльность</Title>
        <Text size="sm" c="dimmed">
          Выберите клинику в шапке, чтобы работать с программами лояльности.
        </Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <Group justify="space-between">
        <Title order={3}>Лояльность</Title>
        <Text size="xs" c="dimmed">
          Пакеты абонементов и кошельки пациентов.
        </Text>
      </Group>

      {loading && <Loader size="sm" />}

      <Tabs defaultValue="packages" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="packages">Пакеты</Tabs.Tab>
          <Tabs.Tab value="subscriptions">Абонементы</Tabs.Tab>
          <Tabs.Tab value="wallets">Кошельки</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="packages" pt="md">
          <Card shadow="sm" padding="md" withBorder>
            <Text size="sm" fw={500} mb="sm">
              Пакеты абонементов
            </Text>
            {packages && packages.length === 0 && (
              <Text size="sm" c="dimmed">
                Пакеты ещё не созданы. Добавьте их через админку или API.
              </Text>
            )}
            {packages && packages.length > 0 && (
              <Table highlightOnHover striped withColumnBorders>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Код</Table.Th>
                    <Table.Th>Название</Table.Th>
                    <Table.Th>Тип</Table.Th>
                    <Table.Th>Визитов</Table.Th>
                    <Table.Th>Баланс</Table.Th>
                    <Table.Th>Цена</Table.Th>
                    <Table.Th>Срок (дн.)</Table.Th>
                    <Table.Th>Активен</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {packages.map((p) => (
                    <Table.Tr key={p.id}>
                      <Table.Td>{p.code}</Table.Td>
                      <Table.Td>{p.name}</Table.Td>
                      <Table.Td>{p.kind}</Table.Td>
                      <Table.Td>{p.total_visits ?? "—"}</Table.Td>
                      <Table.Td>{p.total_amount ?? "—"}</Table.Td>
                      <Table.Td>{p.price}</Table.Td>
                      <Table.Td>{p.validity_days ?? "—"}</Table.Td>
                      <Table.Td>{p.is_active ? "Да" : "Нет"}</Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
        </Tabs.Panel>

        <Tabs.Panel value="subscriptions" pt="md">
          <Stack>
            <TextInput
              label="ID пациента"
              placeholder="Вставьте UUID пациента для поиска его абонементов"
              value={patientIdFilter}
              onChange={(e) => setPatientIdFilter(e.currentTarget.value)}
            />
            <Card shadow="sm" padding="md" withBorder>
              <Text size="sm" fw={500} mb="sm">
                Абонементы пациента
              </Text>
              {subs && subs.length === 0 && (
                <Text size="sm" c="dimmed">
                  Для указанного пациента нет абонементов.
                </Text>
              )}
              {subs && subs.length > 0 && (
                <Table highlightOnHover striped withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Пакет</Table.Th>
                      <Table.Th>Статус</Table.Th>
                      <Table.Th>Остаток визитов</Table.Th>
                      <Table.Th>Остаток суммы</Table.Th>
                      <Table.Th>Истекает</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {subs.map((s) => (
                      <Table.Tr key={s.id}>
                        <Table.Td>{s.id.slice(0, 8)}…</Table.Td>
                        <Table.Td>{s.subscription_package_id.slice(0, 8)}…</Table.Td>
                        <Table.Td>{s.status}</Table.Td>
                        <Table.Td>{s.remaining_visits ?? "—"}</Table.Td>
                        <Table.Td>{s.remaining_amount ?? "—"}</Table.Td>
                        <Table.Td>{s.expires_at ?? "—"}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="wallets" pt="md">
          <Stack>
            <TextInput
              label="ID пациента"
              placeholder="Вставьте UUID пациента для поиска кошелька"
              value={patientIdFilter}
              onChange={(e) => setPatientIdFilter(e.currentTarget.value)}
            />
            <Card shadow="sm" padding="md" withBorder>
              <Text size="sm" fw={500} mb="sm">
                Кошелёк пациента
              </Text>
              {wallets && wallets.length === 0 && (
                <Text size="sm" c="dimmed">
                  Кошелёк для указанного пациента ещё не создан.
                </Text>
              )}
              {wallets && wallets.length > 0 && (
                <Table highlightOnHover striped withColumnBorders>
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>ID</Table.Th>
                      <Table.Th>Баланс</Table.Th>
                      <Table.Th>Валюта</Table.Th>
                      <Table.Th>Обновлён</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {wallets.map((w) => (
                      <Table.Tr
                        key={w.id}
                        onClick={() => setSelectedWalletId(w.id)}
                        style={{ cursor: "pointer" }}
                      >
                        <Table.Td>{w.id.slice(0, 8)}…</Table.Td>
                        <Table.Td>{w.balance}</Table.Td>
                        <Table.Td>{w.currency}</Table.Td>
                        <Table.Td>{w.updated_at}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
            {selectedWalletId && (
              <Card shadow="sm" padding="md" withBorder>
                <Text size="sm" fw={500} mb="sm">
                  Движения по кошельку
                </Text>
                {walletTxs && walletTxs.length === 0 && (
                  <Text size="sm" c="dimmed">
                    Для выбранного кошелька пока нет транзакций.
                  </Text>
                )}
                {walletTxs && walletTxs.length > 0 && (
                  <Table highlightOnHover striped withColumnBorders>
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Дата</Table.Th>
                        <Table.Th>Тип</Table.Th>
                        <Table.Th>Сумма</Table.Th>
                        <Table.Th>Описание</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {walletTxs.map((t) => (
                        <Table.Tr key={t.id}>
                          <Table.Td>{t.happened_at}</Table.Td>
                          <Table.Td>{t.type}</Table.Td>
                          <Table.Td>{t.amount}</Table.Td>
                          <Table.Td>{t.description ?? "—"}</Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                )}
              </Card>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Stack>
  );
}

