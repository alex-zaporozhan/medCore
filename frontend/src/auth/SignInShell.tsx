import { Box, Container, Grid, List, Paper, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconCalendarEvent, IconMessages, IconShieldLock } from "@tabler/icons-react";
import type { ReactNode } from "react";

type SignInShellProps = {
  children: ReactNode;
};

/**
 * Общая оболочка экрана входа: единый визуальный язык для всех контуров аутентификации.
 */
export function SignInShell({ children }: SignInShellProps) {
  return (
    <Box
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(160deg, var(--bg-main) 0%, color-mix(in srgb, var(--mantine-color-teal-7) 14%, var(--bg-main)) 55%, var(--bg-main) 100%)",
      }}
    >
      <Container size="xl" py={{ base: "lg", md: "xl" }} px="md">
        <Grid gutter={{ base: "lg", md: "xl" }} align="stretch">
          <Grid.Col span={{ base: 12, md: 5 }}>
            <Stack gap="lg" justify="center" style={{ minHeight: "100%" }} py={{ base: 0, md: "xl" }}>
              <div>
                <Text size="xs" fw={700} tt="uppercase" c="dimmed" mb={6}>
                  Dental Booking
                </Text>
                <Title order={1} size="h2" style={{ color: "var(--text-main)", lineHeight: 1.2 }}>
                  Business OS для клиник
                </Title>
                <Text mt="md" size="md" c="dimmed" maw={440}>
                  Пациенты, персонал и команда платформы работают в разных контурах с разными токенами. Форма
                  справа — только для входа.
                </Text>
              </div>
              <List
                spacing="sm"
                size="sm"
                icon={
                  <ThemeIcon color="teal" variant="light" radius="md" size={34}>
                    <IconShieldLock size={18} aria-hidden />
                  </ThemeIcon>
                }
              >
                <List.Item>
                  <Text fw={600}>Безопасность</Text>
                  <Text size="sm" c="dimmed">
                    Раздельные токены для пациента, персонала клиники и платформы; соединение по HTTPS.
                  </Text>
                </List.Item>
              </List>
              <List
                spacing="sm"
                size="sm"
                icon={
                  <ThemeIcon color="teal" variant="light" radius="md" size={34}>
                    <IconCalendarEvent size={18} aria-hidden />
                  </ThemeIcon>
                }
              >
                <List.Item>
                  <Text fw={600}>Запись и расписание</Text>
                  <Text size="sm" c="dimmed">
                    Онлайн-запись, очереди и напоминания в одной системе.
                  </Text>
                </List.Item>
              </List>
              <List
                spacing="sm"
                size="sm"
                icon={
                  <ThemeIcon color="teal" variant="light" radius="md" size={34}>
                    <IconMessages size={18} aria-hidden />
                  </ThemeIcon>
                }
              >
                <List.Item>
                  <Text fw={600}>Омниканал и задачи</Text>
                  <Text size="sm" c="dimmed">
                    Диалоги с пациентами, внутренние чаты и операционные задачи.
                  </Text>
                </List.Item>
              </List>
            </Stack>
          </Grid.Col>
          <Grid.Col span={{ base: 12, md: 7 }}>
            <Paper
              radius="xl"
              p={{ base: "md", sm: "xl" }}
              shadow="md"
              withBorder
              style={{
                background: "var(--mantine-color-body)",
                borderColor: "var(--divider)",
              }}
            >
              {children}
            </Paper>
          </Grid.Col>
        </Grid>
      </Container>
    </Box>
  );
}
