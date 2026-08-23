import { Anchor, Container, Paper, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ROUTE_PATHS } from "@/routePaths";
import { MarketingPublicChrome } from "@/marketing/components/MarketingPublicChrome";

/** Terms-of-use placeholder. */
export default function LegalTermsPage() {
  const { t } = useTranslation("marketing");
  return (
    <MarketingPublicChrome>
      <Container size="sm" py="xl">
        <Paper p="xl" radius="md" withBorder>
          <Stack gap="md">
            <Title order={2}>{t("legal.termsTitle")}</Title>
            <Text c="dimmed" size="sm">
              {t("legal.termsBody")}
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
