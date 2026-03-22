import { Anchor, Button, Card, Group, Paper, ScrollArea, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useClinics, useDoctors, usePatientBookings, usePublicClinicServices } from "@/hooks";
import { usePatientAuth } from "@/contexts/PatientAuthContext";
import { useState, useEffect, useMemo } from "react";
import { useUtmTracking } from "@/shared/utmTracking";
import { EmptyState } from "@/shared/ui/EmptyState";
import { QueryErrorAlert } from "@/shared/ui";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { IconRefresh } from "@tabler/icons-react";
import { ROUTE_PATHS } from "@/routePaths";
import { SEMANTIC } from "@/shared/semanticUi";

const SELECTED_CLINIC_KEY = "app.selectedClinicId";

function shortId(id: string): string {
  if (id.length <= 12) return id;
  return `${id.slice(0, 8)}…`;
}

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Доброе утро";
  if (h < 18) return "Добрый день";
  return "Добрый вечер";
}

/** Имя пациента для приветствия: при наличии GET /v1/patient/me с full_name — подставляется. */
function usePatientName(accessToken: string | null) {
  const { data } = useQuery({
    queryKey: ["patient", "me"],
    queryFn: async (): Promise<{ full_name?: string } | null> => {
      if (!accessToken) return null;
      try {
        const { authApi } = await import("@/api/client");
        return await authApi(accessToken).get<{ full_name?: string }>("/v1/patient/me");
      } catch {
        return null;
      }
    },
    enabled: !!accessToken,
    staleTime: 5 * 60 * 1000,
  });
  return { patientName: data?.full_name ?? null };
}

