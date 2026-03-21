import type { Booking } from "@/api/types";
import {
  useAdminBookings,
  useCancelBookingAdmin,
  useCompleteBookingAdmin,
  useCheckoutInfo,
} from "@/hooks/useAdminBookings";
import { useDoctors } from "@/hooks/useDoctors";
import { usePatients } from "@/hooks/usePatients";
import { useServices } from "@/hooks/useServices";
import { useAdminFormTemplates, useSendFormLink } from "@/hooks";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { AdminDrawer, GlassModal, DataSkeleton, ContextBar, QueryErrorAlert } from "@/shared/ui";
import { BookingEntityDrawer } from "@/admin/components/entity/BookingEntityDrawer";
import {
  ActionIcon,
  Button,
  Card,
  Group,
  HoverCard,
  Menu,
  Paper,
  Select,
  Skeleton,
  Stack,
  Table,
  Text,
  TextInput,
} from "@mantine/core";
import { IconDotsVertical } from "@tabler/icons-react";
import dayjs from "dayjs";
import { useState } from "react";
import { Link } from "react-router-dom";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { ROUTE_PATHS } from "@/routePaths";

const EMPTY_DB_HINT =
  "Если ошибка из-за отсутствия данных в базе — добавьте клинику, врачей или пациентов в соответствующих разделах.";

const STATUS_OPTIONS = [
  { value: "", label: "Любой" },
  { value: "pending", label: "Ожидает" },
  { value: "confirmed", label: "Подтверждено" },
  { value: "completed", label: "Оказано" },
  { value: "cancelled", label: "Отменено" },
  { value: "no_show", label: "Неявка" },
];

