import { SignInShell } from "@/auth/SignInShell";
import { ClinicStaffSignInPanel } from "@/auth/panels/ClinicStaffSignInPanel";
import { Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

/** Staff and clinic-owner sign-in. Separate from patient and founder. */
export default function ClinicSignInPage() {
  const { t } = useTranslation("auth");
  return (
    <SignInShell>
      <Stack gap="lg">
        <div>
          <Title order={2}>{t("clinic.pageTitle")}</Title>
          <Text size="sm" c="dimmed" mt={6}>
            {t("clinic.pageSubtitle")}
          </Text>
        </div>
        <ClinicStaffSignInPanel />
      </Stack>
    </SignInShell>
  );
}
