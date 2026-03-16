import { usePatientAuth } from "@/contexts/PatientAuthContext";
import {
  useCreatePatientBooking,
  useCreatePayment,
  useDoctorSchedule,
  useDoctors,
  usePublicClinicServices,
  useClinics,
} from "@/hooks";
import { Avatar, Button, Card, Group, Loader, Select, SimpleGrid, Stack, Stepper, Text, TextInput, Title } from "@mantine/core";
import dayjs from "dayjs";
import { useState } from "react";

export default function BookingWizardPage() {
  const { accessToken, patientId } = usePatientAuth();
  const [step, setStep] = useState(0);
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [doctorId, setDoctorId] = useState<string | null>(null);
  const [dateStr, setDateStr] = useState(dayjs().format("YYYY-MM-DD"));
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);

  const { data: clinics } = useClinics();
  const clinicId = (() => {
    const key = "app.selectedClinicId";
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem(key) : null;
    if (saved && clinics?.some((c) => c.id === saved)) return saved;
    return clinics?.[0]?.id ?? null;
  })();
  const { data: publicServices, isLoading: servicesLoading } = usePublicClinicServices(clinicId);
  const { data: doctors, isLoading: doctorsLoading } = useDoctors({
    clinic_id: clinicId ?? undefined,
    is_active: true,
  });
  const { data: schedule, isLoading: scheduleLoading } = useDoctorSchedule(doctorId, dateStr);

  const createBooking = useCreatePatientBooking(accessToken);
  const createPayment = useCreatePayment(accessToken);

  const currentClinic = clinics?.find((c) => c.id === clinicId) ?? null;
  const prepaymentEnabled = !!currentClinic?.prepayment_enabled;

  const selectedService = publicServices?.find((s) => s.id === serviceId);
  const serviceOptions =
    publicServices?.map((s) => {
      const basePrice = s.base_price ?? s.price;
      const effectivePrice = s.effective_price ?? basePrice;
      const hasDiscount = s.has_active_discount ?? false;
      const label = hasDiscount
        ? `${s.name} — ${basePrice} ₽ → ${effectivePrice} ₽`
        : `${s.name} — ${effectivePrice} ₽`;
      return { value: s.id, label };
    }) ?? [];
  const doctorOptions =
    doctors?.filter((d) =>
      !selectedService ||
      (selectedService.doctor_ids?.length ?? 0) === 0 ||
      selectedService.doctor_ids.includes(d.id)
    ).map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  const slots = schedule?.slots?.filter((s) => s.is_available) ?? [];
  const selectedSlotObj = selectedSlot
    ? slots.find((s) => {
        const t = typeof s.start_time === "string" ? s.start_time.slice(0, 5) : String(s.start_time).slice(0, 5);
        return t === selectedSlot;
      })
    : null;
  const timeForApi = selectedSlotObj && typeof selectedSlotObj.start_time === "string"
    ? selectedSlotObj.start_time.length === 5
      ? `${selectedSlotObj.start_time}:00`
      : selectedSlotObj.start_time
    : "";

  const paymentOptions = currentClinic?.payment_options ?? [];

  const handleConfirm = (gatewayId?: string) => {
    if (!patientId || !clinicId || !serviceId || !doctorId || !dateStr || !timeForApi) return;
    createBooking.mutate(
      {
        patientId,
        body: {
          clinic_id: clinicId,
          doctor_id: doctorId,
          service_id: serviceId,
          appointment_date: dateStr,
          appointment_time: timeForApi,
        },
      },
      {
        onSuccess: (booking) => {
          createPayment.mutate(
            { bookingId: booking.id, gatewayId },
            {
              onSuccess: (res) => {
                if (res.prepayment_required === false) {
                  window.location.href = "/booking/success";
                  return;
                }
                if (res.payment_url) {
                  window.location.href = res.payment_url;
                }
              },
            }
          );
        },
      }
    );
  };

  const handleConfirmWithoutPayment = () => {
    if (!patientId || !clinicId || !serviceId || !doctorId || !dateStr || !timeForApi) return;
    createBooking.mutate(
      {
        patientId,
        body: {
          clinic_id: clinicId,
          doctor_id: doctorId,
          service_id: serviceId,
          appointment_date: dateStr,
          appointment_time: timeForApi,
        },
      },
      {
        onSuccess: () => {
          window.location.href = "/booking/success";
        },
      }
    );
  };

  const lastStep = prepaymentEnabled ? 3 : 2;

  const nextDisabled =
    (step === 0 && !serviceId) ||
    (step === 1 && !doctorId) ||
    (step === 2 && !selectedSlot) ||
    (prepaymentEnabled &&
      step === 3 &&
      (!patientId || !clinicId || !serviceId || !doctorId || !dateStr || !timeForApi));

  return (
    <Stack>
      <Title order={3}>Запись на приём</Title>
      <Stepper active={step > lastStep ? lastStep : step} onStepClick={setStep}>
        <Stepper.Step label="Услуга" description="Выберите услугу">
          {servicesLoading && <Loader />}
          <Select
            label="Услуга"
            placeholder="Выберите услугу"
            data={serviceOptions}
            value={serviceId}
            onChange={(v) => {
              setServiceId(v);
              setDoctorId(null);
            }}
          />
        </Stepper.Step>
        <Stepper.Step label="Врач" description="Выберите врача">
          {doctorsLoading && <Loader />}
          {!doctorsLoading && doctorOptions.length === 0 && selectedService && (
            <Text size="sm" c="dimmed">Нет доступных врачей для этой услуги</Text>
          )}
          {!doctorsLoading && doctors && doctors.length > 0 && (
            <SimpleGrid cols={{ base: 2, sm: 3 }} spacing="md" mb="md">
              {doctors
                .filter(
                  (d) =>
                    !selectedService ||
                    (selectedService.doctor_ids?.length ?? 0) === 0 ||
                    selectedService.doctor_ids.includes(d.id)
                )
                .map((d) => {
                  const isSelected = doctorId === d.id;
                  return (
                    <Card
                      key={d.id}
                      withBorder
                      padding="md"
                      radius="md"
                      style={{
                        cursor: "pointer",
                        borderWidth: isSelected ? 2 : 1,
                        borderColor: isSelected ? "var(--mantine-color-primary-6)" : undefined,
                        backgroundColor: isSelected ? "var(--mantine-color-primary-light)" : undefined,
                      }}
                      onClick={() => setDoctorId(d.id)}
                    >
                      <Stack align="center" gap="xs">
                        <Avatar
                          src={d.photo_url ?? undefined}
                          size="lg"
                          radius="xl"
                          color="primary"
                        >
                          {d.full_name.slice(0, 2).toUpperCase()}
                        </Avatar>
                        <Text size="sm" fw={600} ta="center" lineClamp={2}>
                          {d.full_name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          Рейтинг: {d.rating ?? "—"}
                        </Text>
                      </Stack>
                    </Card>
                  );
                })}
            </SimpleGrid>
          )}
          <Select
            label="Врач (или выберите выше)"
            placeholder={doctorOptions.length === 0 ? "Нет доступных врачей" : "Выберите врача"}
            data={doctorOptions}
            value={doctorId}
            onChange={setDoctorId}
            disabled={doctorOptions.length === 0}
          />
        </Stepper.Step>
        <Stepper.Step label="Дата и время" description="Выберите слот">
          <TextInput
            label="Дата"
            type="date"
            value={dateStr}
            onChange={(e) => setDateStr(e.target.value || dayjs().format("YYYY-MM-DD"))}
          />
          {scheduleLoading && <Loader />}
          <Stack gap="xs">
            <Text size="sm" fw={500}>Доступные слоты</Text>
            {slots.length === 0 && !scheduleLoading && <Text size="sm" c="dimmed">Нет свободных слотов на эту дату</Text>}
            {slots.map((s) => {
              const t = typeof s.start_time === "string" ? s.start_time.slice(0, 5) : s.start_time;
              return (
                <Button
                  key={t}
                  variant={selectedSlot === t ? "filled" : "light"}
                  size="xs"
                  onClick={() => setSelectedSlot(t)}
                >
                  {t}
                </Button>
              );
            })}
          </Stack>
        </Stepper.Step>
        {prepaymentEnabled && (
          <Stepper.Step label="Подтверждение" description="Оплата">
            <Text size="sm">Услуга: {publicServices?.find((s) => s.id === serviceId)?.name}</Text>
            <Text size="sm">{doctors?.find((d) => d.id === doctorId)?.display_role ?? "Специалист"}: {doctors?.find((d) => d.id === doctorId)?.full_name}</Text>
            <Text size="sm">Дата: {dateStr}, время: {timeForApi || selectedSlot}</Text>
            {paymentOptions.length > 0 ? (
              <Stack gap="xs">
                <Text size="sm" fw={500}>Способ оплаты</Text>
                {paymentOptions.map((opt) => (
                  <Button
                    key={opt.gateway_id}
                    onClick={() => handleConfirm(opt.gateway_id)}
                    loading={createBooking.isPending || createPayment.isPending}
                    disabled={!!nextDisabled}
                  >
                    Оплатить через {opt.display_name}
                  </Button>
                ))}
              </Stack>
            ) : (
              <Button
                onClick={() => handleConfirm()}
                loading={createBooking.isPending || createPayment.isPending}
                disabled={!!nextDisabled}
              >
                Перейти к оплате
              </Button>
            )}
            {(createBooking.isError || createPayment.isError) && (
              <Text c="red" size="sm">
                {createBooking.error instanceof Error ? createBooking.error.message : createPayment.error instanceof Error ? createPayment.error.message : "Ошибка"}
              </Text>
            )}
          </Stepper.Step>
        )}
      </Stepper>
      <Group>
        {step > 0 && <Button variant="light" onClick={() => setStep(step - 1)}>Назад</Button>}
        {step < lastStep && (
          <Button onClick={() => setStep(step + 1)} disabled={!!nextDisabled}>
            Далее
          </Button>
        )}
        {!prepaymentEnabled && step === lastStep && (
          <Button
            onClick={handleConfirmWithoutPayment}
            loading={createBooking.isPending}
            disabled={!!nextDisabled}
          >
            Подтвердить запись
          </Button>
        )}
      </Group>
    </Stack>
  );
}
