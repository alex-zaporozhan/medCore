import { SignInShell } from "@/auth/SignInShell";
import { PatientPhoneAuthPanel } from "@/auth/panels/PatientPhoneAuthPanel";
import { usePatientEntry } from "@/contexts/PatientEntryContext";
import { Stack, Text, Title } from "@mantine/core";
import { useTranslation } from "react-i18next";

/**
 * Patient sign-in only in clinic context (`/c/:clinicSlug/sign-in`).
 */
export default function PatientSignInPage() {
  const { t } = useTranslation("patient");
  const { clinicSlug } = usePatientEntry();

  return (
    <SignInShell variant="patient">
      <Stack gap="lg">
        <div>
          <Title order={2}>{t("signIn.title")}</Title>
          <Text size="sm" c="dimmed" mt={6}>
            {t("signIn.clinicCabinet")}
            {clinicSlug ? (
              <>
                {" "}
                <Text span fw={600} component="span">
                  {clinicSlug}
                </Text>
              </>
            ) : null}
            . {t("signIn.smsHint")}
          </Text>
        </div>
        <PatientPhoneAuthPanel />
      </Stack>
    </SignInShell>
  );
}
