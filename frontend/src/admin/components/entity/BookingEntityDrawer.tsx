import type { Booking } from "@/api/types";
import {
  Button,
  Drawer,
  Group,
  HoverCard,
  Stack,
  Tabs,
  Text,
  TextInput,
  Select,
  Table,
  Skeleton,
} from "@mantine/core";
import type { ComboboxItem } from "@mantine/core";
import { useServiceConsumables } from "@/hooks/useErpInventory";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { useAdminLoyaltySummaryByContact } from "@/hooks/useLoyalty";
import { useDoctors } from "@/hooks/useDoctors";

export interface BookingEntityDrawerProps {
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
}

export function BookingEntityDrawer({
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
}: BookingEntityDrawerProps) {
  const { currentClinicId } = useAdminClinic();
  const timeStr = booking ? String(booking.appointment_time).slice(0, 5) : "";
  const { data: consumables } = useServiceConsumables(
    currentClinicId,
    booking?.service_id ?? null
  );
  const { data: patientSummary } = useAdminLoyaltySummaryByContact(
    booking?.patient_id ?? null
  );
  const { data: doctors } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
    is_active: true,
  });
  const doctor = booking ? doctors?.find((d) => d.id === booking.doctor_id) : null;

  if (!booking) return null;

  const canCancel =
    booking.status !== "cancelled" &&
    booking.status !== "completed" &&
    new Date(booking.appointment_date + "T" + timeStr + ":00") > new Date();

  return (
    <Drawer
      position="right"
      size="lg"
      opened={opened}
      onClose={onClose}
      title="Запись"
      styles={{ body: { paddingTop: 0 } }}
    >
      <Tabs defaultValue="details">
        <Tabs.List>
          <Tabs.Tab value="details">Детали</Tabs.Tab>
          <Tabs.Tab value="services">Услуги и чек</Tabs.Tab>
          <Tabs.Tab value="consumables">Расходники</Tabs.Tab>
          <Tabs.Tab value="tasks">Задачи</Tabs.Tab>
        </Tabs.List>

        <Tabs.Panel value="details" pt="md">
          <Stack gap="sm">
            {!editing ? (
              <>
                <Text size="sm" c="dimmed">Пациент</Text>
                <HoverCard openDelay={300} width={260} shadow="md">
                  <HoverCard.Target>
                    <Text span style={{ cursor: "default" }}>
                      {patientName ?? booking.patient_id}
                    </Text>
                  </HoverCard.Target>
                  <HoverCard.Dropdown>
                    <Stack gap={4}>
                      <Text size="sm" fw={500}>
                        {patientSummary?.patient_full_name ?? patientName ?? booking.patient_id}
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
                <Text size="sm" c="dimmed">Врач</Text>
                <HoverCard openDelay={300} width={260} shadow="md">
                  <HoverCard.Target>
                    <Text span style={{ cursor: "default" }}>
                      {doctorName ?? doctor?.full_name ?? booking.doctor_id}
                    </Text>
                  </HoverCard.Target>
                  <HoverCard.Dropdown>
                    <Stack gap={4}>
                      <Text size="sm" fw={500}>
                        {doctor?.full_name ?? doctorName ?? booking.doctor_id}
                      </Text>
                      {doctor?.specialization && (
                        <Text size="xs" c="dimmed">Специализация: {doctor.specialization}</Text>
                      )}
                      <Text size="xs" c="dimmed">Данные по запросу</Text>
                    </Stack>
                  </HoverCard.Dropdown>
                </HoverCard>
                <Text size="sm" c="dimmed">Дата и время</Text>
                <Text>
                  {booking.appointment_date} {timeStr}
                </Text>
                <Text size="sm" c="dimmed">Услуга</Text>
                <Text>{serviceName ?? booking.service_id}</Text>
                <Text size="sm" c="dimmed">Статус</Text>
                <Text>{booking.status}</Text>
                {booking.notes && (
                  <>
                    <Text size="sm" c="dimmed">Комментарий</Text>
                    <Text size="sm">{booking.notes}</Text>
                  </>
                )}
                <Group mt="md" gap="sm">
                  {onStartEdit && (
                    <Button variant="light" onClick={onStartEdit}>
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
                </Group>
              </>
            ) : (
              <>
                <Text size="sm" c="dimmed">Пациент</Text>
                <Text>{patientName ?? booking.patient_id}</Text>
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
                />
                <Group mt="sm">
                  <Button
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
                  <Button variant="subtle" onClick={onCancelEdit}>
                    Отмена
                  </Button>
                </Group>
              </>
            )}
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="services" pt="md">
          <Stack gap="sm">
            <Table striped verticalSpacing="sm">
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
            <Text size="sm" c="dimmed">
              Добавление нескольких услуг и чек — при расширении API.
            </Text>
          </Stack>
        </Tabs.Panel>

        <Tabs.Panel value="consumables" pt="md">
          {!consumables ? (
            <Skeleton height={80} />
          ) : consumables.length === 0 ? (
            <Text size="sm" c="dimmed">
              Расходники по техкарте не заданы или загружаются.
            </Text>
          ) : (
            <Table striped verticalSpacing="sm">
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
          )}
        </Tabs.Panel>

        <Tabs.Panel value="tasks" pt="md">
          <Text size="sm" c="dimmed">
            Задачи, привязанные к визиту — при наличии API.
          </Text>
        </Tabs.Panel>
      </Tabs>
    </Drawer>
  );
}
