import { Box, Container, Grid, Group, List, Stack, Text, ThemeIcon, Title } from "@mantine/core";
import { IconCalendarEvent, IconMessages, IconShieldLock } from "@tabler/icons-react";
import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { UiLocaleSwitch } from "@/i18n/UiLocaleSwitch";

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
 * Оболочка экранов входа: по умолчанию единая split-карточка (бренд + форма одной высоты);
 * для пациента — только форма.
 */
export function SignInShell({ children, variant = "split" }: SignInShellProps) {
  const { t } = useTranslation("auth");
  if (variant === "patient") {
    return (
      <Box style={{ minHeight: "100vh" }} className="marketing-gradient-bg">
        <Container size="sm" py={{ base: "lg", md: "xl" }} px="md" mih="100vh">
          <Box style={{ display: "flex", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 4rem)" }}>
            <Box
              maw={480}
              w="100%"
              p={{ base: "lg", sm: "xl" }}
              style={{
                background: "#ffffff",
                borderRadius: "var(--mantine-radius-xl)",
                boxShadow: "var(--mantine-shadow-xl)",
              }}
            >
              {children}
            </Box>
          </Box>
        </Container>
      </Box>
    );
  }

  return (
    <Box
      className="marketing-gradient-bg"
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
      }}
    >
      <Container size="lg" py={{ base: "lg", md: "xl" }} px="md" w="100%">
        <Box
          style={{
            overflow: "hidden",
            borderRadius: "var(--mantine-radius-xl)",
            boxShadow: "var(--mantine-shadow-xl)",
            background: "#ffffff",
          }}
        >
          <Grid gutter={0} align="stretch">
            <Grid.Col span={{ base: 12, md: 5 }} style={{ display: "flex" }}>
              <Box
                className="signin-split-pane"
                p={{ base: "lg", md: "xl" }}
                style={{
                  background:
                    "linear-gradient(165deg, var(--mantine-color-slate-7) 0%, var(--mantine-color-slate-8) 62%, #334155 100%)",
                }}
              >
                <Stack gap="lg">
                  <div>
                    <Text size="xs" fw={700} tt="uppercase" c="rgba(255,255,255,0.55)" mb={6} lts={1}>
                      {t("shell.brand")}
                    </Text>
                    <Title order={1} size="h2" c="#ffffff" style={{ lineHeight: 1.2 }}>
                      {t("shell.title")}
                    </Title>
                    <Text mt="md" size="md" c="rgba(255,255,255,0.78)" maw={440} style={{ lineHeight: 1.55 }}>
                      {t("shell.body")}
                    </Text>
                  </div>
                  <List spacing="sm" size="sm" icon={panelIcon(IconShieldLock)} styles={{ itemLabel: { color: "#ffffff" } }}>
                    <List.Item>
                      <Text fw={600} c="#ffffff">
                        {t("shell.securityTitle")}
                      </Text>
                      <Text size="sm" c="rgba(255,255,255,0.72)">
                        {t("shell.securityBody")}
                      </Text>
                    </List.Item>
                  </List>
                  <List spacing="sm" size="sm" icon={panelIcon(IconCalendarEvent)} styles={{ itemLabel: { color: "#ffffff" } }}>
                    <List.Item>
                      <Text fw={600} c="#ffffff">
                        {t("shell.scheduleTitle")}
                      </Text>
                      <Text size="sm" c="rgba(255,255,255,0.72)">
                        {t("shell.scheduleBody")}
                      </Text>
                    </List.Item>
                  </List>
                  <List spacing="sm" size="sm" icon={panelIcon(IconMessages)} styles={{ itemLabel: { color: "#ffffff" } }}>
                    <List.Item>
                      <Text fw={600} c="#ffffff">
                        {t("shell.omniTitle")}
                      </Text>
                      <Text size="sm" c="rgba(255,255,255,0.72)">
                        {t("shell.omniBody")}
                      </Text>
                    </List.Item>
                  </List>
                </Stack>
              </Box>
            </Grid.Col>
            <Grid.Col span={{ base: 12, md: 7 }} style={{ display: "flex" }}>
              <Box
                className="signin-split-pane"
                p={{ base: "lg", md: "xl" }}
                style={{
                  background: "#ffffff",
                }}
              >
                <Group justify="flex-end" mb="md">
                  <UiLocaleSwitch />
                </Group>
                <Box maw={420} w="100%" mx="auto">
                  {children}
                </Box>
              </Box>
            </Grid.Col>
          </Grid>
        </Box>
      </Container>
    </Box>
  );
}
