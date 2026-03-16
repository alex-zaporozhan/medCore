import { useAdminBookings } from "@/hooks/useAdminBookings";
import { useAdminLoyaltySummaryByContact, useAddFamilyMember } from "@/hooks/useLoyalty";
import { useCreatePatient, useUpdatePatient, usePatients } from "@/hooks";
import { usePatientAiInsight, type PatientAiInsightWithStatus } from "@/hooks/useChatAi";
import { useDoctors } from "@/hooks/useDoctors";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import type { Patient } from "@/api/types";
import {
  Avatar,
  Badge,
  Button,
  Drawer,
  Group,
  Menu,
  ActionIcon,
  Modal,
  Paper,
  Select,
  Stack,
  Tabs,
  Text,
  TextInput,
  Table,
  Skeleton,
} from "@mantine/core";
import { IconCopy, IconPrinter, IconTrash, IconDotsVertical, IconMessageCircle } from "@tabler/icons-react";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import dayjs from "dayjs";

const BIRTHDAY_SOON_DAYS = 14;

function isBirthdaySoon(dateOfBirth: string | null | undefined): boolean {
  if (!dateOfBirth) return false;
  const dob = dayjs(dateOfBirth);
  const now = dayjs();
  const thisYear = dob.year(now.year());
  const daysUntil = thisYear.diff(now, "day");
  return daysUntil >= 0 && daysUntil <= BIRTHDAY_SOON_DAYS;
}

export interface PatientTags {
  vip?: boolean;
  debtor?: boolean;
  cancellation_prone?: boolean;
}

interface PatientEntityDrawerProps {
  opened: boolean;
  onClose: () => void;
  patient: Patient | null;
  mode: "view" | "create" | "edit";
  initialForm?: { phone: string; full_name: string; email: string };
  onSaved?: () => void;
  /** Теги пациента (VIP, Должник, Склонен к отменам) — при наличии API */
  tags?: PatientTags;
}

