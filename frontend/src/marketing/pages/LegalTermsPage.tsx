import { Anchor, Container, Paper, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";

/** Плейсхолдер пользовательского соглашения (Phase 1b / МП §5). */
export default function LegalTermsPage() {
  return (
    <Container size="sm" py="xl">
      <Paper p="xl" radius="md" withBorder>
        <Stack gap="md">
          <Title order={2}>Пользовательское соглашение</Title>
          <Text c="dimmed" size="sm">
            Здесь будет публичный оферта / условия использования SaaS. Текст согласуется с
            юридической службой и подставляется перед продакшен-запуском self-service signup.
          </Text>
          <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
            На главную
          </Anchor>
        </Stack>
      </Paper>
    </Container>
  );
}
