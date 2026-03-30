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
} from "@mantine/core";
import type { ComboboxItem } from "@mantine/core";
import { useClipboard } from "@mantine/hooks";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import { useServiceConsumables } from "@/hooks/useErpInventory";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useAdminLoyaltySummaryByContact } from "@/hooks/useLoyalty";
import { useDoctors } from "@/hooks/useDoctors";
import { usePatchBookingAdmin } from "@/hooks";
import {
  AdminDataTableSurface,
  ADMIN_TABLE_PROPS,
  AdminDrawer,
  GlassModal,
} from "@/shared/ui";
import {
  EntityDrawerFieldBlock,
  EntityDrawerFooterBar,
} from "@/admin/components/entity/entityDrawerChrome";
import { useEffect, useState } from "react";
import { IconCalendarEvent } from "@tabler/icons-react";
import { bookingStatusSelectOptions } from "@/shared/bookingStatusMeta";

function looksLikeUuid(s: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(String(s).trim());
}

function displayPersonName(name: string | undefined, fallbackId: string): string {
  const n = (name ?? "").trim();
  if (n) return n;
  if (looksLikeUuid(fallbackId)) return "Имя неизвестно";
  return fallbackId;
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
  /** После PATCH (комментарий или статус) — синхронизировать запись в родителе */
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
  const { currentClinicId } = useAdminClinic();
  const patchBooking = usePatchBookingAdmin();
  const clipboard = useClipboard({ timeout: 2500 });
  const [notesDraft, setNotesDraft] = useState("");
  const timeStr = booking ? String(booking.appointment_time).slice(0, 5) : "";
  const { data: consumables } = useServiceConsumables(
    currentClinicId,
    booking?.service_id ?? null
  );
  const { data: patientSummary, isPending: patientSummaryLoading } = useAdminLoyaltySummaryByContact(
    booking?.patient_id ?? null
  );
  const { data: doctors } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
    is_active: true,
  });
  const doctor = booking ? doctors?.find((d) => d.id === booking.doctor_id) : null;

  useEffect(() => {
    if (booking) setNotesDraft(booking.notes ?? "");
  }, [booking?.id, booking?.notes]);

  if (!booking) return null;

  /** Swiss Slate / Ink — `DESIGN_TOKENS_85_PLUS` + playbook Step 4 (modal shell convergence). */
  const shellProps = {
    opened,
    onClose,
    title: "Запись",
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

  const tabs = (
    <Box>
      <Tabs defaultValue="details" variant="outline" color="brand" keepMounted styles={bookingTabsStyles}>
        <Tabs.List grow>
          <Tabs.Tab value="details">Детали</Tabs.Tab>
          <Tabs.Tab value="services">Услуги и чек</Tabs.Tab>
          <Tabs.Tab value="consumables">Расходники</Tabs.Tab>
          <Tabs.Tab value="tasks">Задачи</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="details">
          <ScrollArea h={BOOKING_MODAL_TABS_SCROLL_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
            {!editing ? (
              <>
                <EntityDrawerFieldBlock label="Пациент">
                  <HoverCard openDelay={300} width={280} shadow="md" withinPortal>
                    <HoverCard.Target>
                      <Anchor
                        component={Link}
                        to={patientCardHref}
                        underline="hover"
                        fw={500}
                        c="brand.6"
                      >
                        {patientSummaryLoading && !patientName?.trim() ? (
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
                          <Text size="xs" c="dimmed">Телефон: {patientSummary.patient_phone}</Text>
                        )}
                        {patientSummary?.wallet && (
                          <Text size="xs" c="dimmed">
                            Баланс: {patientSummary.wallet.balance} {patientSummary.wallet.currency}
                          </Text>
                        )}
                        <Text size="xs" c="dimmed">След. визит — при API</Text>
                      </Stack>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label="Врач">
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
                        {doctor?.specialization && (
                          <Text size="xs" c="dimmed">Специализация: {doctor.specialization}</Text>
                        )}
                        <Text size="xs" c="dimmed">
                          Рабочие смены — во вкладке «Расписание» в карточке врача.
                        </Text>
                      </Stack>
                    </HoverCard.Dropdown>
                  </HoverCard>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label="Дата и время">
                  <Text size="sm" fw={500} c="gray.9">
                    {booking.appointment_date} {timeStr}
                  </Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label="Услуга">
                  <Text size="sm" fw={500} c="gray.9">
                    {serviceName && !looksLikeUuid(serviceName)
                      ? serviceName
                      : looksLikeUuid(booking.service_id)
                        ? "—"
                        : booking.service_id}
                  </Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label="Статус">
                  <Select
                    size="sm"
                    aria-label="Статус посещения"
                    data={bookingStatusSelectOptions(booking.status)}
                    value={booking.status}
                    disabled={
                      Boolean(editing) ||
                      patchBooking.isPending ||
                      bookingStatusSelectOptions(booking.status).length <= 1
                    }
                    onChange={(v) => {
                      if (!v || v === booking.status) return;
                      patchBooking.mutate(
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
                    {clipboard.copied ? "Ссылка скопирована" : "Скопировать ссылку посещения"}
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
                    label="Комментарий администратора"
                    placeholder="Краткая заметка для смены; в сетке виден значок"
                    minRows={2}
                    value={notesDraft}
                    onChange={(e) => setNotesDraft(e.currentTarget.value)}
                    disabled={Boolean(editing)}
                    aria-label="Комментарий администратора к записи"
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
                      Сохранить комментарий
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
                        Изменить дату / время / врача
                      </Button>
                    )}
                    {canCancel && onCancel && (
                      <Button
                        variant="subtle"
                        color="red"
                        onClick={() => onCancel(booking.id)}
                        loading={isCancelPending}
                      >
                        Отменить запись
                      </Button>
                    )}
                  </EntityDrawerFooterBar>
                )}
              </>
            ) : (
              <>
                <EntityDrawerFieldBlock label="Пациент">
                  <Text size="sm" fw={500} c="gray.9">
                    {displayPersonName(patientName, booking.patient_id)}
                  </Text>
                </EntityDrawerFieldBlock>
                <EntityDrawerFieldBlock label="Дата, время и врач">
                  <Stack gap="sm">
                    <TextInput
                      label="Дата"
                      type="date"
                      value={editDate ?? booking.appointment_date}
                      onChange={(e) => onEditDateChange?.(e.target.value || booking.appointment_date)}
                    />
                    <TextInput
                      label="Время"
                      type="time"
                      value={editTime ?? timeStr}
                      onChange={(e) => onEditTimeChange?.(e.target.value || timeStr)}
                    />
                    <Select
                      label="Врач"
                      data={doctorOptions}
                      value={editDoctorId ?? booking.doctor_id}
                      onChange={(v) => v && onEditDoctorIdChange?.(v)}
                      searchable
                      aria-label="Врач для записи"
                    />
                  </Stack>
                </EntityDrawerFieldBlock>
                <EntityDrawerFooterBar>
                  <Button
                    variant="outline"
                    color="gray"
                    onClick={onCancelEdit}
                  >
                    Отмена
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
                    Сохранить
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
                    <Table.Th>Услуга</Table.Th>
                    <Table.Th>Сумма</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  <Table.Tr>
                    <Table.Td>{serviceName ?? booking.service_id}</Table.Td>
                    <Table.Td>{booking.prepayment_amount ? `${booking.prepayment_amount} ₽` : "—"}</Table.Td>
                  </Table.Tr>
                </Table.Tbody>
              </Table>
            </AdminDataTableSurface>
            <Text size="sm" c="dimmed" style={{ lineHeight: 1.45 }}>
              Добавление нескольких услуг и чек — при расширении API.
            </Text>
          </Stack>
          </ScrollArea>
        </Tabs.Panel>

        <Tabs.Panel value="consumables">
          <ScrollArea h={BOOKING_MODAL_TABS_SCROLL_H} offsetScrollbars type="scroll">
          <Stack gap="sm">
          {!consumables ? (
            <Skeleton height={80} />
          ) : consumables.length === 0 ? (
            <Text size="sm" c="dimmed" style={{ lineHeight: 1.45 }}>
              Расходники по техкарте не заданы или загружаются.
            </Text>
          ) : (
            <AdminDataTableSurface>
              <Table striped {...ADMIN_TABLE_PROPS}>
                <Table.Thead>
                  <Table.Tr>
                    <Table.Th>Материал</Table.Th>
                    <Table.Th>Кол-во на услугу</Table.Th>
                  </Table.Tr>
                </Table.Thead>
                <Table.Tbody>
                  {consumables.map((c) => (
                    <Table.Tr key={c.id}>
                      <Table.Td>{c.product_id}</Table.Td>
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
                Задачи, привязанные к визиту — при наличии API.
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
