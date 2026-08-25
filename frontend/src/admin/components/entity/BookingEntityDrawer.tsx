import type { Booking } from "@/api/types";
import {
  Anchor,
  Box,
  Button,
  Group,
  Paper,
  HoverCard,
  Stack,
  Tabs,
  Text,
  TextInput,
  Textarea,
  Select,
  Table,
  Skeleton,
  ScrollArea,
  Badge,
} from "@mantine/core";
import type { ComboboxItem } from "@mantine/core";
import { useClipboard } from "@mantine/hooks";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import { useServiceConsumables } from "@/hooks/useErpInventory";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useAdminLoyaltySummaryByContact } from "@/hooks/useLoyalty";
import { useDoctors } from "@/hooks/useDoctors";
import { usePatchBookingAdmin, useSetBookingStatusAdmin } from "@/hooks";
import {
  AdminDataTableSurface,
  ADMIN_TABLE_PROPS,
  AdminDrawer,
  GlassModal,
  QueryErrorAlert,
} from "@/shared/ui";
import {
  EntityDrawerFieldBlock,
  EntityDrawerFooterBar,
} from "@/admin/components/entity/entityDrawerChrome";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { IconCalendarEvent } from "@tabler/icons-react";
import { bookingStatusSelectOptions } from "@/shared/bookingStatusMeta";
import { displayPersonName } from "@/shared/ui/personNameFallback";
import { doctorRoleLabel } from "@/shared/doctorRoleI18n";

function looksLikeUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(s).trim());
}

/** Высота области вкладок — фиксированная, чтобы модалка не прыгала при смене вкладки. */
const BOOKING_MODAL_TABS_SCROLL_H = 440;

export interface BookingEntityDrawerProps {
  /** По умолчанию центрированное модальное окно (единый стандарт админки). */
  presentation?: "modal" | "drawer";
  opened: boolean;
  onClose: () => void;
  booking: Booking | null;
  doctorOptions: ComboboxItem[];
  doctorName?: string;
  patientName?: string;
  serviceName?: string;
  onReschedule?: (payload: { id: string; doctor_id: string; date: string; time: string }) => void;
  onCancel?: (id: string) => void;
  isReschedulePending?: boolean;
  isCancelPending?: boolean;
  /** When true, show inline edit form in Details tab */
  editing?: boolean;
  onStartEdit?: () => void;
  onCancelEdit?: () => void;
  /** Controlled edit form state (date, time, doctor_id) */
  editDate?: string;
  editTime?: string;
  editDoctorId?: string;
  onEditDateChange?: (v: string) => void;
  onEditTimeChange?: (v: string) => void;
  onEditDoctorIdChange?: (v: string) => void;
  /** P2: полная ссылка на слот в расписании (для копирования) */
  scheduleShareUrl?: string | null;
  /** После PATCH комментария или PUT статуса — синхронизировать запись в родителе */
  onBookingUpdated?: (booking: Booking) => void;
}

