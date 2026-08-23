import { usePatientAuth } from "@/contexts/PatientAuthContext";
import {
  useCreatePatientBooking,
  useCreatePayment,
  useDoctorSchedule,
  useDoctors,
  usePublicClinicServices,
  useClinics,
} from "@/hooks";
import {
  Avatar,
  Button,
  Card,
  Group,
  Loader,
  Select,
  SimpleGrid,
  Stack,
  Stepper,
  Text,
  TextInput,
  Title,
  Alert,
} from "@mantine/core";
import dayjs from "dayjs";
import { SEMANTIC } from "@/shared/semanticUi";
import { useEffect, useMemo, useState } from "react";
import type { ApiErrorWithCode } from "@/api/client";
import { getBookingErrorMessage } from "@/shared/errors";
import { ROUTE_PATHS } from "@/routePaths";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const CLINIC_STORAGE_KEY = "app.selectedClinicId";

export default function BookingWizardPage() {
  const { t } = useTranslation("patient");
  const { accessToken, patientId } = usePatientAuth();
  const location = useLocation();
  const [step, setStep] = useState(0);
  const [selectedClinicId, setSelectedClinicId] = useState<string | null>(null);
  const [serviceId, setServiceId] = useState<string | null>(null);
  const [doctorId, setDoctorId] = useState<string | null>(null);
  const [dateStr, setDateStr] = useState(dayjs().format("YYYY-MM-DD"));
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [prefillClinicDone, setPrefillClinicDone] = useState(false);
  const [prefillDoctorDone, setPrefillDoctorDone] = useState(false);

  const { data: clinics } = useClinics();

  useEffect(() => {
    if (!clinics?.length) return;
    const sp = new URLSearchParams(location.search);
    const qsClinicId = sp.get("clinic_id");
    if (!prefillClinicDone && qsClinicId && clinics.some((c) => c.id === qsClinicId)) {
      setSelectedClinicId(qsClinicId);
      if (typeof localStorage !== "undefined") {
        localStorage.setItem(CLINIC_STORAGE_KEY, qsClinicId);
      }
      setPrefillClinicDone(true);
      return;
    }
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem(CLINIC_STORAGE_KEY) : null;
    if (saved && clinics.some((c) => c.id === saved)) {
      setSelectedClinicId(saved);
      return;
    }
    if (clinics.length === 1) {
      setSelectedClinicId(clinics[0].id);
    }
  }, [clinics, location.search, prefillClinicDone]);

  const multiClinic = (clinics?.length ?? 0) > 1;
  const clinicStep = 0;
  const serviceStep = multiClinic ? 1 : 0;
  const doctorStep = multiClinic ? 2 : 1;
  const slotStep = multiClinic ? 3 : 2;
  const payStep = multiClinic ? 4 : 3;

  const clinicId = selectedClinicId;

  const { data: publicServices, isLoading: servicesLoading } = usePublicClinicServices(clinicId);
  const { data: doctors, isLoading: doctorsLoading } = useDoctors({
    clinic_id: clinicId ?? undefined,
    is_active: true,
    enabled: !!clinicId,
  });
  const { data: schedule, isLoading: scheduleLoading } = useDoctorSchedule(doctorId, dateStr, clinicId);

  useEffect(() => {
    // clinic changed (including prefill) → allow doctor prefill to re-run and clear slot
    setPrefillDoctorDone(false);
    setSelectedSlot(null);
  }, [clinicId]);

  const createBooking = useCreatePatientBooking(accessToken);
  const createPayment = useCreatePayment(accessToken);

  const currentClinic = clinics?.find((c) => c.id === clinicId) ?? null;
  const prepaymentEnabled = !!currentClinic?.prepayment_enabled;

  const lastStep = prepaymentEnabled ? payStep : slotStep;

  const persistClinic = (id: string | null) => {
    setSelectedClinicId(id);
    if (typeof localStorage !== "undefined" && id) {
      localStorage.setItem(CLINIC_STORAGE_KEY, id);
    }
    setServiceId(null);
    setDoctorId(null);
    setSelectedSlot(null);
  };

  const bookingError = (createBooking.error ?? null) as ApiErrorWithCode | null;
  const paymentError = (createPayment.error ?? null) as ApiErrorWithCode | null;

  const bookingErrorMessage = useMemo(
    () =>
      bookingError
        ? getBookingErrorMessage(bookingError.code, bookingError.message, "booking")
        : null,
    [bookingError]
  );

  const paymentErrorMessage = useMemo(
    () =>
      paymentError
        ? getBookingErrorMessage(paymentError.code, paymentError.message, "payment")
        : null,
    [paymentError]
  );

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
    doctors
      ?.filter(
        (d) =>
          !selectedService ||
          (selectedService.doctor_ids?.length ?? 0) === 0 ||
          selectedService.doctor_ids.includes(d.id)
      )
      .map((d) => ({ value: d.id, label: d.full_name })) ?? [];

  useEffect(() => {
    if (!clinicId) return;
    if (!doctors?.length) return;
    const sp = new URLSearchParams(location.search);
    const qsDoctorId = sp.get("doctor_id");
    if (prefillDoctorDone) return;
    if (!qsDoctorId) return;
    const hit = doctors.find((d) => d.id === qsDoctorId);
    if (!hit) {
      setPrefillDoctorDone(true);
      return;
    }
    if (hit.clinic_id !== clinicId) {
      setPrefillDoctorDone(true);
      return;
    }
    setDoctorId(qsDoctorId);
    setPrefillDoctorDone(true);
  }, [clinicId, doctors, location.search, prefillDoctorDone]);

  const slots = schedule?.slots?.filter((s) => s.is_available) ?? [];
  const selectedSlotObj = selectedSlot
    ? slots.find((s) => {
        const t =
          typeof s.start_time === "string" ? s.start_time.slice(0, 5) : String(s.start_time).slice(0, 5);
        return t === selectedSlot;
      })
    : null;
  const timeForApi =
    selectedSlotObj && typeof selectedSlotObj.start_time === "string"
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
                  window.location.href = ROUTE_PATHS.other.bookingSuccess;
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
          window.location.href = ROUTE_PATHS.other.bookingSuccess;
        },
      }
    );
  };

  const nextDisabled =
    (multiClinic && step === clinicStep && !selectedClinicId) ||
    (step === serviceStep && !serviceId) ||
    (step === doctorStep && !doctorId) ||
    (step === slotStep && !selectedSlot) ||
    (prepaymentEnabled &&
      step === payStep &&
      (!patientId || !clinicId || !serviceId || !doctorId || !dateStr || !timeForApi));

  return (
    <Stack>
      <Title order={3}>{t("booking.title")}</Title>
      {currentClinic && (
        <Group justify="space-between" align="flex-start" wrap="wrap">
          <Text size="sm" c="dimmed">
            {t("booking.bookingAt", { name: currentClinic.name })}
            {currentClinic.address ? ` — ${currentClinic.address}` : ""}
          </Text>
          {multiClinic && step > clinicStep && (
            <Button variant="subtle" size="xs" onClick={() => setStep(clinicStep)}>
              {t("booking.changeClinic")}
            </Button>
          )}
        </Group>
      )}
      <Stepper active={step > lastStep ? lastStep : step} onStepClick={setStep}>
        {multiClinic && (
          <Stepper.Step label={t("booking.stepClinic")} description={t("booking.stepClinicHint")}>
            <Select
              label={t("booking.clinic")}
              placeholder={t("booking.clinicPlaceholder")}
              data={clinics?.map((c) => ({ value: c.id, label: c.address ? `${c.name} — ${c.address}` : c.name })) ?? []}
              value={selectedClinicId}
              onChange={(v) => {
                persistClinic(v);
              }}
            />
          </Stepper.Step>
        )}
        <Stepper.Step label={t("booking.stepService")} description={t("booking.stepServiceHint")}>
          {!clinicId && multiClinic && <Text size="sm" c="dimmed">{t("booking.pickClinicFirst")}</Text>}
          {servicesLoading && <Loader />}
          <Select
            label={t("booking.service")}
            placeholder={t("booking.servicePlaceholder")}
            data={serviceOptions}
            value={serviceId}
            onChange={(v) => {
              setServiceId(v);
              setDoctorId(null);
              setSelectedSlot(null);
            }}
            disabled={!clinicId}
          />
        </Stepper.Step>
        <Stepper.Step label={t("booking.stepDoctor")} description={t("booking.stepDoctorHint")}>
          {doctorsLoading && <Loader />}
          {!doctorsLoading && doctorOptions.length === 0 && selectedService && (
            <Text size="sm" c="dimmed">
              {t("booking.noDoctors")}
            </Text>
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
                        backgroundColor: isSelected ? "var(--primary-light)" : undefined,
                      }}
                      onClick={() => {
                        setDoctorId(d.id);
                        setSelectedSlot(null);
                      }}
                    >
                      <Stack align="center" gap="xs">
                        <Avatar src={d.photo_url ?? undefined} size="lg" radius="xl" color="primary">
                          {d.full_name.slice(0, 2).toUpperCase()}
                        </Avatar>
                        <Text size="sm" fw={600} ta="center" lineClamp={2}>
                          {d.full_name}
                        </Text>
                        <Text size="xs" c="dimmed">
                          {t("booking.rating", { value: d.rating ?? "—" })}
                        </Text>
                      </Stack>
                    </Card>
                  );
                })}
            </SimpleGrid>
          )}
          <Select
            label={t("booking.doctorSelect")}
            placeholder={doctorOptions.length === 0 ? t("booking.noDoctorsShort") : t("booking.doctorPlaceholder")}
            data={doctorOptions}
            value={doctorId}
            onChange={setDoctorId}
            disabled={doctorOptions.length === 0}
          />
        </Stepper.Step>
        <Stepper.Step label={t("booking.stepSlot")} description={t("booking.stepSlotHint")}>
          <TextInput
            label={t("booking.date")}
            type="date"
            value={dateStr}
            onChange={(e) => setDateStr(e.target.value || dayjs().format("YYYY-MM-DD"))}
          />
          {scheduleLoading && <Loader />}
          <Stack gap="xs">
            <Text size="sm" fw={500}>
              {t("booking.slots")}
            </Text>
            {slots.length === 0 && !scheduleLoading && (
              <Text size="sm" c="dimmed">
                {t("booking.noSlots")}
              </Text>
            )}
            {slots.map((s) => {
              const t = typeof s.start_time === "string" ? s.start_time.slice(0, 5) : s.start_time;
              return (
                <Button
                  key={t}
                  variant={selectedSlot === t ? "filled" : "light"}
                  color={SEMANTIC.action.send}
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
          <Stepper.Step label={t("booking.stepPay")} description={t("booking.stepPayHint")}>
            <Text size="sm">{t("booking.serviceLine", { name: publicServices?.find((s) => s.id === serviceId)?.name })}</Text>
            <Text size="sm">
              {doctors?.find((d) => d.id === doctorId)?.display_role ?? t("booking.specialist")}:{" "}
              {doctors?.find((d) => d.id === doctorId)?.full_name}
            </Text>
            <Text size="sm">
              {t("booking.dateTime", { date: dateStr, time: timeForApi || selectedSlot })}
            </Text>
            {paymentOptions.length > 0 ? (
              <Stack gap="xs">
                <Text size="sm" fw={500}>
                  {t("booking.payMethod")}
                </Text>
                {paymentOptions.map((opt) => (
                  <Button
                    key={opt.gateway_id}
                    color={SEMANTIC.action.confirm}
                    onClick={() => handleConfirm(opt.gateway_id)}
                    loading={createBooking.isPending || createPayment.isPending}
                    disabled={!!nextDisabled}
                  >
                    {t("booking.payVia", { name: opt.display_name })}
                  </Button>
                ))}
              </Stack>
            ) : (
              <Button
                color={SEMANTIC.action.confirm}
                onClick={() => handleConfirm()}
                loading={createBooking.isPending || createPayment.isPending}
                disabled={!!nextDisabled}
              >
                {t("booking.goPay")}
              </Button>
            )}
          </Stepper.Step>
        )}
      </Stepper>
      {(bookingErrorMessage || paymentErrorMessage) && (
        <Alert
          color="red"
          radius="md"
          mt="md"
          role="alert"
          aria-live="assertive"
          aria-atomic="true"
        >
          <Stack gap={4}>
            {bookingErrorMessage && <Text size="sm">{bookingErrorMessage}</Text>}
            {paymentErrorMessage && <Text size="sm">{paymentErrorMessage}</Text>}
            {(bookingError?.traceId || paymentError?.traceId) && (
              <Text size="xs" c="dimmed">
                {t("booking.supportCode", { id: bookingError?.traceId || paymentError?.traceId })}
              </Text>
            )}
          </Stack>
        </Alert>
      )}
      <Group>
        {step > 0 && (
          <Button variant="light" color={SEMANTIC.action.dismiss} onClick={() => setStep(step - 1)}>
            {t("booking.back")}
          </Button>
        )}
        {step < lastStep && (
          <Button color={SEMANTIC.action.send} onClick={() => setStep(step + 1)} disabled={!!nextDisabled}>
            {t("booking.next")}
          </Button>
        )}
        {!prepaymentEnabled && step === slotStep && (
          <Button
            color={SEMANTIC.action.confirm}
            onClick={handleConfirmWithoutPayment}
            loading={createBooking.isPending}
            disabled={!!nextDisabled}
          >
            {t("booking.confirm")}
          </Button>
        )}
      </Group>
    </Stack>
  );
}
