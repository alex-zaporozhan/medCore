import {
  useAdminBookings,
  useAdminLoyaltySummaryByContact,
  useAddFamilyMember,
  useAdminPatientDiagnoses,
  useAdminPatientMedicalFiles,
  useAdminPatientMedicalVisits,
  useCreateAdminPatientDiagnosis,
  useCreateAdminPatientMedicalVisit,
  useUploadAdminPatientMedicalFile,
  fetchAdminPatientMedicalFileDownloadUrl,
  useCreatePatient,
  useUpdatePatient,
  usePatients,
  usePatientAiInsight,
  useDoctors,
  type PatientAiInsightWithStatus,
} from "@/hooks";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import type { Patient } from "@/api/types";
import { EntityDrawerFieldBlock, EntityDrawerFooterBar } from "@/admin/components/entity/entityDrawerChrome";
import { AdminDrawer, GlassModal, QueryErrorAlert } from "@/shared/ui";
import { displayPersonName } from "@/shared/ui/personNameFallback";
import { bookingStatusLabel } from "@/shared/bookingStatusMeta";
import {
  Avatar,
  Badge,
  Button,
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
  Textarea,
  ScrollArea,
  Table,
  Skeleton,
  Alert,
} from "@mantine/core";
import { IconCopy, IconPrinter, IconTrash, IconDotsVertical, IconMessageCircle } from "@tabler/icons-react";
import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";

/** Local copy of booking tab pane height — do not import from entity drawer chrome. */
const PATIENT_MODAL_TABS_H = 440;

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
  /** Центрированная модалка или боковая панель */
  presentation?: "modal" | "drawer";
}