export function BookingEntityDrawer({
  presentation = "modal",
  opened,
  onClose,
  booking,
  doctorOptions,
  doctorName,
  patientName,
  serviceName,
  onReschedule,
  onCancel,
  isReschedulePending,
  isCancelPending,
  editing,
  onStartEdit,
  onCancelEdit,
  editDate,
  editTime,
  editDoctorId,
  onEditDateChange,
  onEditTimeChange,
  onEditDoctorIdChange,
  scheduleShareUrl,
  onBookingUpdated,
}: BookingEntityDrawerProps) {
  const { t } = useTranslation("schedule");
  const { currentClinicId } = useAdminClinic();
  const patchBooking = usePatchBookingAdmin();
  const setBookingStatus = useSetBookingStatusAdmin();
  const clipboard = useClipboard({ timeout: 2500 });
  const [notesDraft, setNotesDraft] = useState("");
  const timeStr = booking ? String(booking.appointment_time).slice(0, 5) : "";
  const {
    data: consumables,
    isLoading: consumablesLoading,
    isError: consumablesError,
    error: consumablesErr,
  } = useServiceConsumables(currentClinicId, booking?.service_id ?? null);
  const {
    data: patientSummary,
    isLoading: patientSummaryLoading,
    isError: patientSummaryError,
  } = useAdminLoyaltySummaryByContact(booking?.patient_id ?? null);
  const { data: doctors } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
    is_active: true,
  });
  const doctor = booking ? doctors?.find((d) => d.id === booking.doctor_id) : null;

  useEffect(() => {
    if (booking) setNotesDraft(booking.notes ?? "");
    patchBooking.reset();
    setBookingStatus.reset();
    // Sync draft only on booking identity — refetch of the same notes must not wipe in-progress typing.
    // Reset mutations when the open booking changes (intentional narrow deps).
  }, [booking?.id]);

  if (!booking) return null;

  /** Swiss Slate / Ink — `DESIGN_TOKENS_85_PLUS` + playbook Step 4 (modal shell convergence). */
  const shellProps = {
    opened,
    onClose,
    title: t("drawer.title"),
    styles: {
      header: {
        borderBottom: "1px solid var(--mantine-color-gray-2)",
        marginBottom: 0,
        paddingBottom: "var(--mantine-spacing-sm)",
      },
      title: {
        fontWeight: 600,
        fontSize: "var(--mantine-font-size-lg)",
        color: "var(--mantine-color-gray-9)",
        letterSpacing: "-0.01em",
      },
      body: { paddingTop: 0, paddingBottom: "md" },
      content: { minHeight: 560 },
    } as const,
  };

  const bookingTabsStyles = {
    list: {
      borderBottom: "1px solid var(--mantine-color-gray-2)",
      gap: 0,
    },
    tab: {
      fontWeight: 500,
      fontSize: "var(--mantine-font-size-sm)",
      color: "var(--mantine-color-gray-6)",
    },
    panel: { paddingTop: "var(--mantine-spacing-md)" },
  } as const;

  const canCancel =
    booking.status !== "cancelled" &&
    booking.status !== "completed" &&
    new Date(booking.appointment_date + "T" + timeStr + ":00") > new Date();

  const patientCardHref = `${ROUTE_PATHS.admin.patients}?patient_id=${booking.patient_id}`;
  const doctorCardHref = `${ROUTE_PATHS.admin.doctors}?doctor_id=${booking.doctor_id}&doctor_tab=schedule`;

  const statusCfg = booking ? bookingStatusSelectOptions(booking.status).find((x) => x.value === booking.status) : null;

  const tabs = (
    <Box>
      <Tabs defaultValue="details" variant="outline" color="brand" keepMounted styles={bookingTabsStyles}>
        <Tabs.List grow>
          <Tabs.Tab value="details">{t("drawer.details")}</Tabs.Tab>
          <Tabs.Tab value="services">{t("drawer.services")}</Tabs.Tab>
          <Tabs.Tab value="consumables">{t("drawer.consumables")}</Tabs.Tab>
          <Tabs.Tab value="tasks">{t("drawer.tasks")}</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="details">
          <ScrollArea h={BOOKING_MODAL_TABS_SCROLL_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
            {(patchBooking.isError || setBookingStatus.isError) && (
              <QueryErrorAlert error={patchBooking.error ?? setBookingStatus.error} />
            )}
            {!editing ? (
              <>
                <Paper
                  p="sm"
                  radius="md"
                  withBorder
                  bg="white"
                  style={{
                    borderColor: "var(--mantine-color-gray-2)",
                    boxShadow: "0 1px 2px rgba(15, 20, 25, 0.04)",
                  }}
                >
                  <Group justify="space-between" align="flex-start" wrap="wrap" gap="sm">
                    <Stack gap={4} style={{ flex: 1, minWidth: 220 }}>
                      <Text size="xs" c="dimmed" fw={700}>
                        {t("drawer.summary")}
                      </Text>
                      <Text size="sm" fw={700} c="gray.9">
                        {displayPersonName(patientName, booking.patient_id)}
                      </Text>
                      <Text size="xs" c="dimmed">
                        {booking.appointment_date} {timeStr}
                        {serviceName && !looksLikeUuid(serviceName) ? ` · ${serviceName}` : ""}
                      </Text>
                    </Stack>
                    <Stack gap={6} style={{ alignItems: "flex-end" }}>
                      <Badge variant="light" color="gray">
                        {statusCfg?.label ?? t("drawer.status")}
                      </Badge>
                      {booking.notes?.trim() ? (
                        <Text size="xs" c="dimmed">
                          {t("drawer.hasAdminComment")}
                        </Text>
                      ) : null}
                    </Stack>
                  </Group>
                </Paper>
                <EntityDrawerFieldBlock label={t("drawer.patient")}>
                  <HoverCard openDelay={300} width={280} shadow="md" withinPortal>
                    <HoverCard.Target>
                      <Anchor
                        component={Link}
                        to={patientCardHref}
                        underline="hover"
                        fw={500}
                        c="brand.6"
                      >
                        {patientSummaryLoading && !patientSummaryError && !patientName?.trim() ? (
                          <Skeleton height={18} width={200} />
                        ) : (
                          displayPersonName(
                            patientSummary?.patient_full_name ?? patientName,
                            booking.patient_id
                          )
                        )}
                      </Anchor>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                      <Stack gap={4}>
                        <Text size="sm" fw={500} c="gray.9">
                          {patientSummary?.patient_full_name ??
                            displayPersonName(patientName, booking.patient_id)}
                        </Text>
                        {patientSummary?.patient_phone && (
                          <Text size="xs" c="dimmed">{t("drawer.phoneLine", { phone: patientSummary.patient_phone })}</Text>
                        )}
                        {patientSummary?.wallet && (
                          <Text size="xs" c="dimmed">
                            {t("drawer.balanceLine", {
                              balance: patientSummary.wallet.balance,
                              currency: patientSummary.wallet.currency,
                            })}
                          </Text>
                        )}
                        <Text size="xs" c="dimmed">{t("drawer.nextVisitApi")}</Text>
                      </Stack>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("drawer.doctor")}>
                  <HoverCard openDelay={300} width={280} shadow="md" withinPortal>
                    <HoverCard.Target>
                      <Anchor
                        component={Link}
                        to={doctorCardHref}
                        underline="hover"
                        fw={500}
                        c="brand.6"
                      >
                        {displayPersonName(doctorName ?? doctor?.full_name, booking.doctor_id)}
                      </Anchor>
                    </HoverCard.Target>
                    <HoverCard.Dropdown>
                      <Stack gap={4}>
                        <Text size="sm" fw={500} c="gray.9">
                          {displayPersonName(doctor?.full_name ?? doctorName, booking.doctor_id)}
                        </Text>
                        {doctor ? (
                          <Text size="xs" c="dimmed">
                            {t("drawer.specializationLine", { value: doctorRoleLabel(doctor) })}
                          </Text>
                        ) : null}
                        {doctor?.specialization?.trim() ? (
                          <Text size="xs" c="dimmed">
                            {doctor.specialization.trim()}
                          </Text>
                        ) : null}
                        <Text size="xs" c="dimmed">
                          {t("drawer.shiftsHint")}
                        </Text>
                      </Stack>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("drawer.dateTime")}>
                  <Text size="sm" fw={500} c="gray.9">
                    {booking.appointment_date} {timeStr}
                  </Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("drawer.service")}>
                  <Text size="sm" fw={500} c="gray.9">
                    {serviceName && !looksLikeUuid(serviceName)
                      ? serviceName
                      : looksLikeUuid(booking.service_id)
                        ? "—"
                        : booking.service_id}
                  </Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("drawer.status")}>
                  <Select
                    size="sm"
                    aria-label={t("drawer.visitStatus")}
                    data={bookingStatusSelectOptions(booking.status)}
                    value={booking.status}
                    disabled={
                      Boolean(editing) ||
                      patchBooking.isPending ||
                      setBookingStatus.isPending ||
                      bookingStatusSelectOptions(booking.status).length <= 1
                    }
                    onChange={(v) => {
                      if (!v || v === booking.status) return;
                      setBookingStatus.mutate(
                        { id: booking.id, status: v },
                        {
                          onSuccess: (updated) => {
                            onBookingUpdated?.(updated);
                          },
                        },
                      );
                    }}
                  />
                </EntityDrawerFieldBlock>
                {scheduleShareUrl ? (
                  <Button
                    size="sm"
                    variant="outline"
                    color="brand"
                    fullWidth
                    onClick={() => clipboard.copy(scheduleShareUrl)}
                  >
                    {clipboard.copied ? t("drawer.linkCopied") : t("drawer.copyVisitLink")}
                  </Button>
                ) : null}
                <Paper
                  p="sm"
                  radius="md"
                  withBorder
                  bg="white"
                  style={{
                    borderColor: "var(--mantine-color-gray-1)",
                    boxShadow: "0 1px 2px rgba(15, 20, 25, 0.04)",
                  }}
                >
                  <Textarea
                    label={t("drawer.adminComment")}
                    placeholder={t("drawer.adminCommentPlaceholder")}
                    minRows={2}
                    value={notesDraft}
                    onChange={(e) => setNotesDraft(e.currentTarget.value)}
                    disabled={Boolean(editing)}
                    aria-label={t("drawer.adminComment")}
                  />
                  <Group justify="flex-end" mt="xs">
                    <Button
                      size="sm"
                      variant="filled"
                      color="brand"
                      loading={patchBooking.isPending}
                      disabled={
                        Boolean(editing) ||
                        notesDraft === (booking.notes ?? "")
                      }
                      onClick={() =>
                        patchBooking.mutate(
                          {
                            id: booking.id,
                            notes: notesDraft.trim() ? notesDraft : null,
                          },
                          {
                            onSuccess: (updated) => {
                              onBookingUpdated?.(updated);
                            },
                          },
                        )
                      }
                    >
                      {t("drawer.saveComment")}
                    </Button>
                  </Group>
                </Paper>
                {(onStartEdit || (canCancel && onCancel)) && (
                  <EntityDrawerFooterBar>
                    {onStartEdit && (
                      <Button
                        variant="outline"
                        color="brand"
                        leftSection={<IconCalendarEvent size={18} stroke={1.5} />}
                        onClick={onStartEdit}
                      >
                        {t("drawer.changeSlot")}
                      </Button>
                    )}
                    {canCancel && onCancel && (
                      <Button
                        variant="subtle"
                        color="red"
                        onClick={() => onCancel(booking.id)}
                        loading={isCancelPending}
                      >
                        {t("drawer.cancelBooking")}
                      </Button>
                    )}
                  </EntityDrawerFooterBar>
                )}
              </>
            ) : (
              <>
                <EntityDrawerFieldBlock label={t("drawer.patient")}>
                  <Text size="sm" fw={500} c="gray.9">
                    {displayPersonName(patientName, booking.patient_id)}
                  </Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label={t("drawer.dateTimeDoctor")}>
                  <Stack gap="sm">
                    <TextInput
                      label={t("date")}
                      type="date"
                      value={editDate ?? booking.appointment_date}
                      onChange={(e) => onEditDateChange?.(e.target.value || booking.appointment_date)}
                    />
                    <TextInput
                      label={t("drawer.time")}
                      type="time"
                      value={editTime ?? timeStr}
                      onChange={(e) => onEditTimeChange?.(e.target.value || timeStr)}
                    />
                    <Select
                      label={t("drawer.doctor")}
                      data={doctorOptions}
                      value={editDoctorId ?? booking.doctor_id}
                      onChange={(v) => v && onEditDoctorIdChange?.(v)}
                      searchable
                      aria-label={t("drawer.doctorForBooking")}
                    />
                  </Stack>
                </EntityDrawerFieldBlock>
                <EntityDrawerFooterBar>
                  <Button
                    variant="outline"
                    color="gray"
                    onClick={onCancelEdit}
                  >
                    {t("drawer.cancel")}
                  </Button>
                  <Button
                    variant="filled"
                    color="brand"
                    onClick={() =>
                      onReschedule?.({
                        id: booking.id,
                        doctor_id: editDoctorId ?? booking.doctor_id,
                        date: editDate ?? booking.appointment_date,
                        time: (editTime ?? timeStr).length === 5 ? (editTime ?? timeStr) + ":00" : (editTime ?? timeStr),
                      })
                    }
                    loading={isReschedulePending}
                  >
                    {t("drawer.save")}
                  </Button>
                </EntityDrawerFooterBar>
              </>
            )}
          </Stack>
          </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="services">
          <ScrollArea h={BOOKING_MODAL_TABS_SCROLL_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
            <AdminDataTableSurface>
              <Table striped {...ADMIN_TABLE_PROPS}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("drawer.service")}</Table.Th>
                    <Table.Th>{t("drawer.amount")}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>
                      {serviceName && !looksLikeUuid(serviceName)
                        ? serviceName
                        : looksLikeUuid(booking.service_id)
                          ? "—"
                          : booking.service_id}
                    </Table.Td>
                    <Table.Td>{booking.prepayment_amount ? `${booking.prepayment_amount} ₽` : "—"}</Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </AdminDataTableSurface>
            <Text size="sm" c="dimmed" style={{ lineHeight: 1.45 }}>
              {t("drawer.multiServiceHint")}
            </Text>
          </Stack>
          </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="consumables">
          <ScrollArea h={BOOKING_MODAL_TABS_SCROLL_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
          {consumablesError ? (
            <QueryErrorAlert error={consumablesErr} />
          ) : consumablesLoading ? (
            <Skeleton height={80} />
          ) : !consumables?.length ? (
            <Text size="sm" c="dimmed" style={{ lineHeight: 1.45 }}>
              {t("drawer.noConsumables")}
            </Text>
          ) : (
            <AdminDataTableSurface>
              <Table striped {...ADMIN_TABLE_PROPS}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>{t("drawer.material")}</Table.Th>
                    <Table.Th>{t("drawer.qtyPerService")}</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {consumables.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td>
                        {looksLikeUuid(c.product_id) ? "—" : c.product_id}
                      </Table.Td>
                      <Table.Td>
                        {c.quantity_per_service} {c.unit}
                      </Table.Td>
                    </Table.Tr>
                  ))}
                </Table.Tbody>
              </Table>
            </AdminDataTableSurface>
          )}
          </Stack>
          </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="tasks">
          <ScrollArea h={BOOKING_MODAL_TABS_SCROLL_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
            <Paper
              p="md"
              radius="md"
              withBorder
              bg="white"
              style={{
                borderColor: "var(--mantine-color-gray-1)",
                boxShadow: "0 1px 2px rgba(15, 20, 25, 0.04)",
              }}
            >
              <Text size="sm" c="dimmed" style={{ lineHeight: 1.45 }}>
                {t("drawer.tasksHint")}
              </Text>
            </Paper>
          </Stack>
          </ScrollArea>
        </Tabs.Panel>
      </Tabs>
    </Box>
  );

  if (presentation === "drawer") {
    return (
      <AdminDrawer position="right" size="lg" {...shellProps}>
        {tabs}
      </AdminDrawer>
    );
  }

  return (
    <GlassModal size="xl" centered {...shellProps}>
      {tabs}
    </GlassModal>
  );
}
