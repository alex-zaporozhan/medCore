import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useCashboxes,
  useDoctors,
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
import { ThreeColumnLayout } from "@/components/layout/ThreeColumnLayout";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { moneyCashboxTypeLabel, moneyFinanceTxSourceLabel, moneyFinanceTxTypeLabel, moneyInventoryTxTypeLabel, moneySalaryTxTypeLabel } from "@/shared/moneyI18n";

type TxDrawerMode = "income" | "expense" | "transfer" | null;

export default function AdminFinancePage() {
  const { t, i18n } = useTranslation("money");
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

  const { data: doctors, isLoading: doctorsLoading } = useDoctors({
    clinic_id: clinicId ?? undefined,
    is_active: true,
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
    doctorsLoading ||
    payrollLoading ||
    salaryLoading ||
    productsLoading ||
    warehousesLoading ||
    inventoryTxsLoading ||
    inventoryStockLoading;

  const cashboxOptions =
    cashboxes?.map((c) => ({
      value: c.id,
      label: `${c.name} (${moneyCashboxTypeLabel(c.type)})${c.is_default ? t("finance.defaultSuffix") : ""}`,
    })) ?? [];

  const doctorNameById = useMemo(() => {
    const m = new Map<string, string>();
    doctors?.forEach((d) => {
      m.set(d.id, d.full_name?.trim() || d.specialization?.trim() || d.id);
    });
    return m;
  }, [doctors]);

  const doctorOptions = useMemo(
    () =>
      doctors?.map((d) => ({
        value: d.id,
        label: d.full_name?.trim() || d.specialization?.trim() || d.id.slice(0, 8) + "…",
      })) ?? [],
    [doctors]
  );

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
        <ContextBar title={t("finance.titleShort")} />
        <Text size="sm" c="dimmed">
          {t("finance.pickClinic")}
        </Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title={t("finance.title")} />

      {loading && <PageSkeleton variant="table" rows={6} />}

      <Tabs defaultValue="cashboxes" keepMounted={false}>
        <Tabs.List>
          <Tabs.Tab value="cashboxes">{t("finance.tabCashboxes")}</Tabs.Tab>
          <Tabs.Tab value="transactions">{t("finance.tabTransactions")}</Tabs.Tab>
          <Tabs.Tab value="payroll">{t("finance.tabPayroll")}</Tabs.Tab>
          <Tabs.Tab value="inventory">{t("finance.tabInventory")}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="cashboxes" pt="md">
          <Card shadow="sm" padding="md" withBorder className="data-table-card">
            <Text size="sm" fw={500} mb="sm">
              {t("finance.cashboxesTitle")}
            </Text>
            {cashboxes && cashboxes.length === 0 && (
              <EmptyState
                title={t("finance.emptyCashboxesTitle")}
                description={t("finance.emptyCashboxesHint")}
              />
            )}
            {cashboxes && cashboxes.length > 0 && (
              <Table withRowBorders highlightOnHover verticalSpacing="sm">
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("finance.colName")}</Table.Th>
                    <Table.Th>{t("finance.colBalance")}</Table.Th>
                    <Table.Th>{t("type")}</Table.Th>
                    <Table.Th>{t("finance.colCurrency")}</Table.Th>
                    <Table.Th>{t("finance.colDefault")}</Table.Th>
                    <Table.Th>{t("finance.colActive")}</Table.Th>
                    <Table.Th w={50}></Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {cashboxes.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td>{c.name}</Table.Td>
                      <Table.Td>
                        {c.balance != null
                          ? `${Number(c.balance).toLocaleString(i18n.language.startsWith("ru") ? "ru-RU" : "en-US")} ${c.currency}`
                          : "—"}
                      </Table.Td>
                      <Table.Td>{moneyCashboxTypeLabel(c.type)}</Table.Td>
                      <Table.Td>{c.currency}</Table.Td>
                      <Table.Td>{c.is_default ? t("yes") : t("no")}</Table.Td>
                      <Table.Td>{c.is_active ? t("yes") : t("no")}</Table.Td>
                      <Table.Td>
                        <Menu position="bottom-end">
                          <Menu.Target>
                            <ActionIcon variant="subtle" size="sm" aria-label={t("actions")}>
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
                              {t("finance.deposit")}
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
                              {t("finance.withdraw")}
                            </Menu.Item>
                            <Menu.Item
                              leftSection={<IconTransfer size={14} />}
                              onClick={() => {
                                setTxDrawerMode("transfer");
                                setTxDrawerCashboxId(null);
                                setTxFromCashboxId(c.id);
                                setTxToCashboxId(null);
                                setTxAmount("");
                                setTxCategory(t("finance.categoryTransfer"));
                                setTxDrawerOpen(true);
                              }}
                            >
                              {t("finance.transfer")}
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
                {t("finance.unearnedTitle")}
              </Text>
              <Text size="lg" fw={600}>
                {liability.unearned_revenue} ₽
              </Text>
              <Text size="xs" c="dimmed">
                {t("finance.activePasses", { count: liability.active_subscriptions_count })}
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
                  {t("finance.txFilters")}
                </Text>
                <Select
                  label={t("finance.cashbox")}
                  placeholder={t("finance.allCashboxes")}
                  data={cashboxOptions}
                  value={selectedCashboxId}
                  onChange={setSelectedCashboxId}
                  clearable
                />
                <Text size="xs" c="dimmed">
                  {t("finance.period")}{" "}
                  {txDateFrom && txDateTo
                    ? `${dayjs(txDateFrom).format("DD.MM.YYYY")} — ${dayjs(txDateTo).format(
                        "DD.MM.YYYY",
                      )}`
                    : t("finance.periodDefaultWeek")}
                </Text>
              </Stack>
            }
            center={
              <Card shadow="sm" padding="md" withBorder className="data-table-card">
                <Text size="sm" fw={500} mb="sm">
                  {t("finance.txTitle")}
                </Text>
                {txs && txs.length === 0 && (
                  <Text size="sm" c="dimmed">
                    {t("finance.emptyTx")}
                  </Text>
                )}
                {txs && txs.length > 0 && (
                  <Table withRowBorders highlightOnHover verticalSpacing="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>{t("date")}</Table.Th>
                        <Table.Th>{t("type")}</Table.Th>
                        <Table.Th>{t("amount")}</Table.Th>
                        <Table.Th>{t("finance.colSource")}</Table.Th>
                        <Table.Th>{t("finance.colBooking")}</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {txs.map((tx) => (
                        <Table.Tr key={tx.id}>
                          <Table.Td>{dayjs(tx.happened_at).format("DD.MM.YYYY HH:mm")}</Table.Td>
                          <Table.Td>{moneyFinanceTxTypeLabel(tx.type)}</Table.Td>
                          <Table.Td>
                            {tx.amount} {tx.currency}
                          </Table.Td>
                          <Table.Td>{moneyFinanceTxSourceLabel(tx.source)}</Table.Td>
                          <Table.Td>
                            {tx.booking_id ? (
                              <Anchor size="xs" c="blue">
                                {tx.booking_id.slice(0, 8)}…
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
                  {t("finance.txTotals")}
                </Text>
                <Text size="xs" c="dimmed" mb="sm">
                  {t("finance.txTotalsHint")}
                </Text>
                {txs && txs.length > 0 ? (
                  <Stack gap={4}>
                    <Text size="sm">
                      {t("finance.txOpsCount", { count: txs.length })}
                    </Text>
                  </Stack>
                ) : (
                  <Text size="xs" c="dimmed">
                    {t("finance.txNoTotals")}
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
                      {t("finance.accruedTotal")}
                    </Text>
                    <Text size="xl" fw={700} mt="xs">
                      {salarySummary.total.toFixed(2)} ₽
                    </Text>
                  </Card>
                  <Card shadow="sm" padding="md" withBorder>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                      {t("finance.ops")}
                    </Text>
                    <Text size="xl" fw={700} mt="xs">
                      {salarySummary.count}
                    </Text>
                  </Card>
                  <Card shadow="sm" padding="md" withBorder>
                    <Text size="xs" c="dimmed" tt="uppercase" fw={600}>
                      {t("finance.avgAccrual")}
                    </Text>
                    <Text size="xl" fw={700} mt="xs">
                      {salarySummary.avg.toFixed(2)} ₽
                    </Text>
                  </Card>
                </SimpleGrid>
                {payrollByDoctor.length > 0 && (
                  <Card shadow="sm" padding="md" withBorder>
                    <Text size="sm" fw={500} mb="sm">
                      {t("finance.payrollByDoctor")}
                    </Text>
                    <Table withRowBorders highlightOnHover verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>{t("finance.colDoctor")}</Table.Th>
                          <Table.Th>{t("finance.colAccrued")}</Table.Th>
                          <Table.Th>{t("finance.ops")}</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {payrollByDoctor.map((row) => (
                          <Table.Tr key={row.doctorId}>
                            <Table.Td>
                              {doctorNameById.get(row.doctorId) ?? `${row.doctorId.slice(0, 8)}…`}
                            </Table.Td>
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
                {t("finance.payrollPolicies")}
              </Text>
              {payrollPolicies && payrollPolicies.length === 0 && (
                <Text size="sm" c="dimmed">
                  {t("finance.emptyPayrollPolicies")}
                </Text>
              )}
              {payrollPolicies && payrollPolicies.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>{t("finance.colDoctor")}</Table.Th>
                      <Table.Th>{t("finance.colRole")}</Table.Th>
                      <Table.Th>{t("finance.colFixedShift")}</Table.Th>
                      <Table.Th>{t("finance.colPctServices")}</Table.Th>
                      <Table.Th>{t("finance.colPctGoods")}</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {payrollPolicies.map((p) => (
                      <Table.Tr key={p.id}>
                        <Table.Td>{p.doctor_id ?? t("finance.byRole")}</Table.Td>
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
                  {t("finance.salaryByDoctors")}
                </Text>
                <Select
                  placeholder={t("finance.allDoctors")}
                  data={doctorOptions}
                  value={selectedDoctorId}
                  onChange={setSelectedDoctorId}
                  clearable
                  searchable
                  nothingFoundMessage={
                    doctors && doctors.length === 0
                      ? t("finance.noActiveDoctors")
                      : t("finance.notFound")
                  }
                />
              </Group>
              {salaryTxs && salaryTxs.length === 0 && (
                <Text size="sm" c="dimmed">
                  {selectedDoctorId
                    ? t("finance.emptySalaryDoctor")
                    : t("finance.emptySalary")}
                </Text>
              )}
              {salaryTxs && salaryTxs.length > 0 && (
                <>
                  <Table withRowBorders highlightOnHover verticalSpacing="sm">
                    <Table.Thead>
                      <Table.Tr>
                        <Table.Th>{t("date")}</Table.Th>
                        <Table.Th>{t("amount")}</Table.Th>
                        <Table.Th>{t("type")}</Table.Th>
                        <Table.Th>{t("finance.colPeriod")}</Table.Th>
                      </Table.Tr>
                    </Table.Thead>
                    <Table.Tbody>
                      {salaryTxs.map((tx) => (
                        <Table.Tr key={tx.id}>
                          <Table.Td>{dayjs(tx.created_at).format("DD.MM.YYYY")}</Table.Td>
                          <Table.Td>{tx.amount}</Table.Td>
                          <Table.Td>{moneySalaryTxTypeLabel(tx.type)}</Table.Td>
                          <Table.Td>
                            {tx.period_start && tx.period_end
                              ? `${tx.period_start} — ${tx.period_end}`
                              : "-"}
                          </Table.Td>
                        </Table.Tr>
                      ))}
                    </Table.Tbody>
                  </Table>
                  {salarySummary && (
                    <Stack gap={4} mt="sm">
                      <Text size="sm">
                        {t("finance.salaryCount", { count: salarySummary.count })}
                      </Text>
                      <Text size="sm">
                        {t("finance.salarySum", { amount: salarySummary.total.toFixed(2) })}
                      </Text>
                      <Text size="sm">
                        {t("finance.salaryAvg", { amount: salarySummary.avg.toFixed(2) })}
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
                {t("finance.productsTitle")}
              </Text>
              {products && products.length === 0 && (
                <Text size="sm" c="dimmed">
                  {t("finance.emptyProducts")}
                </Text>
              )}
              {products && products.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>{t("finance.colName")}</Table.Th>
                      <Table.Th>{t("finance.sku")}</Table.Th>
                      <Table.Th>{t("finance.colUnit")}</Table.Th>
                      <Table.Th>{t("active")}</Table.Th>
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
                        <Table.Td>{p.is_active ? t("yes") : t("no")}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>

            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Text size="sm" fw={500} mb="sm">
                {t("finance.warehousesTitle")}
              </Text>
              {warehouses && warehouses.length === 0 && (
                <Text size="sm" c="dimmed">
                  {t("finance.emptyWarehouses")}
                </Text>
              )}
              {warehouses && warehouses.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>{t("finance.colName")}</Table.Th>
                      <Table.Th>{t("finance.colDefault")}</Table.Th>
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
                        <Table.Td>{w.is_default ? t("yes") : t("no")}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>

            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Group justify="space-between" mb="sm">
                <Text size="sm" fw={500}>
                  {t("finance.invHistory")}
                </Text>
                <Text size="xs" c="dimmed">
                  {t("finance.invHistoryHint")}
                </Text>
              </Group>
              <Group mb="md" gap="sm">
                <TextInput
                  type="date"
                  label={t("finance.dateFrom")}
                  value={invDateFrom ?? ""}
                  onChange={(e) => setInvDateFrom(e.target.value || null)}
                  size="xs"
                />
                <TextInput
                  type="date"
                  label={t("finance.dateTo")}
                  value={invDateTo ?? ""}
                  onChange={(e) => setInvDateTo(e.target.value || null)}
                  size="xs"
                />
              </Group>
              {(!inventoryTxs || inventoryTxs.length === 0) && (
                <Text size="sm" c="dimmed">
                  {t("finance.emptyInvTx")}
                </Text>
              )}
              {inventoryTxs && inventoryTxs.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
                  <Table.Thead>
                    <Table.Tr>
                      <Table.Th>{t("date")}</Table.Th>
                      <Table.Th>{t("type")}</Table.Th>
                      <Table.Th>{t("finance.colQty")}</Table.Th>
                      <Table.Th>{t("finance.colDescription")}</Table.Th>
                    </Table.Tr>
                  </Table.Thead>
                  <Table.Tbody>
                    {inventoryTxs.map((tx) => (
                      <Table.Tr key={tx.id}>
                        <Table.Td>{dayjs(tx.happened_at).format("DD.MM.YYYY HH:mm")}</Table.Td>
                        <Table.Td>{moneyInventoryTxTypeLabel(tx.type)}</Table.Td>
                        <Table.Td>{tx.quantity}</Table.Td>
                        <Table.Td>{tx.description ?? "-"}</Table.Td>
                      </Table.Tr>
                    ))}
                  </Table.Tbody>
                </Table>
              )}
            </Card>

            {inventoryStock && (
              <Card shadow="sm" padding="md" withBorder className="data-toolbar-card">
                <Text size="sm" fw={500} mb="xs">
                  {t("finance.stockPair")}
                </Text>
                <Text size="sm">
                  {t("finance.stock")}{" "}
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
            ? t("finance.drawerDeposit")
            : txDrawerMode === "expense"
              ? t("finance.drawerWithdraw")
              : t("finance.drawerTransfer")
        }
      >
        <Stack gap="sm">
          {txDrawerMode === "transfer" && (
            <>
              <Select
                label={t("finance.fromCashbox")}
                placeholder={t("finance.pickCashbox")}
                data={cashboxOptions}
                value={txFromCashboxId}
                onChange={setTxFromCashboxId}
                required
              />
              <Select
                label={t("finance.toCashbox")}
                placeholder={t("finance.pickCashbox")}
                data={cashboxOptions.filter((o) => o.value !== txFromCashboxId)}
                value={txToCashboxId}
                onChange={setTxToCashboxId}
                required
              />
            </>
          )}
          {txDrawerMode !== "transfer" && txDrawerCashboxId && (
            <Text size="sm" c="dimmed">
              {t("finance.cashboxLabel", { name: cashboxes?.find((c) => c.id === txDrawerCashboxId)?.name ?? txDrawerCashboxId })}
            </Text>
          )}
          <NumberInput
            label={t("amount")}
            value={txAmount}
            onChange={(v) => setTxAmount(String(v ?? ""))}
            min={0.01}
            decimalScale={2}
            required
          />
          <TextInput
            label={t("finance.category")}
            placeholder={t("finance.categoryPlaceholder")}
            value={txCategory}
            onChange={(e) => setTxCategory(e.currentTarget.value)}
            required
          />
          <Group justify="flex-end">
            <Button variant="subtle" onClick={() => setTxDrawerOpen(false)}>
              {t("cancel")}
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
                      category: txCategory || t("finance.categoryTransfer"),
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
              {t("create")}
            </Button>
          </Group>
        </Stack>
      </AdminDrawer>
    </Stack>
  );
}

