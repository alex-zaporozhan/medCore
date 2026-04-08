import { PlatformPricingSection } from "@/marketing/components/PlatformPricingSection";
import { ROUTE_PATHS } from "@/routePaths";
import { Anchor, Box, Container, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";

/** Выделенный маршрут «Тарифы» (FE-E1 / бэклог после 1b-E1). */
export default function PricingPage() {
  return (
    <Box
      style={{
        minHeight: "100vh",
        background: "var(--bg-main)",
        padding: "40px 16px",
      }}
    >
      <Container size="lg">
        <Stack gap="xl">
          <div>
            <Title order={1} style={{ color: "var(--text-main)" }}>
              Тарифы для клиник
            </Title>
            <Text size="sm" c="dimmed" mt={8}>
              Каталог планов платформы: выберите пакет, посмотрите состав модулей и оформите подписку.
              Оплата — через YooKassa.
            </Text>
          </div>
          <PlatformPricingSection title="Планы" />
          <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
            ← На главную
          </Anchor>
        </Stack>
      </Container>
    </Box>
  );
}
