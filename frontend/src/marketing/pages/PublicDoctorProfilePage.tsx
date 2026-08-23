import { useParams, Link } from "react-router-dom";
import { Avatar, Button, Container, Group, Paper, Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";
import { ROUTE_PATHS } from "@/routePaths";
import { usePublicDoctorProfileBySlugs } from "@/hooks";
import { QueryErrorAlert } from "@/shared/ui";
import { MarketingPublicChrome } from "@/marketing/components/MarketingPublicChrome";

export default function PublicDoctorProfilePage() {
  const { t } = useTranslation("patient");
  const { clinicSlug, doctorSlug } = useParams();
  const clinicSlugStr = typeof clinicSlug === "string" ? clinicSlug : null;
  const doctorSlugStr = typeof doctorSlug === "string" ? doctorSlug : null;
  const { data, isLoading, isError, error } = usePublicDoctorProfileBySlugs(
    clinicSlugStr,
    doctorSlugStr,
  );

  const photo =
    data?.public_photo_url?.trim() || data?.doctor_photo_url?.trim() || null;

  return (
    <MarketingPublicChrome>
    <Container size="md" py="xl">
      <Paper
        p="xl"
        radius="md"
        style={{ border: "1px solid var(--divider)", background: "var(--bg-card)" }}
      >
        {isLoading ? (
          <Text size="sm" c="dimmed">
            {t("doctorPublic.loading")}
          </Text>
        ) : isError ? (
          <QueryErrorAlert error={error} title={t("doctorPublic.unavailable")} />
        ) : data ? (
          <Stack gap="md">
            <Group align="center" wrap="nowrap">
              <Avatar src={photo} size={88} radius="xl" />
              <Stack gap={4} style={{ flex: 1 }}>
                <Title order={2}>{data.doctor_full_name}</Title>
                <Text size="sm" c="dimmed">
                  {data.doctor_specialization}
                </Text>
              </Stack>
              <Button
                component={Link}
                to={`${ROUTE_PATHS.patient.booking}?clinic_id=${encodeURIComponent(
                  data.clinic_id,
                )}&doctor_id=${encodeURIComponent(data.doctor_id)}`}
                size="md"
              >
                {t("doctorPublic.book")}
              </Button>
            </Group>

            {data.short_bio ? (
              <Text size="sm" c="dimmed">
                {data.short_bio}
              </Text>
            ) : null}

            {data.about_md ? (
              <Stack gap={6}>
                <Text fw={700}>{t("doctorPublic.about")}</Text>
                <Text style={{ whiteSpace: "pre-wrap" }}>{data.about_md}</Text>
              </Stack>
            ) : null}
          </Stack>
        ) : (
          <Text size="sm" c="dimmed">
            {t("doctorPublic.notFound")}
          </Text>
        )}
      </Paper>
    </Container>
    </MarketingPublicChrome>
  );
}
