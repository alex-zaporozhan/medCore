import { Anchor, Container, Paper, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ROUTE_PATHS } from "@/routePaths";
import { MarketingPublicChrome } from "@/marketing/components/MarketingPublicChrome";

/** Privacy-policy placeholder. Legal copy is filled separately; the route is required for landing checklists. */
export default function LegalPrivacyPage() {
  const { t } = useTranslation("marketing");
  return (
    <MarketingPublicChrome>
      <Container size="sm" py="xl">
        <Paper p="xl" radius="md" withBorder>
          <Stack gap="md">
            <Title order={2}>{t("legal.privacyTitle")}</Title>
            <Text c="dimmed" size="sm">
              {t("legal.privacyBody")}
            </Text>
            <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
              {t("legal.home")}
            </Anchor>
          </Stack>
        </Paper>
      </Container>
    </MarketingPublicChrome>
  );
}
