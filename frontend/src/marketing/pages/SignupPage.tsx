import { PlatformPricingSection } from "@/marketing/components/PlatformPricingSection";
import { ROUTE_PATHS } from "@/routePaths";
import { Anchor, Box, Checkbox, Container, Stack, Text, Title } from "@mantine/core";
import { useState } from "react";
import { Link } from "react-router-dom";

/**
 * Регистрация клиники на платформе (FE-E1 / 1b-F3): согласия PII + тот же checkout, что на /pricing.
 */
export default function SignupPage() {
  const [consentPd, setConsentPd] = useState(false);
  const [consentTerms, setConsentTerms] = useState(false);
  const canProceed = consentPd && consentTerms;

  return (
    <Box style={{ minHeight: "100vh", background: "var(--bg-main)", padding: "40px 16px" }}>
      <Container size="lg">
        <Stack gap="xl">
          <div>
            <Title order={1} style={{ color: "var(--text-main)" }}>
              Регистрация клиники
            </Title>
            <Text size="sm" c="dimmed" mt={8}>
              Подбор тарифа из каталога и оплата. После успешной оплаты платформа создаёт организацию и
              отправляет владельцу приглашение в админку.
            </Text>
          </div>

          <Stack gap="sm">
            <Checkbox
              checked={consentPd}
              onChange={(e) => setConsentPd(e.currentTarget.checked)}
              label={
                <Text size="sm">
                  Согласен(на) на обработку персональных данных владельца (email) в рамках оформления
                  подписки. Политика:{" "}
                  <Anchor component={Link} to={ROUTE_PATHS.marketing.legalPrivacy} target="_blank">
                    Конфиденциальность
                  </Anchor>
                  .
                </Text>
              }
            />
            <Checkbox
              checked={consentTerms}
              onChange={(e) => setConsentTerms(e.currentTarget.checked)}
              label={
                <Text size="sm">
                  Ознакомлен(а) и согласен(на) с{" "}
                  <Anchor component={Link} to={ROUTE_PATHS.marketing.legalTerms} target="_blank">
                    условиями использования
                  </Anchor>
                  .
                </Text>
              }
            />
          </Stack>

          {canProceed ? (
            <PlatformPricingSection title="Выбор плана и оплата" />
          ) : (
            <Text size="sm" c="dimmed">
              Отметьте оба согласия, чтобы перейти к выбору тарифа и оплате.
            </Text>
          )}

          <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
            ← На главную
          </Anchor>
        </Stack>
      </Container>
    </Box>
  );
}