export function PatientEntityDrawer({
  opened,
  onClose,
  patient,
  mode,
  initialForm,
  onSaved,
  tags: tagsProp,
  presentation = "modal",
}: PatientEntityDrawerProps) {
  const { t } = useTranslation("directory");
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

  const bookingsQuery = useAdminBookings(
    {
      patient_phone: phoneForBookings || undefined,
      limit: 50,
    },
    { enabled: Boolean(phoneForBookings) },
  );
  const { data: bookings } = bookingsQuery;
  const loyaltyQuery = useAdminLoyaltySummaryByContact(patient?.id ?? null);
  const { data: loyaltySummary } = loyaltyQuery;
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
  const medVisits = useAdminPatientMedicalVisits(currentClinicId, patientId);
  const medDiagnoses = useAdminPatientDiagnoses(currentClinicId, patientId);
  const medFiles = useAdminPatientMedicalFiles(currentClinicId, patientId);
  const createVisit = useCreateAdminPatientMedicalVisit(currentClinicId ?? "", patientId ?? "");
  const createDiagnosis = useCreateAdminPatientDiagnosis(currentClinicId ?? "", patientId ?? "");
  const uploadMedicalFile = useUploadAdminPatientMedicalFile(currentClinicId ?? "", patientId ?? "");
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

  const [visitDate, setVisitDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [visitNotes, setVisitNotes] = useState("");
  const [diagDate, setDiagDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [diagTitle, setDiagTitle] = useState("");
  const [diagDescription, setDiagDescription] = useState("");
  const [fileToUpload, setFileToUpload] = useState<File | null>(null);
  const [medicalDownloadError, setMedicalDownloadError] = useState<string | null>(null);

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
        setInsightError(t("patientDrawer.aiUnavailable"));
      },
    });
  };

  const displayName =
    patient?.full_name || formFullName || patient?.phone || formPhone || t("patientDrawer.newTitle");
  const dateOfBirth = (patient as Patient & { date_of_birth?: string | null })?.date_of_birth;
  const showBirthdaySoon = isBirthdaySoon(dateOfBirth);

  const title =
    mode === "create"
      ? t("patientDrawer.newTitle")
      : mode === "edit"
        ? t("patientDrawer.editTitle")
        : displayName;

  const passOptionLabel = (s: {
    remaining_visits?: number | null;
    remaining_amount?: number | string | null;
  }) =>
    t("patientDrawer.packageRemain", {
      remain: String(s.remaining_visits ?? s.remaining_amount ?? "—"),
    });

  const inner = (
    <>
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
                      {t("patientDrawer.birthdaySoon")}
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
                    {t("patientDrawer.bonusBalance", {
                      balance: loyaltySummary.wallet.balance,
                      currency: loyaltySummary.wallet.currency,
                    })}
                  </Text>
                )}
                {(showVip || showDebtor || showCancellationProne) && (
                  <Group gap="xs" mt={4}>
                    {showVip && (
                      <Badge size="sm" color="yellow" variant="light">
                        {t("patientDrawer.vip")}
                      </Badge>
                    )}
                    {showDebtor && (
                      <Badge size="sm" color="red" variant="light">{t("patientDrawer.debtor")}</Badge>
                    )}
                    {showCancellationProne && (
                      <Badge size="sm" color="orange" variant="light">{t("patientDrawer.cancellationProne")}</Badge>
                    )}
                  </Group>
                )}
                <Text size="xs" c="dimmed">{t("patientDrawer.ltvSoon")}</Text>
              </Stack>
            </Group>
            <Menu position="bottom-end">
              <Menu.Target>
                <ActionIcon variant="subtle" size="sm" aria-label={t("actions")}>
                  <IconDotsVertical size={16} />
                </ActionIcon>
              </Menu.Target>
              <Menu.Dropdown>
                <Menu.Item leftSection={<IconPrinter size={14} />}>{t("print")}</Menu.Item>
                <Menu.Item leftSection={<IconCopy size={14} />}>{t("copy")}</Menu.Item>
                <Menu.Item leftSection={<IconTrash size={14} />} color="red">
                  {t("delete")}
                </Menu.Item>
              </Menu.Dropdown>
            </Menu>
          </Group>
        </Stack>
      )}

      <Tabs value={activeTab} onChange={setActiveTab}>
        <Tabs.List
          style={{
            flexWrap: "nowrap",
            overflowX: "auto",
            minHeight: 40,
            flexShrink: 0,
          }}
        >
          <Tabs.Tab value="main">{t("patientDrawer.tabMain")}</Tabs.Tab>
          <Tabs.Tab value="visits">{t("patientDrawer.tabVisits")}</Tabs.Tab>
          <Tabs.Tab value="finance">{t("patientDrawer.tabFinance")}</Tabs.Tab>
          <Tabs.Tab value="subscriptions">{t("patientDrawer.tabSubscriptions")}</Tabs.Tab>
          <Tabs.Tab value="notes">{t("patientDrawer.tabNotes")}</Tabs.Tab>
          <Tabs.Tab value="comms">{t("patientDrawer.tabComms")}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="main" pt="md">
          <ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
            {mode === "view" && patient ? (
              <>
                <EntityDrawerFieldBlock label={t("patientDrawer.phone")}>
                  <Text size="sm">{patient.phone}</Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("patientDrawer.fullName")}>
                  <Text size="sm">{patient.full_name ?? "—"}</Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("email")}>
                  <Text size="sm">{patient.email ?? "—"}</Text>
                </EntityDrawerFieldBlock>
                {dateOfBirth && (
                  <EntityDrawerFieldBlock label={t("patientDrawer.dateOfBirth")}>
                    <Text size="sm">
                      {dayjs(dateOfBirth).format("DD.MM.YYYY")}
                      {showBirthdaySoon ? ` — ${t("patientDrawer.birthdaySoon")}` : ""}
                    </Text>
                  </EntityDrawerFieldBlock>
                )}
                <EntityDrawerFieldBlock label={t("patientDrawer.extras")}>
                  <Text size="xs" c="dimmed">
                    {t("patientDrawer.extrasHint")}
                  </Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("patientDrawer.aiOverview")}>
                  <Stack gap="xs">
                    <Button variant="light" size="xs" onClick={loadAiInsight}>
                      {t("patientDrawer.loadAi")}
                    </Button>
                    {insightError && (
                      <QueryErrorAlert error={insightError} title={t("patientDrawer.aiFailed")} />
                    )}
                    {insightText && (
                      <Stack gap={4}>
                        <Text size="sm" c="dimmed">{insightText}</Text>
                        {insightStatus && <Text size="xs" c="dimmed">{insightStatus}</Text>}
                      </Stack>
                    )}
                  </Stack>
                </EntityDrawerFieldBlock>
              </>
            ) : (
              <>
                <EntityDrawerFieldBlock label={t("patientDrawer.contact")}>
                  <Stack gap="sm">
                    <TextInput
                      label={t("patientDrawer.phone")}
                      value={formPhone}
                      onChange={(e) => setFormPhone(e.target.value)}
                      required
                      disabled={!!patient}
                    />
                    <TextInput
                      label={t("patientDrawer.fullName")}
                      value={formFullName}
                      onChange={(e) => setFormFullName(e.target.value)}
                    />
                    <TextInput
                      label={t("email")}
                      type="email"
                      value={formEmail}
                      onChange={(e) => setFormEmail(e.target.value)}
                    />
                    {dateOfBirth && (
                      <Text size="sm" c="dimmed">
                        {t("patientDrawer.birthdayLine", { date: dayjs(dateOfBirth).format("DD.MM.YYYY") })}
                        {showBirthdaySoon ? ` — ${t("patientDrawer.birthdaySoon")}` : ""}
                      </Text>
                    )}
                    {patient && (
                      <>
                        <Button variant="light" size="xs" onClick={loadAiInsight}>
                          {t("patientDrawer.aiOverview")}
                        </Button>
                        {insightError && (
                          <QueryErrorAlert error={insightError} title={t("patientDrawer.aiFailed")} />
                        )}
                        {insightText && (
                          <Stack gap={4}>
                            <Text size="sm" c="dimmed">{insightText}</Text>
                            {insightStatus && <Text size="xs" c="dimmed">{insightStatus}</Text>}
                          </Stack>
                        )}
                      </>
                    )}
                  </Stack>
                </EntityDrawerFieldBlock>
                <EntityDrawerFooterBar>
                  <Button onClick={handleSave} loading={createMutation.isPending || updateMutation.isPending}>
                    {t("save")}
                  </Button>
                  <Button variant="subtle" onClick={onClose}>
                    {t("cancel")}
                  </Button>
                </EntityDrawerFooterBar>
                {(createMutation.isError || updateMutation.isError) && (
                  <QueryErrorAlert
                    error={
                      createMutation.isError ? createMutation.error : updateMutation.error
                    }
                    title={t("patientDrawer.saveFailed")}
                  />
                )}
              </>
            )}
          </Stack>
          </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="visits" pt="md">
          <ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll">
          {!phoneForBookings ? (
            <Text size="sm" c="dimmed">
              {t("patientDrawer.saveToSeeVisits")}
            </Text>
          ) : bookingsQuery.isError ? (
            <QueryErrorAlert error={bookingsQuery.error} title={t("patientDrawer.chartLoadFailed")} />
          ) : bookingsQuery.isPending || !bookings ? (
            <Skeleton height={120} />
          ) : bookings.length === 0 ? (
            <Text size="sm" c="dimmed">
              {t("patientDrawer.noVisits")}
            </Text>
          ) : (
            <Table striped verticalSpacing="sm">
              <Table.Thead>
                <Table.Tr>
                  <Table.Th>{t("patientDrawer.date")}</Table.Th>
                  <Table.Th>{t("patientDrawer.time")}</Table.Th>
                  <Table.Th>{t("patientDrawer.doctor")}</Table.Th>
                  <Table.Th>{t("patientDrawer.service")}</Table.Th>
                  <Table.Th>{t("patientDrawer.status")}</Table.Th>
                  <Table.Th>{t("patientDrawer.amount")}</Table.Th>
                  <Table.Th>{t("patientDrawer.nps")}</Table.Th>
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {bookings.slice(0, 20).map((b) => (
                  <Table.Tr key={b.id}>
                    <Table.Td>{b.appointment_date}</Table.Td>
                    <Table.Td>{String(b.appointment_time).slice(0, 5)}</Table.Td>
                    <Table.Td>
                      {displayPersonName(
                        b.doctor_name ?? doctorIdToName[b.doctor_id],
                        b.doctor_id,
                      )}
                    </Table.Td>
                    <Table.Td>{displayPersonName(b.service_name, b.service_id)}</Table.Td>
                    <Table.Td>{bookingStatusLabel(b.status)}</Table.Td>
                    <Table.Td>{b.prepayment_amount ? `${b.prepayment_amount} ₽` : "—"}</Table.Td>
                    <Table.Td>—</Table.Td>
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          )}
                  </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="finance" pt="md">
          <ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll">
          {!patient ? (
            <Text size="sm" c="dimmed">
              {t("patientDrawer.saveToSeeFinance")}
            </Text>
          ) : loyaltyQuery.isError ? (
            <QueryErrorAlert error={loyaltyQuery.error} title={t("patientDrawer.chartLoadFailed")} />
          ) : loyaltyQuery.isPending || !loyaltySummary ? (
            <Skeleton height={80} />
          ) : (
            <Stack gap="sm">
              {loyaltySummary.wallet && (
                <Text size="sm">
                  {t("patientDrawer.balance", { balance: loyaltySummary.wallet.balance, currency: loyaltySummary.wallet.currency })}
                </Text>
              )}
              {loyaltySummary.subscriptions?.length ? (
                <Text size="sm">
                  {t("patientDrawer.subscriptionsCount", { count: loyaltySummary.subscriptions.length })}
                </Text>
              ) : (
                <Text size="sm" c="dimmed">
                  {t("patientDrawer.financeHint")}
                </Text>
              )}
            </Stack>
          )}
                  </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="subscriptions" pt="md">
          <ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll">
          {!patient ? (
            <Text size="sm" c="dimmed">
              {t("patientDrawer.saveToSeeSubs")}
            </Text>
          ) : loyaltyQuery.isError ? (
            <QueryErrorAlert error={loyaltyQuery.error} title={t("patientDrawer.chartLoadFailed")} />
          ) : loyaltyQuery.isPending || !loyaltySummary ? (
            <Skeleton height={80} />
          ) : !loyaltySummary.subscriptions?.length ? (
            <Stack gap="sm">
              <Text size="sm" c="dimmed">
                {t("patientDrawer.noSubs")}
              </Text>
            </Stack>
          ) : (
            <Stack gap="sm">
              {loyaltySummary.subscriptions.map((sub) => (
                <Paper key={sub.id} p="sm" withBorder radius="md">
                  <Group justify="space-between">
                    <Text size="sm" fw={500}>
                      {t("patientDrawer.package")}
                    </Text>
                    <Badge size="sm" variant="light">
                      {t(`patientDrawer.subStatus.${sub.status}`, {
                        defaultValue: sub.status,
                      })}
                    </Badge>
                  </Group>
                  <Group gap="md" mt="xs">
                    {sub.remaining_visits != null && (
                      <Text size="xs" c="dimmed">
                        {t("patientDrawer.remainingVisits", { count: sub.remaining_visits })}
                      </Text>
                    )}
                    {sub.remaining_amount != null && (
                      <Text size="xs" c="dimmed">
                        {t("patientDrawer.remainingAmount", { amount: sub.remaining_amount })}
                      </Text>
                    )}
                    {sub.expires_at && (
                      <Text size="xs" c="dimmed">
                        {t("patientDrawer.expires", { date: dayjs(sub.expires_at).format("DD.MM.YYYY") })}
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
                {t("patientDrawer.addFamily")}
              </Button>
              <Modal
                title={t("patientDrawer.addFamily")}
                opened={familyModalOpen}
                onClose={() => {
                  setFamilyModalOpen(false);
                  addFamilyMember.reset();
                }}
                centered
                zIndex={400}
              >
                <Stack gap="sm">
                  {addFamilyMember.isError ? (
                    <QueryErrorAlert
                      error={addFamilyMember.error}
                      title={t("patientDrawer.familyAddFailed")}
                    />
                  ) : null}
                  <Select
                    label={t("patientDrawer.subscription")}
                    placeholder={t("patientDrawer.subscriptionPlaceholder")}
                    data={loyaltySummary.subscriptions.map((s) => ({
                      value: s.id,
                      label: passOptionLabel(s),
                    }))}
                    value={familySubscriptionId}
                    onChange={(v) => setFamilySubscriptionId(v)}
                  />
                  <Select
                    label={t("patientDrawer.familyPatient")}
                    placeholder={t("patientDrawer.familyPatientPlaceholder")}
                    data={patientsList
                      .filter((p) => p.id !== patient?.id)
                      .map((p) => ({
                        value: p.id,
                        label: [p.full_name, p.phone].filter(Boolean).join(" — ") || t("patientDrawer.familyPatient"),
                      }))}
                    value={familyPatientId}
                    onChange={(v) => setFamilyPatientId(v)}
                    searchable
                    clearable
                  />
                  <Group justify="flex-end" mt="md">
                    <Button variant="subtle" onClick={() => setFamilyModalOpen(false)}>
                      {t("cancel")}
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
                              addFamilyMember.reset();
                            },
                          }
                        );
                      }}
                    >
                      {t("patientDrawer.add")}
                    </Button>
                  </Group>
                </Stack>
              </Modal>
            </Stack>
          )}
                  </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="notes" pt="md">
          <ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll">
          {!patientId || !currentClinicId ? (
            <Text size="sm" c="dimmed">
              {t("patientDrawer.saveToSeeChart")}
            </Text>
          ) : (
              <Stack gap="md" pr="md">
                <EntityDrawerFieldBlock label={t("patientDrawer.visitsBlock")}>
                  <Stack gap="sm">
                  <TextInput
                    type="date"
                    label={t("patientDrawer.date")}
                    value={visitDate}
                    onChange={(e) => setVisitDate(e.target.value)}
                    disabled={mode === "view"}
                  />
                  <Textarea
                    label={t("patientDrawer.notesMarkdown")}
                    value={visitNotes}
                    onChange={(e) => setVisitNotes(e.target.value)}
                    minRows={3}
                    disabled={mode === "view"}
                  />
                  {mode !== "view" && (
                    <Group justify="flex-end">
                      <Button
                        onClick={() =>
                          createVisit.mutate({
                            visit_date: visitDate,
                            notes_md: visitNotes || null,
                          })
                        }
                        loading={createVisit.isPending}
                      >
                        {t("patientDrawer.addVisit")}
                      </Button>
                    </Group>
                  )}
                  {createVisit.isError ? (
                    <QueryErrorAlert
                      error={createVisit.error}
                      title={t("patientDrawer.saveFailed")}
                    />
                  ) : null}
                  {medVisits.isLoading ? (
                    <Skeleton height={80} />
                  ) : medVisits.data?.length ? (
                    <Table striped verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>{t("patientDrawer.date")}</Table.Th>
                          <Table.Th>{t("patientDrawer.notes")}</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {medVisits.data.map((v) => (
                          <Table.Tr key={v.id}>
                            <Table.Td>{v.visit_date}</Table.Td>
                            <Table.Td>
                              <Text size="sm" style={{ whiteSpace: "pre-wrap" }}>
                                {v.notes_md || "—"}
                              </Text>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  ) : (
                    <Text size="sm" c="dimmed">
                      {t("patientDrawer.noChartVisits")}
                    </Text>
                  )}
                  </Stack>
                </EntityDrawerFieldBlock>

                <EntityDrawerFieldBlock label={t("patientDrawer.diagnoses")}>
                  <Stack gap="sm">
                  <Group grow>
                    <TextInput
                      type="date"
                      label={t("patientDrawer.date")}
                      value={diagDate}
                      onChange={(e) => setDiagDate(e.target.value)}
                      disabled={mode === "view"}
                    />
                    <TextInput
                      label={t("patientDrawer.diagName")}
                      value={diagTitle}
                      onChange={(e) => setDiagTitle(e.target.value)}
                      disabled={mode === "view"}
                    />
                  </Group>
                  <Textarea
                    label={t("patientDrawer.description")}
                    value={diagDescription}
                    onChange={(e) => setDiagDescription(e.target.value)}
                    minRows={2}
                    disabled={mode === "view"}
                  />
                  {mode !== "view" && (
                    <Group justify="flex-end">
                      <Button
                        onClick={() =>
                          createDiagnosis.mutate({
                            diagnosis_date: diagDate,
                            title: diagTitle,
                            description: diagDescription || null,
                          })
                        }
                        loading={createDiagnosis.isPending}
                        disabled={!diagTitle.trim()}
                      >
                        {t("patientDrawer.addDiagnosis")}
                      </Button>
                    </Group>
                  )}
                  {createDiagnosis.isError ? (
                    <QueryErrorAlert
                      error={createDiagnosis.error}
                      title={t("patientDrawer.saveFailed")}
                    />
                  ) : null}
                  {medDiagnoses.isLoading ? (
                    <Skeleton height={80} />
                  ) : medDiagnoses.data?.length ? (
                    <Table striped verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>{t("patientDrawer.date")}</Table.Th>
                          <Table.Th>{t("patientDrawer.diagnosis")}</Table.Th>
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {medDiagnoses.data.map((d) => (
                          <Table.Tr key={d.id}>
                            <Table.Td>{d.diagnosis_date}</Table.Td>
                            <Table.Td>
                              <Text fw={600} size="sm">
                                {d.title}
                              </Text>
                              {d.description ? (
                                <Text size="sm" c="dimmed" style={{ whiteSpace: "pre-wrap" }}>
                                  {d.description}
                                </Text>
                              ) : null}
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  ) : (
                    <Text size="sm" c="dimmed">
                      {t("patientDrawer.noDiagnoses")}
                    </Text>
                  )}
                  </Stack>
                </EntityDrawerFieldBlock>

                <EntityDrawerFieldBlock label={t("patientDrawer.files")}>
                  <Stack gap="sm">
                  {medicalDownloadError ? (
                    <Alert
                      color="red"
                      title={t("patientDrawer.downloadFailed")}
                      onClose={() => setMedicalDownloadError(null)}
                      withCloseButton
                    >
                      {medicalDownloadError}
                    </Alert>
                  ) : null}
                  <input
                    type="file"
                    onChange={(e) => setFileToUpload(e.target.files?.[0] ?? null)}
                    disabled={mode === "view"}
                  />
                  {mode !== "view" && (
                    <Group justify="flex-end">
                      <Button
                        onClick={async () => {
                          if (!fileToUpload) return;
                          try {
                            await uploadMedicalFile.mutateAsync({ file: fileToUpload });
                            setFileToUpload(null);
                          } catch {
                            /* error surface: uploadMedicalFile.isError below */
                          }
                        }}
                        loading={uploadMedicalFile.isPending}
                        disabled={!fileToUpload}
                      >
                        {t("patientDrawer.uploadFile")}
                      </Button>
                    </Group>
                  )}
                  {uploadMedicalFile.isError ? (
                    <QueryErrorAlert
                      error={uploadMedicalFile.error}
                      title={t("patientDrawer.saveFailed")}
                    />
                  ) : null}
                  {medFiles.isLoading ? (
                    <Skeleton height={80} />
                  ) : medFiles.data?.length ? (
                    <Table striped verticalSpacing="sm">
                      <Table.Thead>
                        <Table.Tr>
                          <Table.Th>{t("patientDrawer.file")}</Table.Th>
                          <Table.Th>{t("patientDrawer.type")}</Table.Th>
                          <Table.Th>{t("patientDrawer.size")}</Table.Th>
                          <Table.Th />
                        </Table.Tr>
                      </Table.Thead>
                      <Table.Tbody>
                        {medFiles.data.map((f) => (
                          <Table.Tr key={f.id}>
                            <Table.Td>{f.file_name}</Table.Td>
                            <Table.Td>{f.content_type}</Table.Td>
                            <Table.Td>{Math.round(f.size_bytes / 1024)} KB</Table.Td>
                            <Table.Td>
                              <Button
                                size="xs"
                                variant="light"
                                onClick={async () => {
                                  try {
                                    setMedicalDownloadError(null);
                                    const url = await fetchAdminPatientMedicalFileDownloadUrl({
                                      clinicId: currentClinicId,
                                      patientId,
                                      fileId: f.id,
                                    });
                                    window.open(url, "_blank", "noopener,noreferrer");
                                  } catch (e) {
                                    setMedicalDownloadError(
                                      e instanceof Error ? e.message : t("patientDrawer.unknownError")
                                    );
                                  }
                                }}
                              >
                                {t("patientDrawer.download")}
                              </Button>
                            </Table.Td>
                          </Table.Tr>
                        ))}
                      </Table.Tbody>
                    </Table>
                  ) : (
                    <Text size="sm" c="dimmed">
                      {t("patientDrawer.noFiles")}
                    </Text>
                  )}
                  </Stack>
                </EntityDrawerFieldBlock>

                {(medVisits.isError || medDiagnoses.isError || medFiles.isError) && (
                  <QueryErrorAlert
                    error={
                      (medVisits.isError && medVisits.error) ||
                      (medDiagnoses.isError && medDiagnoses.error) ||
                      (medFiles.isError && medFiles.error) ||
                      null
                    }
                    title={t("patientDrawer.chartLoadFailed")}
                  />
                )}
              </Stack>
          )}
          </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="comms" pt="md">
          <ScrollArea h={PATIENT_MODAL_TABS_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
            <Text size="sm" c="dimmed">
              {t("patientDrawer.commsHint")}
            </Text>
            {patient && (
              <Button
                component={Link}
                to={`/admin/omni-chat?patient_id=${patient.id}`}
                leftSection={<IconMessageCircle size={16} />}
                variant="light"
              >
                {t("patientDrawer.openInChat")}
              </Button>
            )}
          </Stack>
                  </ScrollArea>
        </Tabs.Panel>
      </Tabs>
    </>
  );

  if (presentation === "modal") {
    return (
      <GlassModal
        opened={opened}
        onClose={onClose}
        title={title}
        size="xl"
        padding="lg"
        styles={{
          content: { minHeight: 560 },
          body: { paddingTop: 12 },
          header: { marginBottom: 8, paddingBottom: 0 },
        }}
      >
        {inner}
      </GlassModal>
    );
  }

  return (
    <AdminDrawer
      position="right"
      size="lg"
      opened={opened}
      onClose={onClose}
      title={title}
      styles={{ body: { paddingTop: 0, minHeight: 560 } }}
    >
      {inner}
    </AdminDrawer>
  );
}
