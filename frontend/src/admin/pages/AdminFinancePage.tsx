import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useCashboxes,
  useFinanceTransactions,
  useFinanceLiability,
  useCreateFinanceTransaction,
  useInventoryProducts,
  useWarehouses,
  usePayrollPolicies,
  useSalaryTransactions,
  useInventoryTransactions,
  useInventoryStock,
} from "@/hooks";
import {
  ActionIcon,
  Anchor,
  Button,
  Card,
  Group,
  Menu,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { IconDotsVertical, IconPlus, IconMinus, IconTransfer } from "@tabler/icons-react";
import { AdminDrawer, EmptyState, ContextBar, PageSkeleton } from "@/shared/ui";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";

type TxDrawerMode = "income" | "expense" | "transfer" | null;

export default function AdminFinancePage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;

  const [selectedCashboxId, setSelectedCashboxId] = useState<string | null>(null);
  const [selectedDoctorId, setSelectedDoctorId] = useState<string | null>(null);
  const [selectedProductId, setSelectedProductId] = useState<string | null>(null);
  const [selectedWarehouseId, setSelectedWarehouseId] = useState<string | null>(null);

  const [txDrawerOpen, setTxDrawerOpen] = useState(false);
  const [txDrawerMode, setTxDrawerMode] = useState<TxDrawerMode>(null);
  const [txDrawerCashboxId, setTxDrawerCashboxId] = useState<string | null>(null);
  const [txAmount, setTxAmount] = useState<string>("");
  const [txCategory, setTxCategory] = useState("");
  const [txFromCashboxId, setTxFromCashboxId] = useState<string | null>(null);
  const [txToCashboxId, setTxToCashboxId] = useState<string | null>(null);

  const today = dayjs().format("YYYY-MM-DD");
  const [txDateFrom] = useState<string | null>(
    dayjs().subtract(7, "day").format("YYYY-MM-DD")
  );
  const [txDateTo] = useState<string | null>(today);

  const [invDateFrom, setInvDateFrom] = useState<string | null>(
    dayjs().subtract(30, "day").format("YYYY-MM-DD")
  );
  const [invDateTo, setInvDateTo] = useState<string | null>(today);

  const { data: cashboxes, isLoading: cashboxesLoading } = useCashboxes(clinicId);
  const { data: liability } = useFinanceLiability(clinicId);
  const createTx = useCreateFinanceTransaction(clinicId);
  const { data: txs, isLoading: txsLoading } = useFinanceTransactions(clinicId, {
    cashbox_id: selectedCashboxId,
    date_from: txDateFrom,
    date_to: txDateTo,
  });

  const { data: payrollPolicies, isLoading: payrollLoading } = usePayrollPolicies(clinicId);
  const { data: salaryTxs, isLoading: salaryLoading } = useSalaryTransactions(
    clinicId,
    selectedDoctorId,
    null,
    null
  );

  const { data: products, isLoading: productsLoading } = useInventoryProducts(clinicId);
  const { data: warehouses, isLoading: warehousesLoading } = useWarehouses(clinicId);
  const { data: inventoryTxs, isLoading: inventoryTxsLoading } = useInventoryTransactions(
    clinicId,
    selectedProductId,
    selectedWarehouseId,
    invDateFrom,
    invDateTo
  );
  const { data: inventoryStock, isLoading: inventoryStockLoading } = useInventoryStock(
    clinicId,
    selectedProductId,
    selectedWarehouseId
  );

  const loading =
    cashboxesLoading ||
    txsLoading ||
    payrollLoading ||
    salaryLoading ||
    productsLoading ||
    warehousesLoading ||
    inventoryTxsLoading ||
    inventoryStockLoading;

  const cashboxOptions =
    cashboxes?.map((c) => ({
      value: c.id,
      label: `${c.name} (${c.type})${c.is_default ? " · по умолчанию" : ""}`,
    })) ?? [];

  const doctorOptions = useMemo(() => {
    const seen = new Set<string>();
    const result: { value: string; label: string }[] = [];
    salaryTxs?.forEach((tx) => {
      if (!seen.has(tx.doctor_id)) {
        seen.add(tx.doctor_id);
        result.push({ value: tx.doctor_id, label: tx.doctor_id });
      }
    });
    return result;
  }, [salaryTxs]);

  const salarySummary = useMemo(() => {
    if (!salaryTxs || salaryTxs.length === 0) {
      return null;
    }
    const total = salaryTxs.reduce((acc, tx) => acc + Number(tx.amount), 0);
    const avg = salaryTxs.length > 0 ? total / salaryTxs.length : 0;
    return {
      total,
      avg,
      count: salaryTxs.length,
    };
  }, [salaryTxs]);

  const payrollByDoctor = useMemo(() => {
    if (!salaryTxs || salaryTxs.length === 0) return [];
    const byId = new Map<string, { doctorId: string; total: number; count: number }>();
    for (const tx of salaryTxs) {
      const cur = byId.get(tx.doctor_id);
      const amount = Number(tx.amount);
      if (!cur) {
        byId.set(tx.doctor_id, { doctorId: tx.doctor_id, total: amount, count: 1 });
      } else {
        cur.total += amount;
        cur.count += 1;
      }
    }
    return Array.from(byId.values()).sort((a, b) => b.total - a.total);
  }, [salaryTxs]);

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Финансы" />
        <Text size="sm" c="dimmed">
          Выберите клинику в шапке, чтобы работать с финансами и складом.
        </Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Финансы и ERP" />

      {loading && <PageSkeleton variant="table" rows={6} />}

      <Tabs defaultValue="cashboxes" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="cashboxes">Кассы</Tabs.Tab>
          <Tabs.Tab value="transactions">Транзакции</Tabs.Tab>
          <Tabs.Tab value="payroll">Зарплаты</Tabs.Tab>
          <Tabs.Tab value="inventory">Склад</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="cashboxes" pt="md">
          <Card shadow="sm" padding="md" withBorder className="data-table-card">
            <Text size="sm" fw={500} mb="sm">
              Кассы клиники
            </Text>
            {cashboxes && cashboxes.length === 0 && (
              <EmptyState
                title="Нет касс"
                description="Добавьте первую кассу для учёта наличных и безнала."
                action={{
                  label: "Добавить кассу",
                  onClick: () => {},
                }}
              />
            )}
            {cashboxes && cashboxes.length > 0 && (
              <Table withRowBorders highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Название</Table.Th>
                    <Table.Th>Баланс</Table.Th>
                    <Table.Th>Тип</Table.Th>
                    <Table.Th>Валюта</Table.Th>
                    <Table.Th>По умолчанию</Table.Th>
                    <Table.Th>Активна</Table.Th>
                    <Table.Th w={50}></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {cashboxes.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td>{c.name}</Table.Td>
                      <Table.Td>
                        {c.balance != null
                          ? `${Number(c.balance).toLocaleString("ru-RU")} ${c.currency}`
                          : "—"}
                      </Table.Td>
                      <Table.Td>{c.type}</Table.Td>
                      <Table.Td>{c.currency}</Table.Td>
                      <Table.Td>{c.is_default ? "Да" : "Нет"}</Table.Td>
                      <Table.Td>{c.is_active ? "Да" : "Нет"}</Table.Td>
                      <Table.Td>
                        <Menu position="bottom-end">
                          <Menu.Target>
                            <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                              <IconDotsVertical size={16} />
                            </ActionIcon>
                          </Menu.Target>
                          <Menu.Dropdown>
                            <Menu.Item
                              leftSection={<IconPlus size={14} />}
                              onClick={() => {
                                setTxDrawerMode("income");
                                setTxDrawerCashboxId(c.id);
                                setTxFromCashboxId(null);
                                setTxToCashboxId(null);
                                setTxAmount("");
                                setTxCategory("");
                                setTxDrawerOpen(true);
                              }}
                            >
                              Внести
                            </Menu.Item>
                            <Menu.Item
                              leftSection={<IconMinus size={14} />}
                              onClick={() => {
                                setTxDrawerMode("expense");
                                setTxDrawerCashboxId(c.id);
                                setTxFromCashboxId(null);
                                setTxToCashboxId(null);
                                setTxAmount("");
                                setTxCategory("");
                                setTxDrawerOpen(true);
                              }}
                            >
                              Изъять
                            </Menu.Item>
                            <Menu.Item
                              leftSection={<IconTransfer size={14} />}
                              onClick={() => {
                                setTxDrawerMode("transfer");
                                setTxDrawerCashboxId(null);
                                setTxFromCashboxId(c.id);
                                setTxToCashboxId(null);
                                setTxAmount("");
                                setTxCategory("Перевод");
                                setTxDrawerOpen(true);
                              }}
                            >
                              Перевод
                            </Menu.Item>
                          </Menu.Dropdown>
                        </Menu>
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            )}
          </Card>
          {liability && (
            <Card shadow="sm" padding="md" withBorder mt="md" className="data-toolbar-card">
              <Text size="sm" fw={500} c="dimmed" mb="xs">
                Деньги в воздухе (Unearned Revenue)
              </Text>
              <Text size="lg" fw={600}>
                {liability.unearned_revenue} ₽
              </Text>
              <Text size="xs" c="dimmed">
                Активных абонементов: {liability.active_subscriptions_count}
              </Text>
            </Card>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="transactions" pt="md">
          <ThreeColumnLayout
            preset="wide-center"
            left={
              <Stack gap="sm" p="xs">
                <Text size="sm" fw={500}>
                  Фильтры движения денег
                </Text>
                <Select
                  label="Касса"
                  placeholder="Все кассы"
                  data={cashboxOptions}
                  value={selectedCashboxId}
                  onChange={setSelectedCashboxId}
                  clearable
                />
                <Text size="xs" c="dimmed">
                  Период:{" "}
                  {txDateFrom && txDateTo
                    ? `${dayjs(txDateFrom).format("DD.MM.YYYY")} — ${dayjs(txDateTo).format(
                        "DD.MM.YYYY",
                      )}`
                    : "по умолчанию за последнюю неделю"}
                </Text>
              </Stack>
            }
            center={
              <Card shadow="sm" padding="md" withBorder className="data-table-card">
                <Text size="sm" fw={500} mb="sm">
                  Движение денег по кассам
                </Text>
                {txs && txs.length === 0 && (
                  <Text size="sm" c="dimmed">
                    Нет финансовых транзакций за выбранный период.
                  </Text>
                )}
                {txs && txs.length > 0 && (
                  <Table withRowBorders highlightOnHover verticalSpacing="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Дата</Table.Th>
                        <Table.Th>Тип</Table.Th>
                        <Table.Th>Сумма</Table.Th>
                        <Table.Th>Источник</Table.Th>
                        <Table.Th>Бронь</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {txs.map((t) => (
                        <Table.Tr key={t.id}>
                          <Table.Td>{dayjs(t.happened_at).format("DD.MM.YYYY HH:mm")}</Table.Td>
                          <Table.Td>{t.type}</Table.Td>
                          <Table.Td>
                            {t.amount} {t.currency}
                          </Table.Td>
                          <Table.Td>{t.source}</Table.Td>
                          <Table.Td>
                            {t.booking_id ? (
                              <Anchor size="xs" c="blue">
                                {t.booking_id.slice(0, 8)}…
                              </Anchor>
                            ) : (
                              "-"
                            )}
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                )}
              </Card>
            }
            right={
              <Card shadow="sm" padding="md" withBorder className="data-toolbar-card">
                <Text size="sm" fw={500} mb="xs">
                  Итого по транзакциям
                </Text>
                <Text size="xs" c="dimmed" mb="sm">
                  Быстрый взгляд на оборот по выбранным фильтрам. Детальные отчёты доступны в
                  разделе Analytics.
                </Text>
                {txs && txs.length > 0 ? (
                  <Stack gap={4}>
                    <Text size="sm">
                      Всего операций: <strong>{txs.length}</strong>
                    </Text>
                  </Stack>
                ) : (
                  <Text size="xs" c="dimmed">
                    Данных для расчёта итогов пока нет.
                  </Text>
                )}
              </Card>
            }
          />
        </Tabs.Panel>

        <Tabs.Panel value="payroll" pt="md">
          <Stack>
            {salarySummary && (
              <>
                <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="md">
                  <Card shadow="sm" padding="md" withBorder className="data-table-card">
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                      Всего начислено
                    </Text>
                    <Text size="xl" fw={700} mt="xs">
                      {salarySummary.total.toFixed(2)} ₽
                    </Text>
                  </Card>
                  <Card shadow="sm" padding="md" withBorder>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                      Операций
                    </Text>
                    <Text size="xl" fw={700} mt="xs">
                      {salarySummary.count}
                    </Text>
                  </Card>
                  <Card shadow="sm" padding="md" withBorder>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                      Среднее начисление
                    </Text>
                    <Text size="xl" fw={700} mt="xs">
                      {salarySummary.avg.toFixed(2)} ₽
                    </Text>
                  </Card>
                </SimpleGrid>
                {payrollByDoctor.length > 0 && (
                  <Card shadow="sm" padding="md" withBorder>
                    <Text size="sm" fw={500} mb="sm">
                      Начисления по врачам (агрегат)
                    </Text>
                    <Table withRowBorders highlightOnHover verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>Врач (ID)</Table.Th>
                          <Table.Th>Начислено</Table.Th>
                          <Table.Th>Операций</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {payrollByDoctor.map((row) => (
                          <Table.Tr key={row.doctorId}>
                            <Table.Td>{row.doctorId.slice(0, 8)}…</Table.Td>
                            <Table.Td>{row.total.toFixed(2)} ₽</Table.Td>
                            <Table.Td>{row.count}</Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  </Card>
                )}
              </>
            )}
            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Text size="sm" fw={500} mb="sm">
                Политики расчёта зарплаты
              </Text>
              {payrollPolicies && payrollPolicies.length === 0 && (
                <Text size="sm" c="dimmed">
                  Политики ЗП ещё не настроены.
                </Text>
              )}
              {payrollPolicies && payrollPolicies.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Доктор</Table.Th>
                      <Table.Th>Роль</Table.Th>
                      <Table.Th>Фикс за смену</Table.Th>
                      <Table.Th>% от услуг</Table.Th>
                      <Table.Th>% от товаров</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {payrollPolicies.map((p) => (
                      <Table.Tr key={p.id}>
                        <Table.Td>{p.doctor_id ?? "по роли"}</Table.Td>
                        <Table.Td>{p.role ?? "-"}</Table.Td>
                        <Table.Td>{p.fixed_per_shift}</Table.Td>
                        <Table.Td>{p.percent_from_services}</Table.Td>
                        <Table.Td>{p.percent_from_products}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>
            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Group justify="space-between" mb="sm">
                <Text size="sm" fw={500}>
                  Начисления по врачам
                </Text>
                <Select
                  placeholder="Выберите доктора"
                  data={doctorOptions}
                  value={selectedDoctorId}
                  onChange={setSelectedDoctorId}
                  clearable
                  searchable
                />
              </Group>
              {salaryTxs && salaryTxs.length === 0 && (
                <Text size="sm" c="dimmed">
                  Нет начислений по выбранному врачу.
                </Text>
              )}
              {salaryTxs && salaryTxs.length > 0 && (
                <>
                  <Table withRowBorders highlightOnHover verticalSpacing="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>Дата</Table.Th>
                        <Table.Th>Сумма</Table.Th>
                        <Table.Th>Тип</Table.Th>
                        <Table.Th>Период</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {salaryTxs.map((t) => (
                        <Table.Tr key={t.id}>
                          <Table.Td>{dayjs(t.created_at).format("DD.MM.YYYY")}</Table.Td>
                          <Table.Td>{t.amount}</Table.Td>
                          <Table.Td>{t.type}</Table.Td>
                          <Table.Td>
                            {t.period_start && t.period_end
                              ? `${t.period_start} — ${t.period_end}`
                              : "-"}
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                  {salarySummary && (
                    <Stack gap={4} mt="sm">
                      <Text size="sm">
                        Всего начислений: <strong>{salarySummary.count}</strong>
                      </Text>
                      <Text size="sm">
                        Суммарно: <strong>{salarySummary.total.toFixed(2)} ₽</strong>
                      </Text>
                      <Text size="sm">
                        Среднее начисление:{" "}
                        <strong>{salarySummary.avg.toFixed(2)} ₽</strong>
                      </Text>
                    </Stack>
                  )}
                </>
              )}
            </Card>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="inventory" pt="md">
          <Stack>
            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Text size="sm" fw={500} mb="sm">
                Товары и материалы
              </Text>
              {products && products.length === 0 && (
                <Text size="sm" c="dimmed">
                  Склад ещё не настроен. Добавьте продукты через админку или API.
                </Text>
              )}
              {products && products.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Название</Table.Th>
                      <Table.Th>SKU</Table.Th>
                      <Table.Th>Ед.</Table.Th>
                      <Table.Th>Активен</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {products.map((p) => (
                      <Table.Tr
                        key={p.id}
                        className="data-table-clickable-row"
                        onClick={() => setSelectedProductId(p.id)}
                      >
                        <Table.Td>{p.name}</Table.Td>
                        <Table.Td>{p.sku ?? "-"}</Table.Td>
                        <Table.Td>{p.unit}</Table.Td>
                        <Table.Td>{p.is_active ? "Да" : "Нет"}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>

            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Text size="sm" fw={500} mb="sm">
                Склады
              </Text>
              {warehouses && warehouses.length === 0 && (
                <Text size="sm" c="dimmed">
                  Складские площадки ещё не созданы.
                </Text>
              )}
              {warehouses && warehouses.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Название</Table.Th>
                      <Table.Th>По умолчанию</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {warehouses.map((w) => (
                      <Table.Tr
                        key={w.id}
                        className="data-table-clickable-row"
                        onClick={() => setSelectedWarehouseId(w.id)}
                      >
                        <Table.Td>{w.name}</Table.Td>
                        <Table.Td>{w.is_default ? "Да" : "Нет"}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>

            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Group justify="space-between" mb="sm">
                <Text size="sm" fw={500}>
                  История движений по складу
                </Text>
                <Text size="xs" c="dimmed">
                  Фильтруется по выбранному товару, складу и периоду.
                </Text>
              </Group>
              <Group mb="md" gap="sm">
                <TextInput
                  type="date"
                  label="Дата с"
                  value={invDateFrom ?? ""}
                  onChange={(e) => setInvDateFrom(e.target.value || null)}
                  size="xs"
                />
                <TextInput
                  type="date"
                  label="Дата по"
                  value={invDateTo ?? ""}
                  onChange={(e) => setInvDateTo(e.target.value || null)}
                  size="xs"
                />
              </Group>
              {(!inventoryTxs || inventoryTxs.length === 0) && (
                <Text size="sm" c="dimmed">
                  Нет движений по выбранным фильтрам.
                </Text>
              )}
              {inventoryTxs && inventoryTxs.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>Дата</Table.Th>
                      <Table.Th>Тип</Table.Th>
                      <Table.Th>Количество</Table.Th>
                      <Table.Th>Описание</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {inventoryTxs.map((t) => (
                      <Table.Tr key={t.id}>
                        <Table.Td>
                          {dayjs(t.happened_at).format("DD.MM.YYYY HH:mm")}
                        </Table.Td>
                        <Table.Td>{t.type}</Table.Td>
                        <Table.Td>{t.quantity}</Table.Td>
                        <Table.Td>{t.description ?? "-"}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>

            {inventoryStock && (
              <Card shadow="sm" padding="md" withBorder className="data-toolbar-card">
                <Text size="sm" fw={500} mb="xs">
                  Текущий остаток по выбранной паре товар/склад
                </Text>
                <Text size="sm">
                  Остаток:{" "}
                  <strong>
                    {inventoryStock.quantity} {inventoryStock.unit}
                  </strong>
                </Text>
              </Card>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>

      <AdminDrawer
        position="right"
        size="md"
        opened={txDrawerOpen}
        onClose={() => setTxDrawerOpen(false)}
        title={
          txDrawerMode === "income"
            ? "Внести в кассу"
            : txDrawerMode === "expense"
              ? "Изъять из кассы"
              : "Перевод между кассами"
        }
      >
        <Stack gap="sm">
          {txDrawerMode === "transfer" && (
            <>
              <Select
                label="Из кассы"
                placeholder="Выберите кассу"
                data={cashboxOptions}
                value={txFromCashboxId}
                onChange={setTxFromCashboxId}
                required
              />
              <Select
                label="В кассу"
                placeholder="Выберите кассу"
                data={cashboxOptions.filter((o) => o.value !== txFromCashboxId)}
                value={txToCashboxId}
                onChange={setTxToCashboxId}
                required
              />
            </>
          )}
          {txDrawerMode !== "transfer" && txDrawerCashboxId && (
            <Text size="sm" c="dimmed">
              Касса: {cashboxes?.find((c) => c.id === txDrawerCashboxId)?.name ?? txDrawerCashboxId}
            </Text>
          )}
          <NumberInput
            label="Сумма"
            value={txAmount}
            onChange={(v) => setTxAmount(String(v ?? ""))}
            min={0.01}
            decimalScale={2}
            required
          />
          <TextInput
            label="Назначение / категория"
            placeholder="Например: Оплата услуги, Изъятие наличных"
            value={txCategory}
            onChange={(e) => setTxCategory(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setTxDrawerOpen(false)}>
              Отмена
            </Button>
            <Button
              disabled={
                !Number(txAmount) ||
                !txCategory?.trim() ||
                (txDrawerMode === "transfer"
                  ? !txFromCashboxId || !txToCashboxId || txFromCashboxId === txToCashboxId
                  : !txDrawerCashboxId)
              }
              loading={createTx.isPending}
              onClick={() => {
                if (txDrawerMode === "transfer") {
                  createTx.mutate(
                    {
                      type: "transfer",
                      amount: txAmount,
                      category: txCategory || "Перевод",
                      from_cashbox_id: txFromCashboxId!,
                      to_cashbox_id: txToCashboxId!,
                    },
                    {
                      onSuccess: () => {
                        setTxDrawerOpen(false);
                        setTxAmount("");
                        setTxCategory("");
                        setTxFromCashboxId(null);
                        setTxToCashboxId(null);
                      },
                    }
                  );
                } else {
                  createTx.mutate(
                    {
                      type: txDrawerMode!,
                      amount: txAmount,
                      category: txCategory || undefined,
                      cashbox_id: txDrawerCashboxId!,
                    },
                    {
                      onSuccess: () => {
                        setTxDrawerOpen(false);
                        setTxAmount("");
                        setTxCategory("");
                        setTxDrawerCashboxId(null);
                        setTxDrawerMode(null);
                      },
                    }
                  );
                }
              }}
            >
              Создать
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>
    </Stack>
  );
}

