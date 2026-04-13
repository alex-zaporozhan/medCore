import { Box, Container, Grid, List, Paper, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconCalendarEvent, IconMessages, IconShieldLock } from "@tabler/icons-react";
import type { ReactNode } from "react";

type SignInShellProps = {
  children: ReactNode;
  /**
   * `split` — маркетинговая колонка слева (владелец / сотрудник / основатель).
   * `patient` — только форма по центру (вход пациента по `/c/:slug/sign-in`, без тёмной боковой плашки).
   */
  variant?: "split" | "patient";
};

const panelIcon = (Icon: typeof IconShieldLock) => (
  <ThemeIcon
    variant="transparent"
    radius="md"
    size={36}
    style={{
      backgroundColor: "rgba(255,255,255,0.14)",
      color: "#ffffff",
      border: "1px solid rgba(255,255,255,0.2)",
    }}
  >
    <Icon size={18} aria-hidden />
  </ThemeIcon>
);

/**
 * Оболочка экранов входа: по умолчанию тёмный маркетинговый блок слева и форма справа; для пациента — только форма.
 */
export function SignInShell({ children, variant = "split" }: SignInShellProps) {
  if (variant === "patient") {
    return (
      <Box style={{ minHeight: "100vh" }} className="marketing-gradient-bg">
        <Container size="sm" py={{ base: "lg", md: "xl" }} px="md" mih="100vh">
          <Box style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 4rem)" }}>
            <Paper
              radius="xl"
              p={{ base: "lg", sm: "xl" }}
              shadow="xl"
              withBorder={false}
              maw={480}
              w="100%"
              style={{
                background: "#ffffff",
                boxShadow: "var(--mantine-shadow-xl)",
              }}
            >
              {children}
            </Paper>
          </Box>
        </Container>
      </Box>
    );
  }

  return (
    <Box style={{ minHeight: "100vh" }} className="marketing-gradient-bg">
      <Container size="xl" py={{ base: "md", md: "xl" }} px="md" mih="100vh">
        <Grid gutter={0}>
          <Grid.Col
            span={{ base: 12, md: 5 }}
            p={{ base: "lg", md: "xl" }}
            style={{
              background:
                "linear-gradient(165deg, var(--mantine-color-slate-9) 0%, var(--mantine-color-slate-8) 55%, #0f172a 100%)",
              borderRadius: "var(--mantine-radius-lg)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
            }}
          >
            <Stack gap="lg" py={{ base: "sm", md: 0 }}>
              <div>
                <Text size="xs" fw={700} tt="uppercase" c="rgba(255,255,255,0.55)" mb={6} lts={1}>
                  Единая система управления
                </Text>
                <Title order={1} size="h2" c="#ffffff" style={{ lineHeight: 1.2 }}>
                  Операционная платформа для бизнеса с сервисной моделью
                </Title>
                <Text mt="md" size="md" c="rgba(255,255,255,0.78)" maw={440} style={{ lineHeight: 1.55 }}>
                  Пациенты, персонал и команда платформы работают в разных контурах с разными токенами. Форма справа —
                  только для входа.
                </Text>
              </div>
              <List spacing="sm" size="sm" icon={panelIcon(IconShieldLock)} styles={{ itemLabel: { color: "#ffffff" } }}>
                <List.Item>
                  <Text fw={600} c="#ffffff">
                    Безопасность
                  </Text>
                  <Text size="sm" c="rgba(255,255,255,0.72)">
                    Раздельные токены и соединение по HTTPS.
                  </Text>
                </List.Item>
              </List>
              <List spacing="sm" size="sm" icon={panelIcon(IconCalendarEvent)} styles={{ itemLabel: { color: "#ffffff" } }}>
                <List.Item>
                  <Text fw={600} c="#ffffff">
                    Запись и расписание
                  </Text>
                  <Text size="sm" c="rgba(255,255,255,0.72)">
                    Онлайн-запись, очереди и напоминания в одной системе.
                  </Text>
                </List.Item>
              </List>
              <List spacing="sm" size="sm" icon={panelIcon(IconMessages)} styles={{ itemLabel: { color: "#ffffff" } }}>
                <List.Item>
                  <Text fw={600} c="#ffffff">
                    Омниканал и задачи
                  </Text>
                  <Text size="sm" c="rgba(255,255,255,0.72)">
                    Диалоги с клиентами, внутренние чаты и операционные задачи.
                  </Text>
                </List.Item>
              </List>
            </Stack>
          </Grid.Col>
          <Grid.Col
            span={{ base: 12, md: 7 }}
            p={{ base: "md", md: "xl" }}
            style={{ display: "flex", alignItems: "center", justifyContent: "center" }}
          >
            <Paper
              radius="xl"
              p={{ base: "lg", sm: "xl" }}
              shadow="xl"
              withBorder={false}
              maw={480}
              w="100%"
              style={{
                background: "#ffffff",
                boxShadow: "var(--mantine-shadow-xl)",
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