export default function HomePage() {
  const queryClient = useQueryClient();
  const { data: clinics, isLoading, isError, error } = useClinics();
  const { patientId, accessToken } = usePatientAuth();
  const { patientName } = usePatientName(accessToken);
  const { data: bookings, isFetching: bookingsFetching } = usePatientBookings(patientId, accessToken);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useUtmTracking();

  useEffect(() => {
    const saved = localStorage.getItem(SELECTED_CLINIC_KEY);
    if (saved && clinics?.some((c) => c.id === saved)) setSelectedId(saved);
    else if (clinics?.length === 1) {
      setSelectedId(clinics[0].id);
      localStorage.setItem(SELECTED_CLINIC_KEY, clinics[0].id);
    }
  }, [clinics]);

  const selectClinic = (id: string) => {
    setSelectedId(id);
    localStorage.setItem(SELECTED_CLINIC_KEY, id);
  };

  const nextVisit = useMemo(() => {
    if (!bookings?.length) return null;
    const today = new Date().toISOString().slice(0, 10);
    const upcoming = bookings
      .filter((b) => b.status !== "cancelled" && String(b.appointment_date) >= today)
      .sort((a, b) => String(a.appointment_date).localeCompare(String(b.appointment_date)));
    return upcoming[0] ?? null;
  }, [bookings]);

  const nextVisitClinicId = nextVisit?.clinic_id ?? null;
  const { data: visitServices } = usePublicClinicServices(nextVisitClinicId);
  const { data: visitDoctors } = useDoctors({
    clinic_id: nextVisitClinicId ?? undefined,
    is_active: true,
    enabled: !!nextVisitClinicId,
  });

  const nextVisitDoctorLabel = useMemo(() => {
    if (!nextVisit) return "";
    const d = visitDoctors?.find((x) => x.id === nextVisit.doctor_id);
    return d?.full_name ?? shortId(nextVisit.doctor_id);
  }, [nextVisit, visitDoctors]);

  const nextVisitServiceLabel = useMemo(() => {
    if (!nextVisit) return "";
    const s = visitServices?.find((x) => x.id === nextVisit.service_id);
    return s?.name ?? shortId(nextVisit.service_id);
  }, [nextVisit, visitServices]);

  const hasSingleClinic = clinics && clinics.length === 1;
  const hasMultipleClinics = clinics && clinics.length > 1;
  const greetingText = patientName ? `${getGreeting()}, ${patientName}!` : `${getGreeting()}!`;

  const refreshHome = () => {
    queryClient.invalidateQueries({ queryKey: ["patient", "bookings", patientId ?? ""] });
    queryClient.invalidateQueries({ queryKey: ["clinics"] });
    queryClient.invalidateQueries({ queryKey: ["patient", "me"] });
  };

  return (
    <Stack gap="lg" pb="md" maw={720} w="100%" mx="auto">
      <Group justify="space-between" wrap="nowrap">
        <Title order={3} c="dark.8">
          {greetingText}
        </Title>
        <Button
          variant="subtle"
          color="dark"
          size="xs"
          leftSection={<IconRefresh size={14} />}
          loading={bookingsFetching}
          onClick={refreshHome}
          aria-label="Обновить"
        >
          Обновить
        </Button>
      </Group>

      {/* Next Visit Ticket (PWA 2.0): дата, время, врач, услуга, QR, кнопки */}
      {nextVisit ? (
        <Card
          withBorder
          padding="md"
          radius="md"
          shadow="none"
          style={{ borderColor: "var(--divider)" }}
        >
          <Text size="xs" c="dimmed" tt="uppercase" fw={700} mb="xs" style={{ letterSpacing: "0.04em" }}>
            Ближайший визит
          </Text>
          <Group align="flex-start" justify="space-between" wrap="nowrap">
            <Stack gap={4}>
              <Text fw={600} c="dark.8" size="lg">
                {String(nextVisit.appointment_date)} в {String(nextVisit.appointment_time).slice(0, 5)}
              </Text>
              <Text size="sm" c="dimmed">
                Врач: {nextVisitDoctorLabel} · Услуга: {nextVisitServiceLabel}
              </Text>
              <Group mt="sm">
                <Button
                  component={Link}
                  to={ROUTE_PATHS.patient.booking}
                  variant="light"
                  color={SEMANTIC.action.send}
                  size="xs"
                >
                  Перенести
                </Button>
                <Button
                  component={Link}
                  to={ROUTE_PATHS.patient.history}
                  variant="light"
                  color={SEMANTIC.action.send}
                  size="xs"
                >
                  Отменить
                </Button>
                <Button
                  component={Link}
                  to={ROUTE_PATHS.patient.booking}
                  color={SEMANTIC.action.confirm}
                  size="xs"
                >
                  Добавить в календарь
                </Button>
              </Group>
            </Stack>
            {/* QR для записи (при наличии библиотеки — подставить реальный QR) */}
            <Paper withBorder p="xs" radius="sm" style={{ flexShrink: 0 }}>
              <div
                style={{
                  width: 56,
                  height: 56,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  background: "var(--mantine-color-gray-1)",
                  borderRadius: 4,
                  fontSize: 10,
                  color: "var(--mantine-color-gray-6)",
                }}
              >
                QR
              </div>
              <Text size="xs" c="dimmed" ta="center" mt={4}>
                Визит
              </Text>
            </Paper>
          </Group>
        </Card>
      ) : (
        <EmptyState
          title="Нет ближайших записей"
          description="Запишитесь на приём — выберите врача и удобное время."
          action={{
            label: "Записаться",
            onClick: () => window.location.assign(ROUTE_PATHS.patient.booking),
          }}
        />
      )}

      {/* Stories Bar — горизонтальный скролл (акции, новости) */}
      <div>
        <Text size="sm" fw={600} mb="xs" c="dark.8">
          Акции и новости
        </Text>
        <ScrollArea type="scroll" scrollbarSize={6} style={{ width: "100%" }}>
          <Group gap="md" style={{ flexWrap: "nowrap", paddingBottom: 4 }}>
            {[1, 2, 3].map((i) => (
              <Card
                key={i}
                withBorder
                padding="md"
                radius="xl"
                style={{
                  minWidth: 72,
                  height: 72,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  cursor: "pointer",
                  boxShadow: "none",
                  borderColor: "var(--divider)",
                  background: "var(--bg-card-soft)",
                }}
              >
                <Text size="xs" c="dimmed">
                  {i}
                </Text>
              </Card>
            ))}
          </Group>
        </ScrollArea>
      </div>

      <Paper
        radius="md"
        p="xl"
        maw={520}
        w="100%"
        shadow="none"
        style={{
          border: "1px solid var(--divider)",
          background: "var(--bg-card)",
        }}
      >
        <Stack gap="md">
          <Title order={4} c="dark.8" fw={600}>
            Онлайн‑запись к врачу
          </Title>
          <Text size="sm" c="dimmed">
            Выберите удобное время приёма, не звоня в клинику.
          </Text>
          <Button
            component={Link}
            to={ROUTE_PATHS.patient.booking}
            size="md"
            variant="outline"
            color={SEMANTIC.action.confirm}
          >
            Записаться на приём
          </Button>
          <Anchor component={Link} to={ROUTE_PATHS.patient.history} c={SEMANTIC.action.link} fw={500}>
            Смотреть историю посещений
          </Anchor>
          {isLoading && (
            <Text size="sm" c="dimmed">
              Загружаем клиники...
            </Text>
          )}
          {isError && (
            <QueryErrorAlert error={error} title="Не удалось загрузить клиники" />
          )}
          {hasSingleClinic && (
            <Card
              radius="md"
              withBorder
              shadow="none"
              mt="md"
              style={{ borderColor: "var(--divider)" }}
            >
              <Stack gap={4}>
                <Text fw={500}>Клиника</Text>
                <Text size="sm">{clinics![0].name}</Text>
                {clinics![0].address && (
                  <Text size="sm" c="dimmed">
                    {clinics![0].address}
                  </Text>
                )}
                <Group gap="md" mt="xs">
                  {clinics![0].phone && (
                    <Text size="sm" c="dimmed">
                      Телефон: {clinics![0].phone}
                    </Text>
                  )}
                  {clinics![0].email && (
                    <Text size="sm" c="dimmed">
                      Email: {clinics![0].email}
                    </Text>
                  )}
                </Group>
              </Stack>
            </Card>
          )}
          {hasMultipleClinics && (
            <Stack gap="xs" mt="md">
              <Text size="sm" fw={500}>
                Выберите клинику перед записью
              </Text>
              {clinics!.map((c) => {
                const isSelected = selectedId === c.id;
                return (
                  <Card
                    key={c.id}
                    shadow="none"
                    radius="md"
                    withBorder
                    style={{
                      cursor: "pointer",
                      borderWidth: isSelected ? 2 : 1,
                      borderColor: isSelected ? "var(--mantine-color-primary-6)" : undefined,
                      backgroundColor: isSelected ? "var(--mantine-color-primary-light)" : undefined,
                    }}
                    onClick={() => selectClinic(c.id)}
                  >
                    <Stack gap={4}>
                      <Text fw={500}>{c.name}</Text>
                      {c.address && (
                        <Text size="sm" c="dimmed">
                          {c.address}
                        </Text>
                      )}
                      <Group gap="md" mt="xs">
                        {c.phone && (
                          <Text size="sm" c="dimmed">
                            Телефон: {c.phone}
                          </Text>
                        )}
                        {c.email && (
                          <Text size="sm" c="dimmed">
                            Email: {c.email}
                          </Text>
                        )}
                      </Group>
                    </Stack>
                  </Card>
                );
              })}
            </Stack>
          )}
        </Stack>
      </Paper>
    </Stack>
  );
}
