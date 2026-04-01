import type { Booking } from "@/api/types";
import {
  useAdminBookings,
  useCreateAdminBooking,
  useRescheduleBookingAdmin,
  useCancelBookingAdmin,
  useAdminSchedule,
  useAdminWaitlist,
  useDoctors,
  useAdminClinicServices,
  usePatients,
  usePatient,
  useDoctor,
  type CreateAdminBookingPayload,
} from "@/hooks";
import { useQueryClient } from "@tanstack/react-query";
import { ScheduleCalendarGrid } from "@/admin/components/ScheduleCalendarGrid";
import { WaitlistPanel } from "@/admin/components/WaitlistPanel";
import { BookingEntityDrawer } from "@/admin/components/entity/BookingEntityDrawer";
import { EmptyState, GlassModal, DataSkeleton, ContextBar, QueryErrorAlert, CompactMonthPicker } from "@/shared/ui";
import { PatientEntityDrawer } from "@/admin/components/entity/PatientEntityDrawer";
import { DoctorEntityDrawer } from "@/admin/components/entity/DoctorEntityDrawer";
import {
  ActionIcon,
  Box,
  Button,
  Group,
  MultiSelect,
  Popover,
  Select,
  Stack,
  Text,
  TextInput,
} from "@mantine/core";
import dayjs from "dayjs";
import { useState, useEffect, useRef, useMemo, type CSSProperties } from "react";
import { useSearchParams } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";
import type { ComboboxItem } from "@mantine/core";
import { IconCalendarEvent, IconChevronLeft, IconChevronRight, IconCalendar } from "@tabler/icons-react";
import { useAdminClinic } from "@/contexts/AdminClinicContext";
import { ClinicSelector } from "@/admin/components/ClinicSelector";
import { SEMANTIC } from "@/shared/semanticUi";

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
  const { currentClinicId, clinics, isClinicScopeLocked } = useAdminClinic();
  const [searchParams] = useSearchParams();
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
  const [editDate, setEditDate] = useState("");
  const [editTime, setEditTime] = useState("");
  const [editDoctorId, setEditDoctorId] = useState("");
  const [pendingCancelBookingId, setPendingCancelBookingId] = useState<string | null>(null);
  const rescheduleMutation = useRescheduleBookingAdmin();
  const queryClient = useQueryClient();
  const cancelBookingMutation = useCancelBookingAdmin();
  const [createSlot, setCreateSlot] = useState<{ doctorId: string; time: string } | null>(null);
  const [patientModalId, setPatientModalId] = useState<string | null>(null);
  const [doctorModalId, setDoctorModalId] = useState<string | null>(null);
  const [datePickerOpened, setDatePickerOpened] = useState(false);
  const [pickerMonth, setPickerMonth] = useState(() => dayjs().startOf("month"));
  const prevDateStrRef = useRef(dateStr);
  const [scheduleSlideSign, setScheduleSlideSign] = useState(1);
  const [pendingDragMove, setPendingDragMove] = useState<{
    bookingId: string;
    fromDoctorId: string;
    fromDate: string;
    fromTime: string;
    toDoctorId: string;
    toDate: string;
    toTime: string;
    patientLabel: string;
  } | null>(null);

  const { data: patientModalData } = usePatient(patientModalId);
  const { data: doctorModalData } = useDoctor(doctorModalId);
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

  const handleRescheduleDrag = (payload: { bookingId: string; toDoctorId: string; date: string; time: string }) => {
    const b = bookingsForGrid.find((x) => x.id === payload.bookingId);
    if (!b) return;
    const fromTime = String(b.appointment_time).slice(0, 5);
    const patientLabel = patientNameMap?.[b.patient_id] || b.patient_name || b.patient_id;
    setPendingDragMove({
      bookingId: payload.bookingId,
      fromDoctorId: b.doctor_id,
      fromDate: b.appointment_date,
      fromTime,
      toDoctorId: payload.toDoctorId,
      toDate: payload.date,
      toTime: payload.time,
      patientLabel: String(patientLabel).trim() || "Пациент",
    });
  };

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

  useEffect(() => {
    setPickerMonth(dayjs(dateStr).startOf("month"));
  }, [dateStr]);

  useEffect(() => {
    const prev = prevDateStrRef.current;
    if (dayjs(dateStr).isAfter(prev)) setScheduleSlideSign(1);
    else if (dayjs(dateStr).isBefore(prev)) setScheduleSlideSign(-1);
    prevDateStrRef.current = dateStr;
  }, [dateStr]);

  const hasInitializedDoctors = useRef(false);
  useEffect(() => {
    if (!doctors?.length) return;
    const d = searchParams.get("date");
    if (d) setDateStr(d);
    const doc = searchParams.get("doctor");
    if (doc) {
      const ids = doc
        .split(",")
        .filter(Boolean)
        .filter((id) => doctors.some((x) => x.id === id));
      if (ids.length) setDoctorIds(ids);
      return;
    }
    if (!hasInitializedDoctors.current) {
      hasInitializedDoctors.current = true;
      setDoctorIds(doctors.map((x) => x.id));
    }
  }, [doctors, searchParams]);

  useEffect(() => {
    const bid = searchParams.get("booking");
    if (!bid || !bookings?.length) return;
    const b = bookings.find((x) => x.id === bid);
    if (b) setSelectedBooking(b);
  }, [searchParams, bookings]);

  useEffect(() => {
    if (selectedBooking) {
      setEditDate(selectedBooking.appointment_date);
      setEditTime(String(selectedBooking.appointment_time).slice(0, 5));
      setEditDoctorId(selectedBooking.doctor_id);
    }
  }, [selectedBooking?.id]);

  const scheduleShareUrl = useMemo(() => {
    if (!selectedBooking || typeof window === "undefined") return null;
    const u = new URL(`${window.location.origin}${ROUTE_PATHS.admin.schedule}`);
    u.searchParams.set("date", selectedBooking.appointment_date);
    u.searchParams.set("doctor", selectedBooking.doctor_id);
    u.searchParams.set("booking", selectedBooking.id);
    return `${u.pathname}${u.search}`;
  }, [selectedBooking]);

  return (
    <Stack>
      <ContextBar
        title="Расписание"
        breadcrumbs={<ClinicSelector variant="compact" />}
      />
      {!isClinicScopeLocked && clinics.length > 1 && (
        <Text size="sm" c="dimmed">
          В другой клинике — другие врачи и услуги. Выберите клинику выше.
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
      <Stack gap="xs">
        <Text size="sm" fw={600}>
          Дата
        </Text>
        <Group align="center" gap="sm" wrap="wrap">
          <ActionIcon
            variant="light"
            size="lg"
            radius="md"
            color={SEMANTIC.dateNav.yesterday}
            aria-label="Предыдущий день"
            onClick={() => setDateStr(dayjs(dateStr).subtract(1, "day").format("YYYY-MM-DD"))}
            style={{ boxShadow: "var(--shadow-soft-sm)" }}
          >
            <IconChevronLeft size={20} stroke={1.5} />
          </ActionIcon>
          <Button
            size="xs"
            variant="light"
            color={SEMANTIC.dateNav.yesterday}
            onClick={() => setDateStr(dayjs(dateStr).subtract(1, "day").format("YYYY-MM-DD"))}
          >
            Вчера
          </Button>
          <Button
            size="xs"
            variant="filled"
            color={SEMANTIC.dateNav.today}
            onClick={() => setDateStr(dayjs().format("YYYY-MM-DD"))}
          >
            Сегодня
          </Button>
          <Button
            size="xs"
            variant="light"
            color={SEMANTIC.dateNav.tomorrow}
            onClick={() => setDateStr(dayjs(dateStr).add(1, "day").format("YYYY-MM-DD"))}
          >
            Завтра
          </Button>
          <ActionIcon
            variant="light"
            size="lg"
            radius="md"
            color={SEMANTIC.dateNav.tomorrow}
            aria-label="Следующий день"
            onClick={() => setDateStr(dayjs(dateStr).add(1, "day").format("YYYY-MM-DD"))}
            style={{ boxShadow: "var(--shadow-soft-sm)" }}
          >
            <IconChevronRight size={20} stroke={1.5} />
          </ActionIcon>
          <Popover
            position="bottom-start"
            shadow="md"
            opened={datePickerOpened}
            onChange={setDatePickerOpened}
            withArrow
            closeOnClickOutside
            withinPortal
          >
            <Popover.Target>
              <Button
                variant="default"
                size="sm"
                leftSection={<IconCalendar size={18} stroke={1.5} />}
                onClick={() => setDatePickerOpened((o) => !o)}
                style={{
                  boxShadow: "var(--shadow-soft-sm)",
                  border: "1px solid var(--input-border)",
                }}
              >
                {dayjs(dateStr).format("DD MMM YYYY")}
              </Button>
            </Popover.Target>
            <Popover.Dropdown p="sm">
              <CompactMonthPicker
                value={dateStr}
                onChange={(iso) => {
                  setDateStr(iso);
                  setDatePickerOpened(false);
                }}
                monthAnchor={pickerMonth}
                onMonthAnchorChange={setPickerMonth}
                size="compact"
              />
            </Popover.Dropdown>
          </Popover>
        </Group>
      </Stack>

      {doctorsLoading && <DataSkeleton lines={3} />}
      {doctorIds.length > 0 && scheduleLoading && <DataSkeleton lines={6} />}
      {doctorIds.length > 0 && isError && <QueryErrorAlert error={error} />}
      {doctorIds.length === 0 && (
        <EmptyState
          title="Выберите врачей"
          description="Выберите одного или нескольких врачей для отображения сетки расписания."
        />
      )}
      {aggregatedSchedule &&
        aggregatedSchedule.times.length > 0 &&
        doctorIds.length > 0 && (
          <Stack gap="lg">
            {bookingsForGrid.length === 0 && (
              <EmptyState
                title="Нет записей на эту дату"
                description="Создайте запись по кнопке ниже или добавьте пациента из листа ожидания."
                icon={<IconCalendarEvent size={64} stroke={1} color="var(--mantine-color-gray-4)" />}
                action={{
                  label: "Новая запись",
                  onClick: () => {
                    const firstDoctor = gridDoctors[0];
                    const firstTime = aggregatedSchedule?.times[0];
                    if (firstDoctor && firstTime)
                      setCreateSlot({ doctorId: firstDoctor.id, time: String(firstTime).slice(0, 5) });
                  },
                }}
              />
            )}
            <Box
              key={dateStr}
              className="schedule-calendar-day-enter"
              style={{ ["--schedule-slide" as string]: scheduleSlideSign } as CSSProperties}
            >
              <ScheduleCalendarGrid
                doctors={gridDoctors}
                date={aggregatedSchedule.date}
                times={aggregatedSchedule.times.map((t) => String(t).slice(0, 5))}
                byDoctor={aggregatedSchedule.by_doctor}
                bookings={bookingsForGrid}
                patientNameMap={patientNameMap}
                serviceNameMap={serviceNameMap}
                onBookingClick={(booking) => setSelectedBooking(booking)}
                onReschedule={handleRescheduleDrag}
                onEmptySlotClick={({ doctorId, time }) =>
                  setCreateSlot({ doctorId, time })
                }
                onPatientProfileClick={(b) => setPatientModalId(b.patient_id)}
                onDoctorHeaderClick={(id) => setDoctorModalId(id)}
              />
            </Box>
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
          <EmptyState
            title="Нет слотов на эту дату"
            description="На выбранную дату нет доступных слотов расписания."
          />
        )}

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

      <BookingEntityDrawer
        opened={selectedBooking !== null}
        onClose={() => {
          setSelectedBooking(null);
          setEditingBooking(null);
        }}
        booking={selectedBooking}
        doctorOptions={doctorOptions}
        doctorName={
          selectedBooking
            ? doctors?.find((d) => d.id === selectedBooking.doctor_id)?.full_name
            : undefined
        }
        patientName={
          selectedBooking ? patientNameMap?.[selectedBooking.patient_id] : undefined
        }
        serviceName={
          selectedBooking ? serviceNameMap?.[selectedBooking.service_id] : undefined
        }
        onReschedule={(payload) => {
          const timeForApi =
            payload.time.length === 5 ? `${payload.time}:00` : payload.time;
          rescheduleMutation.mutate(
            {
              id: payload.id,
              doctor_id: payload.doctor_id,
              date: payload.date,
              time: timeForApi,
            },
            {
              onSuccess: () => {
                setEditingBooking(null);
                setSelectedBooking(null);
              },
            }
          );
        }}
        onCancel={(id) => {
          setPendingCancelBookingId(id);
          setSelectedBooking(null);
        }}
        isReschedulePending={rescheduleMutation.isPending}
        isCancelPending={cancelBookingMutation.isPending}
        editing={editingBooking !== null}
        onStartEdit={() =>
          selectedBooking && setEditingBooking(selectedBooking)
        }
        onCancelEdit={() => setEditingBooking(null)}
        editDate={editDate || selectedBooking?.appointment_date}
        editTime={editTime || (selectedBooking ? String(selectedBooking.appointment_time).slice(0, 5) : "")}
        editDoctorId={editDoctorId || selectedBooking?.doctor_id}
        onEditDateChange={setEditDate}
        onEditTimeChange={setEditTime}
        onEditDoctorIdChange={setEditDoctorId}
        scheduleShareUrl={scheduleShareUrl}
        onBookingUpdated={(b) => setSelectedBooking(b)}
      />

      <GlassModal
        opened={pendingDragMove !== null}
        onClose={() => setPendingDragMove(null)}
        title="Подтверждение перемещения"
      >
        <Stack gap="md">
          <Text size="sm">
            Вы действительно хотите переместить запись{" "}
            <Text component="span" fw={700}>
              {pendingDragMove?.patientLabel ?? "Пациент"}
            </Text>{" "}
            с{" "}
            <Text component="span" fw={700}>
              {pendingDragMove ? `${pendingDragMove.fromDate} ${pendingDragMove.fromTime}` : ""}
            </Text>{" "}
            на{" "}
            <Text component="span" fw={700}>
              {pendingDragMove ? `${pendingDragMove.toDate} ${pendingDragMove.toTime}` : ""}
            </Text>
            ?
          </Text>
          <Group justify="flex-end" gap="sm">
            <Button variant="subtle" onClick={() => setPendingDragMove(null)} disabled={rescheduleMutation.isPending}>
              Нет
            </Button>
            <Button
              onClick={() => {
                if (!pendingDragMove) return;
                const timeForApi =
                  pendingDragMove.toTime.length === 5 ? `${pendingDragMove.toTime}:00` : pendingDragMove.toTime;
                rescheduleMutation.mutate(
                  {
                    id: pendingDragMove.bookingId,
                    doctor_id: pendingDragMove.toDoctorId,
                    date: pendingDragMove.toDate,
                    time: timeForApi,
                  },
                  {
                    onSettled: () => setPendingDragMove(null),
                  }
                );
              }}
              loading={rescheduleMutation.isPending}
            >
              Да
            </Button>
          </Group>
        </Stack>
      </GlassModal>

      <PatientEntityDrawer
        opened={patientModalId !== null && Boolean(patientModalData)}
        onClose={() => setPatientModalId(null)}
        patient={patientModalData ?? null}
        mode="view"
        presentation="modal"
      />

      <DoctorEntityDrawer
        opened={doctorModalId !== null && Boolean(doctorModalData)}
        onClose={() => setDoctorModalId(null)}
        doctor={doctorModalData ?? null}
        mode="view"
        initialTab="schedule"
        presentation="modal"
      />

      <GlassModal
        opened={createSlot !== null}
        onClose={() => setCreateSlot(null)}
        title="Новая запись"
        size="lg"
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
