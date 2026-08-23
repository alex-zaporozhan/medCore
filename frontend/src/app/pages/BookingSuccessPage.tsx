import { Anchor, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useClinics } from "@/hooks";
import { ROUTE_PATHS } from "@/routePaths";
import { useTranslation } from "react-i18next";

export default function BookingSuccessPage() {
  const { t } = useTranslation("patient");
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
      <Title order={2}>{t("success.title")}</Title>
      {prepaymentEnabled ? (
        <Text>{t("success.paid")}</Text>
      ) : (
        <Text>{t("success.wait")}</Text>
      )}
      <Anchor component={Link} to={ROUTE_PATHS.patient.history}>
        {t("success.toHistory")}
      </Anchor>
      <Anchor component={Link} to={ROUTE_PATHS.patient.home}>
        {t("success.toHome")}
      </Anchor>
    </Stack>
  );
}
