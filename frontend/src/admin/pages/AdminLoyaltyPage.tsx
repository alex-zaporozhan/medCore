import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import {
  useLoyaltyPackages,
  useCustomerSubscriptions,
  useWallets,
  useWalletTransactions,
  useLoyaltyCampaignSettings,
  useUpdateLoyaltyCampaignSettings,
  useRunLoyaltyCampaigns,
} from "@/hooks";
import type { LoyaltyCampaignSettings } from "@/api/types";
import {
  Button,
  Card,
  Group,
  NumberInput,
  Stack,
  Switch,
  Table,
  Tabs,
  Text,
  TextInput,
} from "@mantine/core";
import { ContextBar, PageSkeleton, QueryErrorAlert } from "@/shared/ui";
import { isBoxEdition } from "@/config/edition";

export default function AdminLoyaltyPage() {
  const { currentClinicId } = useAdminClinic();
  const clinicId = currentClinicId ?? null;
  const [searchParams, setSearchParams] = useSearchParams();
  const isBox = isBoxEdition();
  const mainTab =
    !isBox && searchParams.get("tab") === "loyalty" ? "loyalty" : "subscriptions";
  const initialPatientId = searchParams.get("patient_id") ?? "";
  const [patientIdFilter, setPatientIdFilter] = useState<string>(initialPatientId);
  const [selectedWalletId, setSelectedWalletId] = useState<string | null>(null);

  const { data: packages, isLoading: packagesLoading } = useLoyaltyPackages();
  const packageNameById = useMemo(() => {
    if (!packages?.length) return {} as Record<string, string>;
    const m: Record<string, string> = {};
    for (const p of packages) {
      m[p.id] = p.name?.trim() ? p.name : (p.code ?? p.id);
    }
    return m;
  }, [packages]);
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

  const { data: campaignSettings, isLoading: campaignSettingsLoading } =
    useLoyaltyCampaignSettings(clinicId);
  const updateCampaignSettings = useUpdateLoyaltyCampaignSettings();
  const runCampaigns = useRunLoyaltyCampaigns();
  const [campaignDraft, setCampaignDraft] = useState<LoyaltyCampaignSettings | null>(
    null,
  );
  useEffect(() => {
    if (campaignSettings) setCampaignDraft(campaignSettings);
  }, [campaignSettings]);

  useEffect(() => {
    if (isBox && searchParams.get("tab") === "loyalty") {
      const next = new URLSearchParams(searchParams);
      next.set("tab", "subscriptions");
      setSearchParams(next, { replace: true });
    }
  }, [isBox, searchParams, setSearchParams]);

  const loading =
    packagesLoading || subsLoading || walletsLoading || walletTxsLoading;

  if (!clinicId) {
    return (
      <Stack>
        <ContextBar title="Абонементы и лояльность" />
        <Text size="sm" c="dimmed">
          Выберите клинику в шапке, чтобы работать с программами лояльности.
        </Text>
      </Stack>
    );
  }

  return (
    <Stack>
      <ContextBar title="Абонементы и лояльность" />

      {loading && <PageSkeleton variant="table" rows={4} />}

      <Tabs
        value={mainTab}
        onChange={(v) => {
          if (!v) return;
          const next = new URLSearchParams(searchParams);
          next.set("tab", v);
          setSearchParams(next);
        }}
        keepMounted={false}
      >
        <Tabs.List>
          <Tabs.Tab value="subscriptions">Абонементы</Tabs.Tab>
          {!isBox ? <Tabs.Tab value="loyalty">Лояльность</Tabs.Tab> : null}
        </Tabs.List>

        <Tabs.Panel value="subscriptions" pt="md">
          <Tabs defaultValue="packages" keepMounted={false}>
            <Tabs.List>
              <Tabs.Tab value="packages">Пакеты</Tabs.Tab>
              <Tabs.Tab value="subscriptions">Абонементы пациента</Tabs.Tab>
            </Tabs.List>

        <Tabs.Panel value="packages" pt="md">
          <Card shadow="sm" padding="md" withBorder className="data-table-card">
            <Text size="sm" fw={500} mb="sm">
              Пакеты абонементов
            </Text>
            {packages && packages.length === 0 && (
              <Text size="sm" c="dimmed">
                Пакеты ещё не созданы. Добавьте их через админку или API.
              </Text>
            )}
            {packages && packages.length > 0 && (
              <Table withRowBorders highlightOnHover verticalSpacing="sm">
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
            <Card withBorder p="sm" className="data-toolbar-card">
              <TextInput
                label="ID пациента"
                placeholder="Вставьте UUID пациента для поиска его абонементов"
                value={patientIdFilter}
                onChange={(e) => setPatientIdFilter(e.currentTarget.value)}
              />
            </Card>
            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Text size="sm" fw={500} mb="sm">
                Абонементы пациента
              </Text>
              {subs && subs.length === 0 && (
                <Text size="sm" c="dimmed">
                  Для указанного пациента нет абонементов.
                </Text>
              )}
              {subs && subs.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
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
                        <Table.Td>
                          {packageNameById[s.subscription_package_id] ??
                            `${s.subscription_package_id.slice(0, 8)}…`}
                        </Table.Td>
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

        </Tabs>
        </Tabs.Panel>

        {!isBox ? (
        <Tabs.Panel value="loyalty" pt="md">
          <Tabs defaultValue="wallets" keepMounted={false}>
            <Tabs.List>
              <Tabs.Tab value="wallets">Кошельки</Tabs.Tab>
              <Tabs.Tab value="campaigns">Кампании</Tabs.Tab>
            </Tabs.List>

        <Tabs.Panel value="wallets" pt="md">
          <Stack>
            <Card withBorder p="sm" className="data-toolbar-card">
              <TextInput
                label="ID пациента"
                placeholder="Вставьте UUID пациента для поиска кошелька"
                value={patientIdFilter}
                onChange={(e) => setPatientIdFilter(e.currentTarget.value)}
              />
            </Card>
            <Card shadow="sm" padding="md" withBorder className="data-table-card">
              <Text size="sm" fw={500} mb="sm">
                Кошелёк пациента
              </Text>
              {wallets && wallets.length === 0 && (
                <Text size="sm" c="dimmed">
                  Кошелёк для указанного пациента ещё не создан.
                </Text>
              )}
              {wallets && wallets.length > 0 && (
                <Table withRowBorders highlightOnHover verticalSpacing="sm">
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
                        className="data-table-clickable-row"
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
              <Card shadow="sm" padding="md" withBorder className="data-table-card">
                <Text size="sm" fw={500} mb="sm">
                  Движения по кошельку
                </Text>
                {walletTxs && walletTxs.length === 0 && (
                  <Text size="sm" c="dimmed">
                    Для выбранного кошелька пока нет транзакций.
                  </Text>
                )}
                {walletTxs && walletTxs.length > 0 && (
                  <Table withRowBorders highlightOnHover verticalSpacing="sm">
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

        <Tabs.Panel value="campaigns" pt="md">
          <Card shadow="sm" padding="md" withBorder>
            <Text size="sm" fw={500} mb="xs">
              Автокампании лояльности (задачи для операторов)
            </Text>
            <Text size="sm" c="dimmed" mb="md">
              Задачи с типами LOYALTY_* не создаются при отключённых уведомлениях у пациента
              или без согласия на рассылку (для реактивации). Учитесь дневные и месячные лимиты.
            </Text>
            {!campaignDraft && campaignSettingsLoading && (
              <Text size="sm" c="dimmed">
                Загрузка…
              </Text>
            )}
            {campaignDraft && (
              <Stack gap="md">
                <Switch
                  label="Истекающие пакеты"
                  checked={campaignDraft.expiring_packages_enabled}
                  onChange={(e) =>
                    setCampaignDraft({
                      ...campaignDraft,
                      expiring_packages_enabled: e.currentTarget.checked,
                    })
                  }
                />
                <Switch
                  label="Высокий баланс + низкая активность"
                  checked={campaignDraft.high_balance_low_activity_enabled}
                  onChange={(e) =>
                    setCampaignDraft({
                      ...campaignDraft,
                      high_balance_low_activity_enabled: e.currentTarget.checked,
                    })
                  }
                />
                <Switch
                  label="Реактивация (не было визита давно)"
                  checked={campaignDraft.reengagement_enabled}
                  onChange={(e) =>
                    setCampaignDraft({
                      ...campaignDraft,
                      reengagement_enabled: e.currentTarget.checked,
                    })
                  }
                />
                <Switch
                  label="Создавать задачи (канал Tasks)"
                  checked={campaignDraft.channel_tasks_enabled}
                  onChange={(e) =>
                    setCampaignDraft({
                      ...campaignDraft,
                      channel_tasks_enabled: e.currentTarget.checked,
                    })
                  }
                />
                <Switch
                  label="Не дублировать с SMS по истекающим (если уже отправлено сегодня)"
                  checked={campaignDraft.skip_expiring_task_if_sms_expiring_sent_today}
                  onChange={(e) =>
                    setCampaignDraft({
                      ...campaignDraft,
                      skip_expiring_task_if_sms_expiring_sent_today:
                        e.currentTarget.checked,
                    })
                  }
                />
                <Group grow>
                  <NumberInput
                    label="Макс. касаний клиники / день"
                    min={1}
                    max={10000}
                    value={campaignDraft.max_contacts_per_day_clinic}
                    onChange={(v) =>
                      setCampaignDraft({
                        ...campaignDraft,
                        max_contacts_per_day_clinic: typeof v === "number" ? v : 50,
                      })
                    }
                  />
                  <NumberInput
                    label="Макс. касаний пациента / день"
                    min={1}
                    max={100}
                    value={campaignDraft.max_contacts_per_day_patient}
                    onChange={(v) =>
                      setCampaignDraft({
                        ...campaignDraft,
                        max_contacts_per_day_patient: typeof v === "number" ? v : 3,
                      })
                    }
                  />
                </Group>
                <Group grow>
                  <NumberInput
                    label="Макс. задач LOYALTY_* на пациента / месяц (UTC)"
                    min={1}
                    max={100}
                    value={campaignDraft.max_campaign_touches_per_patient_month}
                    onChange={(v) =>
                      setCampaignDraft({
                        ...campaignDraft,
                        max_campaign_touches_per_patient_month:
                          typeof v === "number" ? v : 12,
                      })
                    }
                  />
                  <NumberInput
                    label="Cooldown между однотипными кампаниями, дни"
                    min={1}
                    max={365}
                    value={campaignDraft.campaign_cooldown_days}
                    onChange={(v) =>
                      setCampaignDraft({
                        ...campaignDraft,
                        campaign_cooldown_days: typeof v === "number" ? v : 14,
                      })
                    }
                  />
                </Group>
                <NumberInput
                  label="Дней без визита для реактивации"
                  min={30}
                  max={730}
                  value={campaignDraft.reengagement_inactive_days}
                  onChange={(v) =>
                    setCampaignDraft({
                      ...campaignDraft,
                      reengagement_inactive_days: typeof v === "number" ? v : 180,
                    })
                  }
                />
                <Group>
                  <Button
                    loading={updateCampaignSettings.isPending}
                    onClick={() =>
                      updateCampaignSettings.mutate({
                        expiring_packages_enabled:
                          campaignDraft.expiring_packages_enabled,
                        high_balance_low_activity_enabled:
                          campaignDraft.high_balance_low_activity_enabled,
                        reengagement_enabled: campaignDraft.reengagement_enabled,
                        channel_tasks_enabled: campaignDraft.channel_tasks_enabled,
                        channel_omnichannel_enabled:
                          campaignDraft.channel_omnichannel_enabled,
                        skip_expiring_task_if_sms_expiring_sent_today:
                          campaignDraft.skip_expiring_task_if_sms_expiring_sent_today,
                        max_contacts_per_day_clinic:
                          campaignDraft.max_contacts_per_day_clinic,
                        max_contacts_per_day_patient:
                          campaignDraft.max_contacts_per_day_patient,
                        max_campaign_touches_per_patient_month:
                          campaignDraft.max_campaign_touches_per_patient_month,
                        campaign_cooldown_days: campaignDraft.campaign_cooldown_days,
                        reengagement_inactive_days:
                          campaignDraft.reengagement_inactive_days,
                      })
                    }
                  >
                    Сохранить настройки
                  </Button>
                  <Button
                    variant="light"
                    loading={runCampaigns.isPending}
                    onClick={() => runCampaigns.mutate()}
                  >
                    Запустить кампании сейчас
                  </Button>
                </Group>
                {runCampaigns.data && (
                  <Text size="sm">
                    Последний запуск: expiring {runCampaigns.data.created_expiring}, high
                    balance {runCampaigns.data.created_high_balance}, реактивация{" "}
                    {runCampaigns.data.created_reengagement}; пропуски: лимиты{" "}
                    {runCampaigns.data.skipped_limits}, cooldown{" "}
                    {runCampaigns.data.skipped_cooldown}, пересечение кампаний{" "}
                    {runCampaigns.data.skipped_cross_campaign}, SMS-дубль{" "}
                    {runCampaigns.data.skipped_sms_duplicate}, opt-out{" "}
                    {runCampaigns.data.skipped_opt_out}
                  </Text>
                )}
                {updateCampaignSettings.isError && (
                  <QueryErrorAlert
                    error={updateCampaignSettings.error}
                    title="Не удалось сохранить настройки кампаний"
                  />
                )}
                {runCampaigns.isError && (
                  <QueryErrorAlert
                    error={runCampaigns.error}
                    title="Не удалось запустить кампании"
                  />
                )}
              </Stack>
            )}
          </Card>
        </Tabs.Panel>
          </Tabs>
        </Tabs.Panel>
        ) : null}
      </Tabs>
    </Stack>
  );
}

