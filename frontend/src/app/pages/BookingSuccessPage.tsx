import { Anchor, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useClinics } from "@/hooks";
import { ROUTE_PATHS } from "@/routePaths";

export default function BookingSuccessPage() {
  const { data: clinics } = useClinics();

  const clinicId = (() => {
    const key = "app.selectedClinicId";
    const saved = typeof localStorage !== "undefined" ? localStorage.getItem(key) : null;
    if (saved && clinics?.some((c) => c.id === saved)) return saved;
    return clinics?.[0]?.id ?? null;
  })();

  const currentClinic = clinics?.find((c) => c.id === clinicId) ?? null;
  const prepaymentEnabled = !!currentClinic?.prepayment_enabled;

  return (
    <Stack gap="md" p="xl">
      <Title order={2}>Запись оформлена</Title>
      {prepaymentEnabled ? (
        <Text>Оплата прошла успешно. Ждём вас на приёме.</Text>
      ) : (
        <Text>Ждём вас на приёме.</Text>
      )}
      <Anchor component={Link} to={ROUTE_PATHS.patient.history}>
        В историю
      </Anchor>
      <Anchor component={Link} to={ROUTE_PATHS.patient.home}>
        На главную
      </Anchor>
    </Stack>
  );
}
