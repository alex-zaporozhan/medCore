import type { Booking } from "@/api/types";
import {
  useAdminBookings,
  useCreateAdminBooking,
  useRescheduleBookingAdmin,
  useCancelBookingAdmin,
} from "@/hooks/useAdminBookings";
import { useQueryClient } from "@tanstack/react-query";
import { useAdminSchedule } from "@/hooks/useDoctorSchedule";
import { useAdminWaitlist } from "@/hooks/useAdminWaitlist";
import { useDoctors } from "@/hooks/useDoctors";
import { useAdminClinicServices } from "@/hooks/useAdminClinicServices";
import { usePatients } from "@/hooks/usePatients";
import { ScheduleCalendarGrid } from "@/admin/components/ScheduleCalendarGrid";
import { WaitlistPanel } from "@/admin/components/WaitlistPanel";
import { EmptyStateHint } from "@/shared/emptyStateHint";
import { GlassModal } from "@/shared/ui/GlassModal";
import { DataSkeleton } from "@/shared/ui/DataSkeleton";
import {
  Button,
  Group,
  MultiSelect,
  Select,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import dayjs from "dayjs";
import { useState, useEffect, useRef, useMemo } from "react";
import type {
  CreateAdminBookingPayload,
  RescheduleBookingPayload,
} from "@/hooks/useAdminBookings";
import type { ComboboxItem } from "@mantine/core";
import { useAdminClinic } from "@/contexts/AdminClinicContext";

interface BookingEditFormProps {
  booking: Booking;
  doctorOptions: ComboboxItem[];
  onSave: (payload: RescheduleBookingPayload) => void;
  onCancel: () => void;
  isLoading: boolean;
}

function BookingEditForm({
  booking,
  doctorOptions,
  onSave,
  onCancel,
  isLoading,
}: BookingEditFormProps) {
  const [date, setDate] = useState(booking.appointment_date);
  const [time, setTime] = useState(String(booking.appointment_time).slice(0, 5));
  const [doctorId, setDoctorId] = useState(booking.doctor_id);

  const handleSubmit = () => {
    const timeForApi = time.length === 5 ? `${time}:00` : time;
    onSave({
      id: booking.id,
      doctor_id: doctorId,
      date,
      time: timeForApi,
    });
  };

  return (
    <Stack gap="sm">
      <TextInput
        label="Дата"
        type="date"
        value={date}
        onChange={(e) => setDate(e.target.value || date)}
      />
      <TextInput
        label="Время"
        type="time"
        value={time}
        onChange={(e) => setTime(e.target.value || time)}
      />
      <Select
        label="Специалист"
        data={doctorOptions}
        value={doctorId}
        onChange={(v) => v && setDoctorId(v)}
        searchable
      />
      <Group justify="flex-end" mt="sm">
        <Button variant="subtle" onClick={onCancel}>
          Отмена
        </Button>
        <Button onClick={handleSubmit} loading={isLoading}>
          Сохранить
        </Button>
      </Group>
    </Stack>
  );
}

interface ScheduleCreateBookingFormProps {
  date: string;
  time: string;
  doctorId: string;
  doctorName: string;
  displayRole?: string;
  clinicId: string;
  servicesOptions: ComboboxItem[];
  onClose: () => void;
  onCreate: (payload: CreateAdminBookingPayload) => void;
}

function ScheduleCreateBookingForm({
  date,
  time,
  doctorId,
  doctorName,
  displayRole,
  clinicId,
  servicesOptions,
  onClose,
  onCreate,
}: ScheduleCreateBookingFormProps) {
  const [patientId, setPatientId] = useState("");
  const [searchPhone, setSearchPhone] = useState("");
  const [searchFullName, setSearchFullName] = useState("");
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [notes, setNotes] = useState("");

  const { currentClinicId } = useAdminClinic();
  const { data: patients } = usePatients({
    clinic_id: currentClinicId ?? undefined,
    phone: searchPhone || undefined,
    full_name: searchFullName || undefined,
  });

  const patientOptions: ComboboxItem[] =
    patients?.map((p) => ({
      value: p.id,
      label: p.full_name ? `${p.phone} — ${p.full_name}` : p.phone,
    })) ?? [];

  const handleSubmit = () => {
    if (!patientId || !serviceId || !clinicId) return;
    const timeForApi = time.length === 5 ? `${time}:00` : time;
    onCreate({
      clinic_id: clinicId,
      patient_id: patientId,
      doctor_id: doctorId,
      service_id: serviceId,
      appointment_date: date,
      appointment_time: timeForApi,
      notes: notes || undefined,
    });
  };

  return (
    <Stack gap="sm">
      <Text size="sm" c="dimmed">
        {displayRole ?? "Специалист"}
      </Text>
      <Text size="sm">{doctorName}</Text>
      <Text size="sm" c="dimmed" mt="xs">
        Дата и время
      </Text>
      <Text size="sm">
        {date} {time}
      </Text>
      <Text size="sm" c="dimmed" mt="xs">
        Найдите пациента по телефону или ФИО
      </Text>
      <Group grow>
        <TextInput
          label="Телефон"
          placeholder="+7..."
          value={searchPhone}
          onChange={(e) => setSearchPhone(e.target.value)}
        />
        <TextInput
          label="ФИО"
          placeholder="Например, Иванов Иван"
          value={searchFullName}
          onChange={(e) => setSearchFullName(e.target.value)}
        />
      </Group>
      <Select
        label="Пациент"
        placeholder="Выберите пациента из списка"
        data={patientOptions}
        value={patientId}
        onChange={(value) => setPatientId(value ?? "")}
        searchable
        nothingFoundMessage={
          searchPhone || searchFullName
            ? "Пациенты не найдены. Проверьте данные или создайте нового пациента в разделе «Пациенты»."
            : "Начните вводить телефон или ФИО."
        }
      />
      <Select
        label="Услуга"
        placeholder="Выберите услугу"
        data={servicesOptions}
        value={serviceId}
        onChange={setServiceId}
        searchable
      />
      <TextInput
        label="Комментарий"
        placeholder="Необязательно"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
      />
      <Group justify="flex-end" mt="sm">
        <Button variant="subtle" onClick={onClose}>
          Отмена
        </Button>
        <Button onClick={handleSubmit} disabled={!patientId || !serviceId}>
          Создать запись
        </Button>
      </Group>
    </Stack>
  );
}

export default function SchedulePage() {
  const { currentClinicId, clinics } = useAdminClinic();
  const [dateStr, setDateStr] = useState(dayjs().format("YYYY-MM-DD"));
  const [doctorIds, setDoctorIds] = useState<string[]>([]);
  const { data: doctors, isLoading: doctorsLoading } = useDoctors({
    clinic_id: currentClinicId ?? undefined,
  });
  const {
    data: aggregatedSchedule,
    isLoading: scheduleLoading,
    isError,
    error,
  } = useAdminSchedule(currentClinicId, doctorIds, dateStr);
  const { data: bookings } = useAdminBookings({
    date: dateStr,
  });
  const { data: waitlistEntries } = useAdminWaitlist(
    currentClinicId,
    doctorIds[0] ?? null,
    dateStr
  );
  const [selectedBooking, setSelectedBooking] = useState<Booking | null>(null);
  const [editingBooking, setEditingBooking] = useState<Booking | null>(null);
  const [pendingReschedule, setPendingReschedule] = useState<{
    bookingId: string;
    toDoctorId: string;
    date: string;
    time: string;
  } | null>(null);
  const [pendingCancelBookingId, setPendingCancelBookingId] = useState<string | null>(null);
  const rescheduleMutation = useRescheduleBookingAdmin();
  const queryClient = useQueryClient();
  const cancelBookingMutation = useCancelBookingAdmin();
  const [createSlot, setCreateSlot] = useState<{ doctorId: string; time: string } | null>(null);
  const { data: adminServices } = useAdminClinicServices(currentClinicId);
  const createAdminBooking = useCreateAdminBooking();
  const { data: patientsList } = usePatients({
    clinic_id: currentClinicId ?? undefined,
    limit: 500,
  });

  const patientNameMap = useMemo(() => {
    if (!patientsList) return undefined;
    const map: Record<string, string> = {};
    for (const p of patientsList) {
      map[p.id] = p.full_name?.trim() ? p.full_name : p.phone;
    }
    return map;
  }, [patientsList]);

  const serviceNameMap = useMemo(() => {
    if (!adminServices) return undefined;
    const map: Record<string, string> = {};
    for (const item of adminServices) {
      map[item.service.id] = item.service.name;
    }
    return map;
  }, [adminServices]);

  const rescheduleConfirmText = useMemo(() => {
    if (!pendingReschedule || !bookings || !patientNameMap || !doctors) return null;
    const booking = bookings.find((b) => b.id === pendingReschedule.bookingId);
    if (!booking) return null;
    const clientName = patientNameMap[booking.patient_id] ?? booking.patient_id;
    const toDoctor = doctors.find((d) => d.id === pendingReschedule.toDoctorId);
    const toDoctorName = toDoctor?.full_name ?? "";
    const isDoctorChange = booking.doctor_id !== pendingReschedule.toDoctorId;
    const timeShort = String(pendingReschedule.time).slice(0, 5);
    if (isDoctorChange && toDoctorName) {
      return { clientName, date: pendingReschedule.date, time: timeShort, toDoctorName, isDoctorChange: true };
    }
    return { clientName, date: pendingReschedule.date, time: timeShort, toDoctorName: "", isDoctorChange: false };
  }, [pendingReschedule, bookings, patientNameMap, doctors]);

  const doctorOptions =
    doctors?.map((d) => ({ value: d.id, label: d.full_name })) ?? [];
  const servicesOptions =
    adminServices?.map((item) => {
      const basePrice = item.service.base_price ?? item.service.price;
      const effectivePrice = item.service.effective_price ?? basePrice;
      const hasDiscount = item.service.has_active_discount ?? false;
      const label = hasDiscount
        ? `${item.service.name} — ${basePrice} ₽ → ${effectivePrice} ₽`
        : `${item.service.name} — ${effectivePrice} ₽`;
      return {
        value: item.service.id,
        label,
      };
    }) ?? [];

  const gridDoctors =
    doctors?.filter((d) => doctorIds.includes(d.id)).map((d) => ({ id: d.id, name: d.full_name })) ?? [];

  /** В сетке показываем только активные записи — отменённые не отображаем и слот считается свободным */
  const bookingsForGrid = useMemo(
    () => bookings?.filter((b) => b.status !== "cancelled") ?? [],
    [bookings]
  );

  const hasInitializedDoctors = useRef(false);
  useEffect(() => {
    if (doctors && doctors.length > 0 && !hasInitializedDoctors.current) {
      hasInitializedDoctors.current = true;
      setDoctorIds(doctors.map((d) => d.id));
    }
  }, [doctors]);

  return (
    <Stack>
      <Title order={3}>Расписание</Title>
      {clinics.length > 1 && (
        <Text size="sm" c="dimmed">
          В другой клинике — другие врачи и услуги. Выберите клинику в шапке.
        </Text>
      )}
      <MultiSelect
        label="Врачи"
        placeholder="Выберите одного или нескольких врачей"
        data={doctorOptions}
        value={doctorIds}
        onChange={setDoctorIds}
        searchable
        clearable
      />
      <Group align="flex-end" gap="md">
        <TextInput
          label="Дата"
          type="date"
          value={dateStr}
          onChange={(e) => setDateStr(e.target.value || dayjs().format("YYYY-MM-DD"))}
        />
        <Group gap="xs" mb={4}>
          <Button
            size="xs"
            variant="light"
            onClick={() =>
              setDateStr(dayjs(dateStr).subtract(1, "day").format("YYYY-MM-DD"))
            }
          >
            Вчера
          </Button>
          <Button size="xs" variant="light" onClick={() => setDateStr(dayjs().format("YYYY-MM-DD"))}>
            Сегодня
          </Button>
          <Button
            size="xs"
            variant="light"
            onClick={() =>
              setDateStr(dayjs(dateStr).add(1, "day").format("YYYY-MM-DD"))
            }
          >
            Завтра
          </Button>
        </Group>
      </Group>

      {doctorsLoading && <DataSkeleton lines={3} />}
      {doctorIds.length > 0 && scheduleLoading && <DataSkeleton lines={6} />}
      {doctorIds.length > 0 && isError && (
        <Text c="red">{error instanceof Error ? error.message : "Ошибка"}</Text>
      )}
      {doctorIds.length === 0 && (
        <EmptyStateHint title="Выберите врачей" subtitle="Выберите одного или нескольких врачей для отображения сетки расписания." />
      )}
      {aggregatedSchedule &&
        aggregatedSchedule.times.length > 0 &&
        doctorIds.length > 0 && (
          <Stack gap="lg">
            <ScheduleCalendarGrid
              doctors={gridDoctors}
              date={aggregatedSchedule.date}
              times={aggregatedSchedule.times.map((t) => String(t).slice(0, 5))}
              byDoctor={aggregatedSchedule.by_doctor}
              bookings={bookingsForGrid}
              patientNameMap={patientNameMap}
              serviceNameMap={serviceNameMap}
              onBookingClick={(booking) => setSelectedBooking(booking)}
              onReschedule={({ bookingId, toDoctorId, date: d, time: t }) => {
                setPendingReschedule({ bookingId, toDoctorId, date: d, time: t });
              }}
              onEmptySlotClick={({ doctorId, time }) =>
                setCreateSlot({ doctorId, time })
              }
            />
            <WaitlistPanel
              clinicId={currentClinicId}
              doctorId={doctorIds[0]}
              date={dateStr}
              entries={waitlistEntries}
              patientNameMap={patientNameMap}
            />
          </Stack>
        )}
      {aggregatedSchedule &&
        aggregatedSchedule.times.length === 0 &&
        doctorIds.length > 0 && (
          <EmptyStateHint title="Нет слотов на эту дату" />
        )}

      <GlassModal
        opened={pendingReschedule !== null}
        onClose={() => setPendingReschedule(null)}
        title="Подтверждение переноса"
      >
        <Stack gap="md">
          {rescheduleConfirmText ? (
            <Text size="sm">
              {rescheduleConfirmText.isDoctorChange && rescheduleConfirmText.toDoctorName
                ? `Вы действительно хотите перенести запись ${rescheduleConfirmText.clientName} на ${rescheduleConfirmText.date} ${rescheduleConfirmText.time} к ${rescheduleConfirmText.toDoctorName}?`
                : `Вы действительно хотите перенести запись ${rescheduleConfirmText.clientName} на ${rescheduleConfirmText.date} ${rescheduleConfirmText.time}?`}
            </Text>
          ) : (
            <Text size="sm" c="dimmed">
              Данные записи загружаются…
            </Text>
          )}
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={() => setPendingReschedule(null)}>
              Отмена
            </Button>
            <Button
              loading={rescheduleMutation.isPending}
              disabled={!rescheduleConfirmText}
              onClick={() => {
                if (!pendingReschedule || !rescheduleConfirmText) return;
                rescheduleMutation.mutate(
                  {
                    id: pendingReschedule.bookingId,
                    doctor_id: pendingReschedule.toDoctorId,
                    date: pendingReschedule.date,
                    time: pendingReschedule.time,
                  },
                  {
                    onSuccess: () => setPendingReschedule(null),
                  }
                );
              }}
            >
              Перенести
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        opened={pendingCancelBookingId !== null}
        onClose={() => setPendingCancelBookingId(null)}
        title="Подтверждение отмены"
      >
        <Stack gap="md">
          <Text size="sm">
            Вы действительно хотите отменить запись?
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={() => setPendingCancelBookingId(null)}>
              Нет
            </Button>
            <Button
              color="red"
              loading={cancelBookingMutation.isPending}
              onClick={() => {
                if (!pendingCancelBookingId) return;
                const idToCancel = pendingCancelBookingId;
                cancelBookingMutation.mutate(idToCancel, {
                  onSuccess: async () => {
                    setPendingCancelBookingId(null);
                    setSelectedBooking(null);
                    setEditingBooking(null);
                    await Promise.all([
                      queryClient.refetchQueries({ queryKey: ["admin-bookings"] }),
                      queryClient.refetchQueries({ queryKey: ["admin-schedule"] }),
                    ]);
                  },
                  onSettled: () => {
                    setPendingCancelBookingId(null);
                  },
                });
              }}
            >
              Отменить запись
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <GlassModal
        opened={selectedBooking !== null}
        onClose={() => { setSelectedBooking(null); setEditingBooking(null); }}
        title={editingBooking ? "Изменить запись" : "Детали записи"}
      >
        {selectedBooking && !editingBooking && (
          <Stack gap="xs">
            <Text size="sm" c="dimmed">
              ФИО пациента
            </Text>
            <Text size="md">
              {patientNameMap?.[selectedBooking.patient_id] ?? selectedBooking.patient_id}
            </Text>
            <Text size="sm" c="dimmed" mt="sm">
              {doctors?.find((d) => d.id === selectedBooking.doctor_id)?.display_role ?? "Специалист"}
            </Text>
            <Text size="md">
              {doctors?.find((d) => d.id === selectedBooking.doctor_id)?.full_name ?? selectedBooking.doctor_id}
            </Text>
            <Text size="sm" c="dimmed" mt="sm">
              Дата посещения и время
            </Text>
            <Text size="md">
              {selectedBooking.appointment_date}{" "}
              {String(selectedBooking.appointment_time).slice(0, 5)}
            </Text>
            <Text size="sm" c="dimmed" mt="sm">
              Услуга
            </Text>
            <Text size="md">
              {serviceNameMap?.[selectedBooking.service_id] ?? selectedBooking.service_id}
            </Text>
            <Text size="sm" c="dimmed" mt="sm">
              Статус
            </Text>
            <Text size="md">{selectedBooking.status}</Text>
            <Group mt="md" gap="sm">
              <Button
                variant="light"
                onClick={() => setEditingBooking(selectedBooking)}
              >
                Изменить дату/время/врача
              </Button>
              {(() => {
                const cancelledOrCompleted =
                  selectedBooking.status === "cancelled" ||
                  selectedBooking.status === "completed";
                const timeStr = String(selectedBooking.appointment_time).slice(0, 5);
                const slotDt = new Date(
                  selectedBooking.appointment_date + "T" + timeStr + ":00"
                );
                const isPastSlot = slotDt <= new Date();
                const canCancel = !cancelledOrCompleted && !isPastSlot;
                return canCancel ? (
                  <Button
                    variant="subtle"
                    color="red"
                    onClick={() => {
                      setPendingCancelBookingId(selectedBooking.id);
                      setSelectedBooking(null);
                    }}
                    loading={cancelBookingMutation.isPending}
                  >
                    Отменить запись
                  </Button>
                ) : null;
              })()}
            </Group>
          </Stack>
        )}
        {selectedBooking && editingBooking && (
          <BookingEditForm
            booking={editingBooking}
            doctorOptions={doctorOptions}
            onSave={(payload) => {
              rescheduleMutation.mutate(payload, {
                onSuccess: () => {
                  setEditingBooking(null);
                  setSelectedBooking(null);
                },
              });
            }}
            onCancel={() => setEditingBooking(null)}
            isLoading={rescheduleMutation.isPending}
          />
        )}
      </GlassModal>

      <GlassModal
        opened={createSlot !== null}
        onClose={() => setCreateSlot(null)}
        title="Новая запись"
      >
        {createSlot && (
          <ScheduleCreateBookingForm
            date={dateStr}
            time={createSlot.time}
            doctorId={createSlot.doctorId}
            doctorName={
              doctors?.find((d) => d.id === createSlot.doctorId)?.full_name ?? ""
            }
            displayRole={doctors?.find((d) => d.id === createSlot.doctorId)?.display_role}
            clinicId={currentClinicId ?? ""}
            servicesOptions={servicesOptions}
            onClose={() => setCreateSlot(null)}
            onCreate={(payload) =>
              createAdminBooking.mutate(payload, {
                onSuccess: () => {
                  setCreateSlot(null);
                },
              })
            }
          />
        )}
      </GlassModal>
    </Stack>
  );
}
