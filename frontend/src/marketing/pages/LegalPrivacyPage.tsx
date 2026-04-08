import { Anchor, Container, Paper, Stack, Text, Title } from "@mantine/core";
import { Link } from "react-router-dom";
import { ROUTE_PATHS } from "@/routePaths";

/**
 * Плейсхолдер политики конфиденциальности (Phase 1b / МП §5).
 * Юридический текст заполняется отдельно; маршрут нужен для лендинга и чеклистов.
 */
export default function LegalPrivacyPage() {
  return (
    <Container size="sm" py="xl">
      <Paper p="xl" radius="md" withBorder>
        <Stack gap="md">
          <Title order={2}>Политика конфиденциальности</Title>
          <Text c="dimmed" size="sm">
            Здесь будет актуальный текст политики обработки персональных данных и хранения данных
            сервиса. До публикации финальной версии обратитесь к администратору платформы.
          </Text>
          <Anchor component={Link} to={ROUTE_PATHS.marketing.landing} size="sm">
            На главную
          </Anchor>
        </Stack>
      </Paper>
    </Container>
  );
}