export default function AdminBookingsPage() {
  const [doctorId, setDoctorId] = useState<string | null>(null);
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [status, setStatus] = useState<string | null>(null);
  const [patientPhone, setPatientPhone] = useState("");
  const [pendingCancelId, setPendingCancelId] = useState<string | null>(null);
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [sendFormBooking, setSendFormBooking] = useState<{ patient_id: string; booking_id: string } | null>(null);
  const [formTemplateId, setFormTemplateId] = useState<string | null>(null);
  const [formSendVia, setFormSendVia] = useState<"whatsapp" | "sms" | "copy_only">("copy_only");
  const [checkoutBookingId, setCheckoutBookingId] = useState<string | null>(null);
  const { data: formTemplates } = useAdminFormTemplates();
  const sendFormLink = useSendFormLink();
  const { data: checkoutInfo, isLoading: checkoutInfoLoading } = useCheckoutInfo(checkoutBookingId);

  const { currentClinicId, clinics } = useAdminClinic();
  const currentClinicLabel = clinics.find((c) => c.id === currentClinicId)?.name ?? null;

  const { data: doctors } = useDoctors({ clinic_id: currentClinicId ?? undefined });
  const { data: patients } = usePatients({});
  const { data: services } = useServices({});
  const doctorOptions =
    doctors?.map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  const handleCancelBooking = (id: string) => {
    setSelectedBooking(null);
    setPendingCancelId(id);
  };

  const filters = {
    doctor_id: doctorId ?? undefined,
    date,
    status: status ?? undefined,
    patient_phone: patientPhone || undefined,
  };

  const { data: bookings, isLoading, isError, error } = useAdminBookings(filters);
  const cancelMutation = useCancelBookingAdmin();
  const completeMutation = useCompleteBookingAdmin();

  const errMessage = isError && error instanceof Error ? error.message : "";
  const isEmptyDb = errMessage.includes("клиник") || errMessage.includes("клиники");

  return (
    <Stack>
      <ContextBar
        title="Записи"
        breadcrumbs={
          currentClinicLabel ? (
            <Text size="sm" c="dimmed">
              Клиника: {currentClinicLabel}
            </Text>
          ) : null
        }
        actions={<Button component={Link} to={ROUTE_PATHS.admin.schedule}>Новая запись</Button>}
      />
      <Select
        label="Врач"
        placeholder="Выберите врача"
        data={doctorOptions}
        value={doctorId}
        onChange={setDoctorId}
        searchable
        clearable
      />
      <TextInput
        label="Дата"
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value || dayjs().format("YYYY-MM-DD"))}
      />
      <Select
        label="Статус"
        data={STATUS_OPTIONS}
        value={status ?? ""}
        onChange={(v) => setStatus(v || null)}
      />
      <TextInput
        label="Телефон пациента"
        placeholder="+7..."
        value={patientPhone}
        onChange={(e) => setPatientPhone(e.target.value)}
      />

      {isLoading && <DataSkeleton lines={8} />}
      {isError && (
        <>
          <QueryErrorAlert error={error} />
          {isEmptyDb && (
            <Text size="sm" c="dimmed">
              {EMPTY_DB_HINT}
            </Text>
          )}
        </>
      )}
      {!isLoading && !isError && bookings?.length === 0 && (
        <EmptyStateHint title="Нет записей по выбранным фильтрам" />
      )}
      {!isLoading && !isError && bookings && bookings.length > 0 && (
        <Table striped verticalSpacing="sm">
          <Table.Thead>
            <Table.Tr>
              <Table.Th>Дата</Table.Th>
              <Table.Th>Время</Table.Th>
              <Table.Th>Врач</Table.Th>
              <Table.Th>Пациент</Table.Th>
              <Table.Th>Услуга</Table.Th>
              <Table.Th>Статус</Table.Th>
              <Table.Th>Действия</Table.Th>
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {bookings.map((b) => {
              const doctor = doctors?.find((d) => d.id === b.doctor_id);
              const patient = patients?.find((p) => p.id === b.patient_id);
              const service = services?.find((s) => s.id === b.service_id);
              const patientLabel = patient
                ? [patient.phone, patient.full_name].filter(Boolean).join(" — ") || patient.phone
                : "—";
              return (
              <Table.Tr
                key={b.id}
                style={{ cursor: "pointer" }}
                onClick={() => setSelectedBooking(b)}
              >
                <Table.Td>{b.appointment_date}</Table.Td>
                <Table.Td>{typeof b.appointment_time === "string" ? b.appointment_time.slice(0, 5) : b.appointment_time}</Table.Td>
                <Table.Td>
                  {doctor ? (
                    <HoverCard openDelay={300} width={240} shadow="md">
                      <HoverCard.Target>
                        <Text span style={{ cursor: "default" }}>
                          {doctor.display_role ? `${doctor.display_role} ${doctor.full_name}` : doctor.full_name}
                        </Text>
                      </HoverCard.Target>
                      <HoverCard.Dropdown>
                        <Stack gap={4}>
                          <Text size="sm" fw={500}>{doctor.full_name}</Text>
                          {doctor.display_role && <Text size="xs" c="dimmed">Роль: {doctor.display_role}</Text>}
                          <Text size="xs" c="dimmed">Данные по запросу</Text>
                        </Stack>
                      </HoverCard.Dropdown>
                    </HoverCard>
                  ) : "—"}
                </Table.Td>
                <Table.Td>
                  {patient ? (
                    <HoverCard openDelay={300} width={240} shadow="md">
                      <HoverCard.Target>
                        <Text span style={{ cursor: "default" }}>{patientLabel}</Text>
                      </HoverCard.Target>
                      <HoverCard.Dropdown>
                        <Stack gap={4}>
                          <Text size="sm" fw={500}>{patient.full_name ?? patient.phone}</Text>
                          <Text size="xs" c="dimmed">Телефон: {patient.phone}</Text>
                          {patient.email && <Text size="xs" c="dimmed">Email: {patient.email}</Text>}
                          <Text size="xs" c="dimmed">Данные по запросу</Text>
                        </Stack>
                      </HoverCard.Dropdown>
                    </HoverCard>
                  ) : patientLabel}
                </Table.Td>
                <Table.Td>{service?.name ?? "—"}</Table.Td>
                <Table.Td>{b.status}</Table.Td>
                <Table.Td onClick={(e) => e.stopPropagation()}>
                  <Menu position="bottom-end" withArrow>
                    <Menu.Target>
                      <ActionIcon variant="subtle" size="sm" aria-label="Действия">
                        <IconDotsVertical size={16} />
                      </ActionIcon>
                    </Menu.Target>
                    <Menu.Dropdown>
                      <Menu.Item onClick={() => setSelectedBooking(b)}>
                        Открыть карточку
                      </Menu.Item>
                      <Menu.Item component={Link} to={`/admin/schedule?date=${b.appointment_date}`}>
                        Редактировать (расписание)
                      </Menu.Item>
                      <Menu.Item
                        onClick={() => {
                          setSendFormBooking({ patient_id: b.patient_id, booking_id: b.id });
                          setFormTemplateId(null);
                          setFormSendVia("copy_only");
                        }}
                      >
                        Отправить форму
                      </Menu.Item>
                      {b.status !== "cancelled" && b.status !== "completed" && (() => {
                        const timeStr = String(b.appointment_time).slice(0, 5);
                        const slotDt = new Date(b.appointment_date + "T" + timeStr + ":00");
                        const isPastSlot = slotDt <= new Date();
                        return (
                          <>
                            {!isPastSlot && (
                              <Menu.Item
                                color="red"
                                onClick={(e) => { e.stopPropagation(); setSelectedBooking(null); setPendingCancelId(b.id); }}
                              >
                                Отменить
                              </Menu.Item>
                            )}
                            <Menu.Item
                              onClick={(e) => {
                                e.stopPropagation();
                                setCheckoutBookingId(b.id);
                              }}
                            >
                              Завершить
                            </Menu.Item>
                          </>
                        );
                      })()}
                    </Menu.Dropdown>
                  </Menu>
                </Table.Td>
              </Table.Tr>
              );
            })}
          </Table.Tbody>
        </Table>
      )}

      <BookingEntityDrawer
        opened={selectedBooking !== null}
        onClose={() => setSelectedBooking(null)}
        booking={selectedBooking}
        doctorOptions={doctorOptions}
        doctorName={
          selectedBooking
            ? doctors?.find((d) => d.id === selectedBooking.doctor_id)?.full_name
            : undefined
        }
        patientName={
          selectedBooking
            ? (() => {
                const p = patients?.find((x) => x.id === selectedBooking.patient_id);
                return p ? [p.phone, p.full_name].filter(Boolean).join(" — ") || p.phone : undefined;
              })()
            : undefined
        }
        serviceName={
          selectedBooking ? services?.find((s) => s.id === selectedBooking.service_id)?.name : undefined
        }
        onCancel={handleCancelBooking}
        isCancelPending={cancelMutation.isPending}
      />

      <GlassModal
        opened={pendingCancelId !== null}
        onClose={() => setPendingCancelId(null)}
        title="Подтверждение отмены"
      >
        <Stack gap="md">
          <Text size="sm">
            Вы действительно хотите отменить запись?
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={() => setPendingCancelId(null)}>
              Нет
            </Button>
            <Button
              color="red"
              loading={cancelMutation.isPending}
              onClick={() => {
                if (!pendingCancelId) return;
                cancelMutation.mutate(pendingCancelId, {
                  onSuccess: () => setPendingCancelId(null),
                });
              }}
            >
              Отменить запись
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <AdminDrawer
        opened={checkoutBookingId !== null}
        onClose={() => setCheckoutBookingId(null)}
        position="right"
        size="md"
        title="Чекаут — Завершить визит"
      >
        {checkoutBookingId && (
          <Stack gap="md">
            {checkoutInfoLoading ? (
              <Skeleton height={120} />
            ) : (
              <>
                <Text size="sm" c="dimmed">
                  Выберите способ завершения визита: списание с абонемента или оплата в кассу.
                </Text>
                {checkoutInfo?.eligible_subscriptions && checkoutInfo.eligible_subscriptions.length > 0 && (
                  <Stack gap="xs">
                    <Text size="sm" fw={600}>
                      Доступные абонементы
                    </Text>
                    {checkoutInfo.eligible_subscriptions.map((sub) => (
                      <Paper key={sub.customer_subscription_id} p="sm" withBorder radius="md">
                        <Group justify="space-between">
                          <Stack gap={2}>
                            <Text size="sm" fw={500}>
                              {sub.package_name}
                            </Text>
                            <Text size="xs" c="dimmed">
                              {sub.remaining_visits != null && `Остаток визитов: ${sub.remaining_visits}`}
                              {sub.remaining_amount != null && ` · Остаток: ${sub.remaining_amount} ₽`}
                            </Text>
                          </Stack>
                          <Button
                            size="xs"
                            variant="light"
                            loading={completeMutation.isPending}
                            onClick={() => {
                              completeMutation.mutate(
                                {
                                  bookingId: checkoutBookingId,
                                  use_subscription_id: sub.customer_subscription_id,
                                },
                                {
                                  onSuccess: () => setCheckoutBookingId(null),
                                }
                              );
                            }}
                          >
                            Списать с абонемента
                          </Button>
                        </Group>
                      </Paper>
                    ))}
                  </Stack>
                )}
                <Card withBorder p="sm">
                  <Group justify="space-between">
                    <Text size="sm">
                      Оплата в кассу (без списания с пакета)
                    </Text>
                    <Button
                      size="xs"
                      variant="filled"
                      loading={completeMutation.isPending}
                      onClick={() => {
                        completeMutation.mutate(
                          { bookingId: checkoutBookingId, use_subscription_id: null },
                          { onSuccess: () => setCheckoutBookingId(null) }
                        );
                      }}
                    >
                      Завершить и оплатить в кассу
                    </Button>
                  </Group>
                </Card>
                {completeMutation.isError && (
                  <QueryErrorAlert
                    error={completeMutation.error}
                    title="Не удалось завершить визит"
                  />
                )}
                <Group justify="flex-end">
                  <Button variant="subtle" onClick={() => setCheckoutBookingId(null)}>
                    Отмена
                  </Button>
                </Group>
              </>
            )}
          </Stack>
        )}
      </AdminDrawer>

      <AdminDrawer
        opened={sendFormBooking !== null}
        onClose={() => { setSendFormBooking(null); setFormTemplateId(null); }}
        position="right"
        size="sm"
        title="Отправить форму"
      >
        {sendFormBooking && (
          <Stack gap="md">
            <Select
              label="Шаблон формы"
              placeholder="Выберите шаблон"
              data={(formTemplates ?? []).map((t) => ({ value: t.id, label: t.name }))}
              value={formTemplateId}
              onChange={(v) => setFormTemplateId(v)}
              searchable
            />
            <Select
              label="Куда отправить"
              data={[
                { value: "copy_only", label: "Скопировать ссылку" },
                { value: "whatsapp", label: "WhatsApp" },
                { value: "sms", label: "SMS" },
              ]}
              value={formSendVia}
              onChange={(v) => setFormSendVia((v as "whatsapp" | "sms" | "copy_only") || "copy_only")}
            />
            <Group justify="flex-end">
              <Button variant="default" onClick={() => setSendFormBooking(null)}>
                Отмена
              </Button>
              <Button
                onClick={() => {
                  sendFormLink.mutate(
                    {
                      patient_id: sendFormBooking.patient_id,
                      booking_id: sendFormBooking.booking_id,
                      template_id: formTemplateId!,
                      send_via: formSendVia,
                    },
                    {
                      onSuccess: (res) => {
                        if (res.sent) setSendFormBooking(null);
                        if (res.sent && formSendVia === "copy_only" && res.url) {
                          try { navigator.clipboard.writeText(res.url); } catch { /* ignore */ }
                        }
                      },
                    }
                  );
                }}
                loading={sendFormLink.isPending}
                disabled={!formTemplateId}
              >
                Отправить ссылку
              </Button>
            </Group>
          </Stack>
        )}
      </AdminDrawer>
    </Stack>
  );
}
