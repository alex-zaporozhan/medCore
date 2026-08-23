import { SignInShell } from "@/auth/SignInShell";
import { PlatformFounderMfaPanel } from "@/auth/panels/PlatformFounderMfaPanel";
import { Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

/** Founder sign-in step 2: TOTP after email/password. Direct URL: `/platform/login/mfa`. */
export default function PlatformFounderMfaPage() {
  const { t } = useTranslation("founder");
  return (
    <SignInShell>
      <Stack gap="lg">
        <div>
          <Title order={2}>{t("mfa.title")}</Title>
          <Text size="sm" c="dimmed" mt={6}>
            {t("mfa.lead")}
          </Text>
        </div>
        <PlatformFounderMfaPanel />
      </Stack>
    </SignInShell>
  );
}