export function PatientEntityDrawer({
  opened,
  onClose,
  patient,
  mode,
  initialForm,
  onSaved,
  tags: tagsProp,
}: PatientEntityDrawerProps) {
  const { currentClinicId } = useAdminClinic();
  const [activeTab, setActiveTab] = useState<string | null>("main");
  const [formPhone, setFormPhone] = useState(initialForm?.phone ?? patient?.phone ?? "");
  const [formFullName, setFormFullName] = useState(initialForm?.full_name ?? patient?.full_name ?? "");
  const [formEmail, setFormEmail] = useState(initialForm?.email ?? patient?.email ?? "");
  const [insightText, setInsightText] = useState<string | null>(null);
  const [insightStatus, setInsightStatus] = useState<string | null>(null);
  const [insightError, setInsightError] = useState<string | null>(null);
  const [familyModalOpen, setFamilyModalOpen] = useState(false);
  const [familySubscriptionId, setFamilySubscriptionId] = useState<string | null>(null);
  const [familyPatientId, setFamilyPatientId] = useState<string | null>(null);

  const patientId = patient?.id ?? null;
  const phoneForBookings = mode === "view" || mode === "edit" ? patient?.phone : formPhone;

  const { data: bookings } = useAdminBookings({
    patient_phone: phoneForBookings || undefined,
    limit: 50,
  });
  const { data: loyaltySummary } = useAdminLoyaltySummaryByContact(patient?.id ?? null);
  const { data: doctors } = useDoctors({ clinic_id: currentClinicId ?? undefined, is_active: true });
  const doctorIdToName = doctors?.reduce<Record<string, string>>((acc, d) => {
    acc[d.id] = d.full_name;
    return acc;
  }, {}) ?? {};
  const showDebtor =
    tagsProp?.debtor ?? (loyaltySummary?.wallet && Number(loyaltySummary.wallet.balance) < 0);
  const showVip = tagsProp?.vip ?? false;
  const showCancellationProne = tagsProp?.cancellation_prone ?? false;
  const createMutation = useCreatePatient();
  const updateMutation = useUpdatePatient();
  const aiInsightMutation = usePatientAiInsight(patientId);
  const addFamilyMember = useAddFamilyMember();
  const { data: patientsList = [] } = usePatients({
    clinic_id: currentClinicId ?? undefined,
  });

  useEffect(() => {
    if (patient) {
      setFormPhone(patient.phone);
      setFormFullName(patient.full_name ?? "");
      setFormEmail(patient.email ?? "");
    } else if (initialForm) {
      setFormPhone(initialForm.phone);
      setFormFullName(initialForm.full_name ?? "");
      setFormEmail(initialForm.email ?? "");
    }
  }, [patient, initialForm]);

  const handleSave = () => {
    if (mode === "edit" && patientId) {
      updateMutation.mutate(
        {
          id: patientId,
          body: { full_name: formFullName || null, email: formEmail || null },
        },
        { onSuccess: () => { onSaved?.(); onClose(); } }
      );
    } else if (mode === "create") {
      createMutation.mutate(
        { phone: formPhone, full_name: formFullName || null, email: formEmail || null },
        { onSuccess: () => { onSaved?.(); onClose(); } }
      );
    }
  };

  const loadAiInsight = () => {
    if (!patientId) return;
    setInsightText(null);
    setInsightStatus(null);
    setInsightError(null);
    aiInsightMutation.mutate(undefined, {
      onSuccess: (res: PatientAiInsightWithStatus) => {
        setInsightText(
          [res.summary, res.next_best_action].filter(Boolean).join("\n\n") || res.summary
        );
        setInsightStatus(res.aiStatus ?? null);
      },
      onError: () => {
        setInsightError("AI‑обзор временно недоступен.");
      },
    });
  };

  const displayName = patient?.full_name || formFullName || patient?.phone || formPhone || "Новый пациент";
  const dateOfBirth = (patient as Patient & { date_of_birth?: string | null })?.date_of_birth;
  const showBirthdaySoon = isBirthdaySoon(dateOfBirth);

  const title =
    mode === "create"
      ? "Новый пациент"
      : mode === "edit"
        ? "Редактировать пациента"
        : displayName;

  return (
    <Drawer
      position="right"
      size="lg"
      opened={opened}
      onClose={onClose}
      title={title}
      styles={{ body: { paddingTop: 0 } }}
    >
      {(mode === "view" || mode === "edit") && patient && (
        <Stack gap="md" mb="md">
          <Group justify="space-between" wrap="nowrap">
            <Group wrap="nowrap" gap="sm">
              <Avatar radius="xl" size="lg" color="indigo">
                {(patient.full_name || patient.phone).slice(0, 2).toUpperCase()}
              </Avatar>
              <Stack gap={2}>
                <Group gap="xs">
                  <Text fw={600} size="lg">
                    {patient.full_name || "—"}
                  </Text>
                  {showBirthdaySoon && (
                    <Badge size="sm" color="pink" variant="light">
                      Скоро день рождения
                    </Badge>
                  )}
                </Group>
                <Text size="sm" c="dimmed">
                  {patient.phone}
                </Text>
                {patient.email && (
                  <Text size="xs" c="dimmed">
                    {patient.email}
                  </Text>
                )}
                {loyaltySummary?.wallet && (
                  <Text size="xs">
                    Баланс бонусов: {loyaltySummary.wallet.balance} {loyaltySummary.wallet.currency}
                  </Text>
                )}
                {(showVip || showDebtor || showCancellationProne) && (
                  <Group gap="xs" mt={4}>
                    {showVip && (
                      <Badge size="sm" color="yellow" variant="light">VIP</Badge>
                    )}
                    {showDebtor && (
                      <Badge size="sm" color="red" variant="light">Должник</Badge>
                    )}
                    {showCancellationProne && (
                      <Badge size="sm" color="orange" variant="light">Склонен к отменам</Badge>
                    )}
                  </Group>
                )}
                <Text size="xs" c="dimmed">LTV — при наличии API</Text>
              </Stack>
            </Group>
            <Menu position="bottom-end">
              <Menu.Target>
                <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                  <IconDotsVertical size={16} />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item leftSection={<IconPrinter size={14} />}>Печать</Menu.Item>
                <Menu.Item leftSection={<IconCopy size={14} />}>Скопировать</Menu.Item>
                <Menu.Item leftSection={<IconTrash size={14} />} color="red">
                  Удалить
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Stack>
      )}

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List>
          <Tabs.Tab value="main">Основное</Tabs.Tab>
          <Tabs.Tab value="visits">Визиты</Tabs.Tab>
          <Tabs.Tab value="finance">Финансы</Tabs.Tab>
          <Tabs.Tab value="subscriptions">Абонементы</Tabs.Tab>
          <Tabs.Tab value="notes">Медкарта / Заметки</Tabs.Tab>
          <Tabs.Tab value="comms">Коммуникации</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="main" pt="md">
          <Stack gap="sm">
            {mode === "view" && patient ? (
              <>
                <Text size="sm" c="dimmed">Телефон</Text>
                <Text>{patient.phone}</Text>
                <Text size="sm" c="dimmed">ФИО</Text>
                <Text>{patient.full_name ?? "—"}</Text>
                <Text size="sm" c="dimmed">Email</Text>
                <Text>{patient.email ?? "—"}</Text>
                {dateOfBirth && (
                  <Text size="sm" c="dimmed">
                    Дата рождения: {dayjs(dateOfBirth).format("DD.MM.YYYY")}
                    {showBirthdaySoon && " — Скоро день рождения"}
                  </Text>
                )}
                <Text size="xs" c="dimmed">
                  Пол, категория, согласия на ПД, источник UTM — при наличии API.
                </Text>
                <Button variant="light" size="xs" onClick={loadAiInsight}>
                  AI‑обзор
                </Button>
                {insightError && <Text size="sm" c="red">{insightError}</Text>}
                {insightText && (
                  <Stack gap={4}>
                    <Text size="sm" c="dimmed">{insightText}</Text>
                    {insightStatus && <Text size="xs" c="dimmed">{insightStatus}</Text>}
                  </Stack>
                )}
              </>
            ) : (
              <>
                <TextInput
                  label="Телефон"
                  value={formPhone}
                  onChange={(e) => setFormPhone(e.target.value)}
                  required
                  disabled={!!patient}
                />
                <TextInput
                  label="ФИО"
                  value={formFullName}
                  onChange={(e) => setFormFullName(e.target.value)}
                />
                <TextInput
                  label="Email"
                  type="email"
                  value={formEmail}
                  onChange={(e) => setFormEmail(e.target.value)}
                />
                {dateOfBirth && (
                  <Text size="sm" c="dimmed">
                    Дата рождения: {dayjs(dateOfBirth).format("DD.MM.YYYY")}
                    {showBirthdaySoon && " — Скоро день рождения"}
                  </Text>
                )}
                {patient && (
                  <>
                    <Button variant="light" size="xs" onClick={loadAiInsight}>
                      AI‑обзор
                    </Button>
                    {insightError && <Text size="sm" c="red">{insightError}</Text>}
                    {insightText && (
                      <Stack gap={4}>
                        <Text size="sm" c="dimmed">{insightText}</Text>
                        {insightStatus && <Text size="xs" c="dimmed">{insightStatus}</Text>}
                      </Stack>
                    )}
                  </>
                )}
                <Group mt="sm">
                  <Button onClick={handleSave} loading={createMutation.isPending || updateMutation.isPending}>
                    Сохранить
                  </Button>
                  <Button variant="subtle" onClick={onClose}>
                    Отмена
                  </Button>
                </Group>
                {(createMutation.isError || updateMutation.isError) && (
                  <Text size="sm" c="red">
                    {createMutation.error instanceof Error
                      ? createMutation.error.message
                      : updateMutation.error instanceof Error
                        ? updateMutation.error.message
                        : "Ошибка"}
                  </Text>
                )}
              </>
            )}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="visits" pt="md">
          {!phoneForBookings ? (
            <Text size="sm" c="dimmed">
              Сохраните пациента, чтобы видеть визиты.
            </Text>
          ) : !bookings ? (
            <Skeleton height={120} />
          ) : bookings.length === 0 ? (
            <Text size="sm" c="dimmed">
              Нет визитов.
            </Text>
          ) : (
            <Table striped verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>Дата</Table.Th>
                  <Table.Th>Время</Table.Th>
                  <Table.Th>Врач</Table.Th>
                  <Table.Th>Услуга</Table.Th>
                  <Table.Th>Статус</Table.Th>
                  <Table.Th>Сумма</Table.Th>
                  <Table.Th>NPS</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bookings.slice(0, 20).map((b) => (
                  <Table.Tr key={b.id}>
                    <Table.Td>{b.appointment_date}</Table.Td>
                    <Table.Td>{String(b.appointment_time).slice(0, 5)}</Table.Td>
                    <Table.Td>{doctorIdToName[b.doctor_id] ?? b.doctor_id}</Table.Td>
                    <Table.Td>{b.service_id}</Table.Td>
                    <Table.Td>{b.status}</Table.Td>
                    <Table.Td>{b.prepayment_amount ? `${b.prepayment_amount} ₽` : "—"}</Table.Td>
                    <Table.Td>—</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="finance" pt="md">
          {!patient ? (
            <Text size="sm" c="dimmed">
              Сохраните пациента для просмотра финансов.
            </Text>
          ) : !loyaltySummary ? (
            <Skeleton height={80} />
          ) : (
            <Stack gap="sm">
              {loyaltySummary.wallet && (
                <Text size="sm">
                  Баланс: {loyaltySummary.wallet.balance} {loyaltySummary.wallet.currency}
                </Text>
              )}
              {loyaltySummary.subscriptions?.length ? (
                <Text size="sm">
                  Абонементы: {loyaltySummary.subscriptions.length}
                </Text>
              ) : (
                <Text size="sm" c="dimmed">
                  Платежи, возвраты и абонементы — при наличии API.
                </Text>
              )}
            </Stack>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="subscriptions" pt="md">
          {!patient ? (
            <Text size="sm" c="dimmed">
              Сохраните пациента для просмотра абонементов.
            </Text>
          ) : !loyaltySummary ? (
            <Skeleton height={80} />
          ) : !loyaltySummary.subscriptions?.length ? (
            <Stack gap="sm">
              <Text size="sm" c="dimmed">
                У пациента пока нет активных абонементов.
              </Text>
            </Stack>
          ) : (
            <Stack gap="sm">
              {loyaltySummary.subscriptions.map((sub) => (
                <Paper key={sub.id} p="sm" withBorder radius="md">
                  <Group justify="space-between">
                    <Text size="sm" fw={500}>
                      Пакет {sub.subscription_package_id.slice(0, 8)}…
                    </Text>
                    <Badge size="sm" variant="light">
                      {sub.status}
                    </Badge>
                  </Group>
                  <Group gap="md" mt="xs">
                    {sub.remaining_visits != null && (
                      <Text size="xs" c="dimmed">
                        Остаток визитов: {sub.remaining_visits}
                      </Text>
                    )}
                    {sub.remaining_amount != null && (
                      <Text size="xs" c="dimmed">
                        Остаток: {sub.remaining_amount} ₽
                      </Text>
                    )}
                    {sub.expires_at && (
                      <Text size="xs" c="dimmed">
                        Истекает: {dayjs(sub.expires_at).format("DD.MM.YYYY")}
                      </Text>
                    )}
                  </Group>
                </Paper>
              ))}
              <Button
                variant="light"
                size="sm"
                leftSection={<span>+</span>}
                onClick={() => {
                  setFamilySubscriptionId(loyaltySummary.subscriptions[0]?.id ?? null);
                  setFamilyPatientId(null);
                  setFamilyModalOpen(true);
                }}
              >
                Добавить члена семьи
              </Button>
              <Modal
                title="Добавить члена семьи"
                opened={familyModalOpen}
                onClose={() => setFamilyModalOpen(false)}
              >
                <Stack gap="sm">
                  <Select
                    label="Абонемент"
                    placeholder="Выберите абонемент"
                    data={loyaltySummary.subscriptions.map((s) => ({
                      value: s.id,
                      label: `Пакет ${s.subscription_package_id.slice(0, 8)}… (остаток: ${s.remaining_visits ?? s.remaining_amount ?? "—"})`,
                    }))}
                    value={familySubscriptionId}
                    onChange={(v) => setFamilySubscriptionId(v)}
                  />
                  <Select
                    label="Пациент (член семьи)"
                    placeholder="Выберите пациента"
                    data={patientsList
                      .filter((p) => p.id !== patient?.id)
                      .map((p) => ({
                        value: p.id,
                        label: [p.full_name, p.phone].filter(Boolean).join(" — ") || p.id.slice(0, 8),
                      }))}
                    value={familyPatientId}
                    onChange={(v) => setFamilyPatientId(v)}
                    searchable
                    clearable
                  />
                  <Group justify="flex-end" mt="md">
                    <Button variant="subtle" onClick={() => setFamilyModalOpen(false)}>
                      Отмена
                    </Button>
                    <Button
                      disabled={!familySubscriptionId || !familyPatientId}
                      loading={addFamilyMember.isPending}
                      onClick={() => {
                        if (!familySubscriptionId || !familyPatientId) return;
                        addFamilyMember.mutate(
                          { subscriptionId: familySubscriptionId, patientId: familyPatientId },
                          {
                            onSuccess: () => {
                              setFamilyModalOpen(false);
                              setFamilySubscriptionId(null);
                              setFamilyPatientId(null);
                            },
                          }
                        );
                      }}
                    >
                      Добавить
                    </Button>
                  </Group>
                </Stack>
              </Modal>
            </Stack>
          )}
        </Tabs.Panel>

        <Tabs.Panel value="notes" pt="md">
          <Text size="sm" c="dimmed">
            Медкарта и заметки (RichText, прикрепление файлов) — при наличии API.
          </Text>
        </Tabs.Panel>

        <Tabs.Panel value="comms" pt="md">
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              История отправленных уведомлений (SMS/Email/TG) — при наличии API.
            </Text>
            {patient && (
              <Button
                component={Link}
                to={`/admin/omni-chat?patient_id=${patient.id}`}
                leftSection={<IconMessageCircle size={16} />}
                variant="light"
              >
                Открыть в чате
              </Button>
            )}
          </Stack>
        </Tabs.Panel>
      </Tabs>
    </Drawer>
  );
}
