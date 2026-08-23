import { SignInShell } from "@/auth/SignInShell";
import { PlatformFounderSignInPanel } from "@/auth/panels/PlatformFounderSignInPanel";
import { Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

/**
 * Hidden platform-founder sign-in (not in the marketing nav).
 * Direct URL: `/platform/login`.
 */
export default function PlatformFounderLoginPage() {
  const { t } = useTranslation("auth");
  return (
    <SignInShell>
      <Stack gap="lg">
        <div>
          <Title order={2}>{t("founder.pageTitle")}</Title>
          <Text size="sm" c="dimmed" mt={6}>
            {t("founder.pageSubtitle")}
          </Text>
        </div>
        <PlatformFounderSignInPanel />
      </Stack>
    </SignInShell>
  );
}
