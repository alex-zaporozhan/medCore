import { UiLocaleSwitch } from "@/i18n/UiLocaleSwitch";
import { PlatformPricingSection } from "@/marketing/components/PlatformPricingSection";
import { ROUTE_PATHS } from "@/routePaths";
import { Anchor, Box, Checkbox, Container, Group, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { Trans, useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

/**
 * Organization signup: PII consents + the same checkout as /pricing.
 */
export default function SignupPage() {
  const { t } = useTranslation("marketing");
  const [consentPd, setConsentPd] = useState(false);
  const [consentTerms, setConsentTerms] = useState(false);
  const canProceed = consentPd && consentTerms;

  return (
    <Box className="marketing-gradient-bg" style={{ minHeight: "100vh", padding: "40px 16px" }}>
      <Container size="lg">
        <Stack gap="xl">
          <Group justify="space-between" wrap="wrap" gap="sm" align="flex-start">
            <div>
              <Title order={1} style={{ color: "var(--text-main)" }}>
                {t("signup.title")}
              </Title>
              <Text size="sm" c="dimmed" mt={8}>
                {t("signup.lead")}
              </Text>
            </div>
            <UiLocaleSwitch />
          </Group>

          <Stack gap="sm">
            <Checkbox
              checked={consentPd}
              onChange={(e) => setConsentPd(e.currentTarget.checked)}
              label={
                <Text size="sm">
                  <Trans
                    ns="marketing"
                    i18nKey="signup.consentPd"
                    components={{
                      privacyLink: (
                        <Anchor component={Link} to={ROUTE_PATHS.marketing.legalPrivacy} target="_blank" />
                      ),
                    }}
                  />
                </Text>
              }
            />
            <Checkbox
              checked={consentTerms}
              onChange={(e) => setConsentTerms(e.currentTarget.checked)}
              label={
                <Text size="sm">
                  <Trans
                    ns="marketing"
                    i18nKey="signup.consentTerms"
                    components={{
                      termsLink: <Anchor component={Link} to={ROUTE_PATHS.marketing.legalTerms} target="_blank" />,
                    }}
                  />
                </Text>
              }
            />
          </Stack>

          {!canProceed ? (
            <Text size="sm" c="dimmed">
              {t("signup.needConsents")}
            </Text>
          ) : null}

          <PlatformPricingSection title={t("signup.pricingTitle")} checkoutEnabled={canProceed} />

          <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
            ← {t("signup.backHome")}
          </Anchor>
        </Stack>
      </Container>
    </Box>
  );
}
